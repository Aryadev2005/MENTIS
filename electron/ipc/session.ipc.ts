import { ipcMain, BrowserWindow } from "electron";
import { randomUUID } from "crypto";

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

interface QAPair {
  question: string;
  answer: string;
  confidence: number;
  timestamp: string;
  type: string;
}

let currentSession: SessionState | null = null;
const sessionQAPairs: QAPair[] = [];

export function registerSessionIPC(window: BrowserWindow | null): void {
  ipcMain.handle("session:start", async (_event, config: SessionConfig): Promise<string> => {
    if (currentSession) {
      console.warn("[Session IPC] Session already active, ending it first");
      await endCurrentSession();
    }

    const sessionId = randomUUID();
    currentSession = {
      id: sessionId,
      company: config.company,
      role: config.role,
      department: config.department,
      mode: config.mode,
      startedAt: new Date().toISOString(),
      qaCount: 0,
    };
    sessionQAPairs.length = 0;

    window?.webContents.send("session:started", sessionId);
    console.log(`[Session IPC] Session started: ${sessionId} (${config.mode} at ${config.company})`);

    return sessionId;
  });

  ipcMain.handle("session:end", async (_event, sessionId: string): Promise<SessionSummary> => {
    if (!currentSession || currentSession.id !== sessionId) {
      throw new Error(`No active session with id: ${sessionId}`);
    }

    const summary = await endCurrentSession();
    window?.webContents.send("session:ended", summary);
    return summary;
  });

  ipcMain.handle("session:get-current", async (): Promise<SessionState | null> => {
    return currentSession;
  });

  ipcMain.on("session:record-qa", (_event, qa: QAPair) => {
    if (currentSession) {
      sessionQAPairs.push(qa);
      currentSession.qaCount = sessionQAPairs.length;
    }
  });

  ipcMain.handle("session:get-qa-pairs", async (): Promise<QAPair[]> => {
    return [...sessionQAPairs];
  });
}

async function endCurrentSession(): Promise<SessionSummary> {
  if (!currentSession) {
    throw new Error("No active session to end");
  }

  const startTime = new Date(currentSession.startedAt).getTime();
  const duration = Math.floor((Date.now() - startTime) / 1000);

  const avgConfidence =
    sessionQAPairs.length > 0
      ? sessionQAPairs.reduce((sum, qa) => sum + qa.confidence, 0) / sessionQAPairs.length
      : 0;

  const topicsSet = new Set<string>(
    sessionQAPairs.map((qa) => qa.type).filter(Boolean)
  );

  const summary: SessionSummary = {
    sessionId: currentSession.id,
    duration,
    qaCount: sessionQAPairs.length,
    averageConfidence: Math.round(avgConfidence),
    topicsEncountered: Array.from(topicsSet),
  };

  console.log(
    `[Session IPC] Session ended: ${currentSession.id} | Duration: ${duration}s | Q&As: ${sessionQAPairs.length}`
  );

  currentSession = null;
  sessionQAPairs.length = 0;

  return summary;
}
