import { ipcMain, BrowserWindow, desktopCapturer } from "electron";
import WebSocket from "ws";

interface AudioCaptureConfig {
  sourceId?: string;
  sampleRate: number;
  channels: number;
}

interface AudioDevice {
  id: string;
  name: string;
  type: "input" | "output";
}

let deepgramSocket: WebSocket | null = null;
let isCapturing = false;

async function startDeepgramConnection(window: BrowserWindow | null): Promise<void> {
  const apiKey = process.env.DEEPGRAM_API_KEY;
  if (!apiKey) {
    console.error("[Audio IPC] DEEPGRAM_API_KEY not set");
    return;
  }

  const url = [
    "wss://api.deepgram.com/v1/listen",
    "?model=nova-3",
    "&language=en-IN",
    "&punctuate=true",
    "&smart_format=true",
    "&interim_results=true",
    "&endpointing=300",
    "&utterance_end_ms=1000",
  ].join("");

  deepgramSocket = new WebSocket(url, {
    headers: {
      Authorization: `Token ${apiKey}`,
    },
  });

  deepgramSocket.on("open", () => {
    console.log("[Audio IPC] Deepgram WebSocket connected");
    isCapturing = true;
  });

  deepgramSocket.on("message", (data: WebSocket.Data) => {
    try {
      const result = JSON.parse(data.toString());
      const transcript = result?.channel?.alternatives?.[0]?.transcript;
      const isFinal = result?.is_final;
      const speechFinal = result?.speech_final;

      if (transcript && transcript.trim()) {
        if (isFinal || speechFinal) {
          window?.webContents.send("transcript:final", transcript.trim());
        } else {
          window?.webContents.send("transcript:partial", transcript.trim());
        }
      }
    } catch (error) {
      console.error("[Audio IPC] Failed to parse Deepgram response:", error);
    }
  });

  deepgramSocket.on("error", (error) => {
    console.error("[Audio IPC] Deepgram WebSocket error:", error);
  });

  deepgramSocket.on("close", (code, reason) => {
    console.log(`[Audio IPC] Deepgram WebSocket closed: ${code} ${reason}`);
    isCapturing = false;
    deepgramSocket = null;
  });
}

export function registerAudioIPC(window: BrowserWindow | null): void {
  ipcMain.handle("audio:start-capture", async (_event, config: AudioCaptureConfig) => {
    if (isCapturing) {
      console.warn("[Audio IPC] Already capturing audio");
      return;
    }

    try {
      await startDeepgramConnection(window);
      console.log(`[Audio IPC] Started audio capture (sampleRate: ${config.sampleRate})`);
    } catch (error) {
      console.error("[Audio IPC] Failed to start audio capture:", error);
      throw error;
    }
  });

  ipcMain.handle("audio:stop-capture", async () => {
    if (deepgramSocket && deepgramSocket.readyState === WebSocket.OPEN) {
      deepgramSocket.send(JSON.stringify({ type: "CloseStream" }));
      deepgramSocket.close();
      deepgramSocket = null;
    }
    isCapturing = false;
    console.log("[Audio IPC] Stopped audio capture");
  });

  ipcMain.handle("audio:get-devices", async (): Promise<AudioDevice[]> => {
    try {
      const sources = await desktopCapturer.getSources({
        types: ["window", "screen"],
        fetchWindowIcons: false,
      });

      const devices: AudioDevice[] = [
        { id: "default", name: "System Audio (Default)", type: "output" },
        ...sources.map((s) => ({
          id: s.id,
          name: s.name,
          type: "output" as const,
        })),
      ];

      return devices;
    } catch (error) {
      console.error("[Audio IPC] Failed to get audio devices:", error);
      return [{ id: "default", name: "System Audio", type: "output" }];
    }
  });

  ipcMain.on("audio:send-chunk", (_event, chunk: ArrayBuffer) => {
    if (deepgramSocket && deepgramSocket.readyState === WebSocket.OPEN && isCapturing) {
      deepgramSocket.send(chunk);
    }
  });
}
