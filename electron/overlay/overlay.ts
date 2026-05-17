import { BrowserWindow, screen, clipboard } from "electron";

export class OverlayController {
  private window: BrowserWindow | null = null;
  private overlayUrl: string;
  private isVisible: boolean = false;
  private currentAnswer: string = "";

  constructor(overlayUrl: string) {
    this.overlayUrl = overlayUrl;
    this.createOverlayWindow();
  }

  private createOverlayWindow(): void {
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;

    this.window = new BrowserWindow({
      width: 480,
      height: 320,
      x: width - 500,
      y: 20,
      transparent: true,
      alwaysOnTop: true,
      skipTaskbar: true,
      hasShadow: false,
      frame: false,
      focusable: false,
      resizable: false,
      movable: false,
      show: false,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        webSecurity: true,
      },
    });

    this.window.setIgnoreMouseEvents(true, { forward: true });

    this.applyStealthMode();

    this.window.loadURL(this.overlayUrl).catch((err) => {
      console.error("[Overlay] Failed to load overlay URL:", err);
    });

    this.window.webContents.on("did-finish-load", () => {
      console.log("[Overlay] Overlay window loaded");
    });

    this.window.on("closed", () => {
      this.window = null;
      this.isVisible = false;
    });
  }

  private applyStealthMode(): void {
    if (!this.window) return;

    if (process.platform === "darwin") {
      this.window.setContentProtection(true);

      this.window.setWindowButtonVisibility(false);
    } else if (process.platform === "win32") {
      this.window.setContentProtection(true);
    } else {
      this.window.setContentProtection(true);
    }

    console.log("[Overlay] Stealth mode applied — hidden from screen capture");
  }

  show(): void {
    if (!this.window) {
      this.createOverlayWindow();
    }
    this.window?.showInactive();
    this.isVisible = true;
    console.log("[Overlay] Overlay visible");
  }

  hide(): void {
    this.window?.hide();
    this.isVisible = false;
    console.log("[Overlay] Overlay hidden");
  }

  toggle(): void {
    if (this.isVisible) {
      this.hide();
    } else {
      this.show();
    }
  }

  sendToOverlay(channel: string, data: unknown): void {
    if (this.window && !this.window.isDestroyed()) {
      this.window.webContents.send(channel, data);

      if (channel === "answer:stream-token" && typeof data === "string") {
        this.currentAnswer += data;
      } else if (channel === "answer:clear") {
        this.currentAnswer = "";
      } else if (channel === "answer:complete") {
        const payload = data as { answer: string; confidence: number };
        this.currentAnswer = payload.answer;
        this.show();
      }
    }
  }

  triggerOACapture(): void {
    this.sendToOverlay("oa:capture-triggered", null);
    console.log("[Overlay] OA capture triggered via hotkey");
  }

  copyAnswer(): void {
    if (this.currentAnswer) {
      clipboard.writeText(this.currentAnswer);
      console.log("[Overlay] Answer copied to clipboard");
    }
  }

  setPosition(x: number, y: number): void {
    this.window?.setPosition(x, y);
  }

  resize(width: number, height: number): void {
    this.window?.setSize(width, height);
  }

  destroy(): void {
    if (this.window && !this.window.isDestroyed()) {
      this.window.destroy();
      this.window = null;
    }
  }

  getIsVisible(): boolean {
    return this.isVisible;
  }
}
