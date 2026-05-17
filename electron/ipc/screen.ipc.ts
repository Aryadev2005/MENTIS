import { ipcMain, BrowserWindow, desktopCapturer, screen, nativeImage } from "electron";

interface ScreenSource {
  id: string;
  name: string;
  thumbnail: string;
  appIcon?: string;
}

export function registerScreenIPC(window: BrowserWindow | null): void {
  ipcMain.handle("screen:get-sources", async (): Promise<ScreenSource[]> => {
    try {
      const display = screen.getPrimaryDisplay();
      const { width, height } = display.size;

      const sources = await desktopCapturer.getSources({
        types: ["screen", "window"],
        thumbnailSize: { width: Math.floor(width / 4), height: Math.floor(height / 4) },
        fetchWindowIcons: true,
      });

      return sources.map((source) => ({
        id: source.id,
        name: source.name,
        thumbnail: source.thumbnail.toDataURL(),
        appIcon: source.appIcon?.toDataURL(),
      }));
    } catch (error) {
      console.error("[Screen IPC] Failed to get sources:", error);
      return [];
    }
  });

  ipcMain.handle("screen:capture", async (): Promise<string> => {
    try {
      const display = screen.getPrimaryDisplay();
      const { width, height } = display.size;

      const sources = await desktopCapturer.getSources({
        types: ["screen"],
        thumbnailSize: { width, height },
      });

      const primaryScreen = sources.find((s) => s.name === "Entire Screen" || s.name === "Screen 1") || sources[0];

      if (!primaryScreen) {
        throw new Error("No screen source found");
      }

      const dataUrl = primaryScreen.thumbnail.toDataURL("image/png");
      console.log("[Screen IPC] Full screen captured");
      return dataUrl;
    } catch (error) {
      console.error("[Screen IPC] Screen capture failed:", error);
      throw error;
    }
  });

  ipcMain.handle("screen:capture-current-window", async (): Promise<string> => {
    try {
      const display = screen.getPrimaryDisplay();
      const { width, height } = display.size;

      const sources = await desktopCapturer.getSources({
        types: ["window"],
        thumbnailSize: { width, height },
        fetchWindowIcons: false,
      });

      const activeSource = sources.find((s) => !s.name.includes("MENTIS")) || sources[0];

      if (!activeSource) {
        return ipcMain.emit("screen:capture", null);
      }

      const dataUrl = activeSource.thumbnail.toDataURL("image/png");
      console.log(`[Screen IPC] Window captured: ${activeSource.name}`);
      return dataUrl;
    } catch (error) {
      console.error("[Screen IPC] Window capture failed:", error);
      throw error;
    }
  });

  ipcMain.handle("screen:capture-region", async (_event, x: number, y: number, w: number, h: number): Promise<string> => {
    try {
      const display = screen.getPrimaryDisplay();
      const { width, height } = display.size;

      const sources = await desktopCapturer.getSources({
        types: ["screen"],
        thumbnailSize: { width, height },
      });

      const primaryScreen = sources[0];
      if (!primaryScreen) throw new Error("No screen source");

      const fullImage = primaryScreen.thumbnail;
      const cropped = fullImage.crop({ x, y, width: w, height: h });
      return cropped.toDataURL("image/png");
    } catch (error) {
      console.error("[Screen IPC] Region capture failed:", error);
      throw error;
    }
  });
}
