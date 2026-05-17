import { contextBridge, ipcRenderer, IpcRendererEvent } from "electron";

type IpcCallback = (...args: unknown[]) => void;

function safeOn(channel: string, callback: IpcCallback) {
  const validChannels = new Set([
    "hotkey:oa-capture",
    "hotkey:copy-answer",
    "system:suspend",
    "system:resume",
    "answer:stream-token",
    "answer:complete",
    "answer:clear",
    "session:started",
    "session:ended",
    "audio:chunk",
    "transcript:partial",
    "transcript:final",
    "notification:received",
  ]);

  if (!validChannels.has(channel)) {
    console.warn(`[Preload] Blocked unknown channel: ${channel}`);
    return () => {};
  }

  const handler = (_event: IpcRendererEvent, ...args: unknown[]) =>
    callback(...args);
  ipcRenderer.on(channel, handler);

  return () => ipcRenderer.removeListener(channel, handler);
}

const mentisAPI = {
  app: {
    getVersion: (): Promise<string> =>
      ipcRenderer.invoke("app:get-version"),
    getPlatform: (): Promise<string> =>
      ipcRenderer.invoke("app:get-platform"),
  },

  notification: {
    send: (title: string, body: string): Promise<void> =>
      ipcRenderer.invoke("notification:send", title, body),
  },

  overlay: {
    show: (): void => ipcRenderer.send("overlay:show"),
    hide: (): void => ipcRenderer.send("overlay:hide"),
    toggle: (): void => ipcRenderer.send("overlay:toggle"),
  },

  answer: {
    onStreamToken: (cb: (token: string) => void) =>
      safeOn("answer:stream-token", cb as IpcCallback),
    onComplete: (cb: (data: { answer: string; confidence: number }) => void) =>
      safeOn("answer:complete", cb as IpcCallback),
    onClear: (cb: () => void) =>
      safeOn("answer:clear", cb as IpcCallback),
    streamToken: (token: string): void =>
      ipcRenderer.send("answer:stream-token", token),
    complete: (answer: string, confidence: number): void =>
      ipcRenderer.send("answer:complete", answer, confidence),
    clear: (): void => ipcRenderer.send("answer:clear"),
  },

  session: {
    start: (config: SessionConfig): Promise<string> =>
      ipcRenderer.invoke("session:start", config),
    end: (sessionId: string): Promise<SessionSummary> =>
      ipcRenderer.invoke("session:end", sessionId),
    getCurrent: (): Promise<SessionState | null> =>
      ipcRenderer.invoke("session:get-current"),
    onStarted: (cb: (sessionId: string) => void) =>
      safeOn("session:started", cb as IpcCallback),
    onEnded: (cb: (summary: SessionSummary) => void) =>
      safeOn("session:ended", cb as IpcCallback),
  },

  audio: {
    startCapture: (config: AudioCaptureConfig): Promise<void> =>
      ipcRenderer.invoke("audio:start-capture", config),
    stopCapture: (): Promise<void> =>
      ipcRenderer.invoke("audio:stop-capture"),
    getDevices: (): Promise<AudioDevice[]> =>
      ipcRenderer.invoke("audio:get-devices"),
    onChunk: (cb: (chunk: ArrayBuffer) => void) =>
      safeOn("audio:chunk", cb as IpcCallback),
    onTranscriptPartial: (cb: (text: string) => void) =>
      safeOn("transcript:partial", cb as IpcCallback),
    onTranscriptFinal: (cb: (text: string) => void) =>
      safeOn("transcript:final", cb as IpcCallback),
  },

  screen: {
    capture: (): Promise<string> =>
      ipcRenderer.invoke("screen:capture"),
    captureCurrent: (): Promise<string> =>
      ipcRenderer.invoke("screen:capture-current-window"),
    getSources: (): Promise<ScreenSource[]> =>
      ipcRenderer.invoke("screen:get-sources"),
  },

  hotkeys: {
    onOACapture: (cb: () => void) =>
      safeOn("hotkey:oa-capture", cb as IpcCallback),
    onCopyAnswer: (cb: () => void) =>
      safeOn("hotkey:copy-answer", cb as IpcCallback),
  },

  system: {
    onSuspend: (cb: () => void) =>
      safeOn("system:suspend", cb as IpcCallback),
    onResume: (cb: () => void) =>
      safeOn("system:resume", cb as IpcCallback),
  },
};

contextBridge.exposeInMainWorld("mentis", mentisAPI);

export type MentisAPI = typeof mentisAPI;

interface SessionConfig {
  company: string;
  role: string;
  department: string;
  mode: "interview" | "oa" | "mock";
}

interface SessionState {
  id: string;
  company: string;
  role: string;
  department: string;
  mode: "interview" | "oa" | "mock";
  startedAt: string;
  qaCount: number;
}

interface SessionSummary {
  sessionId: string;
  duration: number;
  qaCount: number;
  averageConfidence: number;
  topicsEncountered: string[];
}

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

interface ScreenSource {
  id: string;
  name: string;
  thumbnail: string;
  appIcon?: string;
}
