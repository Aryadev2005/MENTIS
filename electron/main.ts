import {
  app,
  BrowserWindow,
  globalShortcut,
  ipcMain,
  shell,
  Tray,
  Menu,
  nativeImage,
  Notification,
  screen,
  powerMonitor,
} from "electron";
import path from "path";
import { spawn, ChildProcess } from "child_process";
import fs from "fs";
import { registerAudioIPC } from "./ipc/audio.ipc";
import { registerScreenIPC } from "./ipc/screen.ipc";
import { registerSessionIPC } from "./ipc/session.ipc";
import { OverlayController } from "./overlay/overlay";

const isDev = process.env.ELECTRON_IS_DEV === "true" || !app.isPackaged;
const RENDERER_URL = process.env.RENDERER_URL || "http://localhost:5173";
const OVERLAY_URL = process.env.OVERLAY_URL || "http://localhost:5174";

let mainWindow: BrowserWindow | null = null;
let overlayController: OverlayController | null = null;
let tray: Tray | null = null;
let fastApiProcess: ChildProcess | null = null;

function getRendererPath(): string {
  return isDev
    ? RENDERER_URL
    : `file://${path.join(__dirname, "../renderer/index.html")}`;
}

function getOverlayPath(): string {
  return isDev
    ? OVERLAY_URL
    : `file://${path.join(__dirname, "../overlay/overlay.html")}`;
}

async function startFastAPIServer(): Promise<void> {
  if (isDev) {
    console.log("[MENTIS] Dev mode: Assuming FastAPI server is already running on port 8000");
    return;
  }

  const pythonPath = path.join(process.resourcesPath, "api", "venv", "bin", "python");
  const apiPath = path.join(process.resourcesPath, "api", "main.py");

  if (!fs.existsSync(apiPath)) {
    console.error("[MENTIS] FastAPI main.py not found at:", apiPath);
    return;
  }

  fastApiProcess = spawn(pythonPath, ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"], {
    cwd: path.join(process.resourcesPath, "api"),
    env: {
      ...process.env,
      PYTHONPATH: path.join(process.resourcesPath, "api"),
    },
  });

  fastApiProcess.stdout?.on("data", (data: Buffer) => {
    console.log("[FastAPI]", data.toString().trim());
  });

  fastApiProcess.stderr?.on("data", (data: Buffer) => {
    const msg = data.toString().trim();
    if (msg && !msg.includes("INFO")) {
      console.error("[FastAPI Error]", msg);
    }
  });

  fastApiProcess.on("close", (code) => {
    console.log(`[MENTIS] FastAPI process exited with code ${code}`);
  });

  await new Promise<void>((resolve) => setTimeout(resolve, 2000));
}

function createMainWindow(): void {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  mainWindow = new BrowserWindow({
    width: Math.min(1440, width),
    height: Math.min(900, height),
    minWidth: 1024,
    minHeight: 700,
    show: false,
    backgroundColor: "#0A0A0F",
    titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "default",
    trafficLightPosition: { x: 16, y: 16 },
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
      webSecurity: true,
      allowRunningInsecureContent: false,
    },
  });

  mainWindow.loadURL(getRendererPath());

  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
    if (isDev) {
      mainWindow?.webContents.openDevTools({ mode: "detach" });
    }
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("https://") || url.startsWith("http://")) {
      shell.openExternal(url);
    }
    return { action: "deny" };
  });

  mainWindow.on("minimize", () => {
    if (process.platform === "darwin") {
      mainWindow?.hide();
    }
  });
}

function createTray(): void {
  const iconPath = path.join(__dirname, "../../assets/tray-icon.png");
  const trayIcon = fs.existsSync(iconPath)
    ? nativeImage.createFromPath(iconPath)
    : nativeImage.createEmpty();

  tray = new Tray(trayIcon.resize({ width: 16, height: 16 }));

  const contextMenu = Menu.buildFromTemplate([
    {
      label: "MENTIS — Your Unfair Advantage",
      enabled: false,
    },
    { type: "separator" },
    {
      label: "Open Dashboard",
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        } else {
          createMainWindow();
        }
      },
    },
    {
      label: "Toggle Overlay",
      accelerator: process.platform === "darwin" ? "Cmd+Shift+H" : "Ctrl+Shift+H",
      click: () => overlayController?.toggle(),
    },
    { type: "separator" },
    {
      label: "Quit MENTIS",
      click: () => app.quit(),
    },
  ]);

  tray.setToolTip("MENTIS — Your Unfair Advantage");
  tray.setContextMenu(contextMenu);

  tray.on("double-click", () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    } else {
      createMainWindow();
    }
  });
}

function registerGlobalShortcuts(): void {
  const isMac = process.platform === "darwin";
  const mod = isMac ? "CommandOrControl" : "Ctrl";

  globalShortcut.register(`${mod}+Shift+H`, () => {
    overlayController?.toggle();
  });

  globalShortcut.register(`${mod}+Shift+S`, () => {
    overlayController?.triggerOACapture();
    mainWindow?.webContents.send("hotkey:oa-capture");
  });

  globalShortcut.register(`${mod}+Shift+C`, () => {
    overlayController?.copyAnswer();
    mainWindow?.webContents.send("hotkey:copy-answer");
  });

  globalShortcut.register(`${mod}+Shift+M`, () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });

  console.log("[MENTIS] Global shortcuts registered");
}

function sendNotification(title: string, body: string): void {
  if (Notification.isSupported()) {
    new Notification({
      title,
      body,
      silent: false,
    }).show();
  }
}

ipcMain.handle("app:get-version", () => app.getVersion());
ipcMain.handle("app:get-platform", () => process.platform);

ipcMain.handle("notification:send", (_event, title: string, body: string) => {
  sendNotification(title, body);
});

ipcMain.on("overlay:show", () => overlayController?.show());
ipcMain.on("overlay:hide", () => overlayController?.hide());
ipcMain.on("overlay:toggle", () => overlayController?.toggle());

ipcMain.on("answer:stream-token", (_event, token: string) => {
  overlayController?.sendToOverlay("answer:stream-token", token);
});

ipcMain.on("answer:complete", (_event, answer: string, confidence: number) => {
  overlayController?.sendToOverlay("answer:complete", { answer, confidence });
});

ipcMain.on("answer:clear", () => {
  overlayController?.sendToOverlay("answer:clear", null);
});

app.whenReady().then(async () => {
  console.log("[MENTIS] App starting...");

  if (!isDev) {
    await startFastAPIServer();
  }

  createMainWindow();
  createTray();
  registerGlobalShortcuts();

  overlayController = new OverlayController(getOverlayPath());

  registerAudioIPC(mainWindow);
  registerScreenIPC(mainWindow);
  registerSessionIPC(mainWindow);

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    } else {
      mainWindow?.show();
    }
  });

  powerMonitor.on("suspend", () => {
    mainWindow?.webContents.send("system:suspend");
    overlayController?.hide();
  });

  powerMonitor.on("resume", () => {
    mainWindow?.webContents.send("system:resume");
  });

  console.log("[MENTIS] Ready. Your unfair advantage awaits.");
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();

  if (fastApiProcess) {
    fastApiProcess.kill("SIGTERM");
    fastApiProcess = null;
  }

  console.log("[MENTIS] Shutting down gracefully.");
});

app.on("web-contents-created", (_event, contents) => {
  contents.on("will-navigate", (event, navigationUrl) => {
    const parsedUrl = new URL(navigationUrl);
    const allowedHosts = ["localhost", "127.0.0.1"];

    if (!allowedHosts.includes(parsedUrl.hostname)) {
      event.preventDefault();
    }
  });
});

if (!isDev) {
  app.enableSandbox();
}
