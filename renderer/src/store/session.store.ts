import { create } from "zustand";

interface QAPair {
  id: string;
  question: string;
  answer: string;
  confidence: number;
  question_type: string;
  timestamp: string;
  feedback: "helpful" | "not_helpful" | "partially_helpful" | null;
}

interface SessionState {
  sessionId: string | null;
  isActive: boolean;
  company: string;
  role: string;
  department: string;
  mode: "interview" | "oa" | "mock";
  startedAt: string | null;
  qaPairs: QAPair[];
  currentQuestion: string | null;
  currentAnswer: string;
  isStreaming: boolean;
  confidence: number | null;
  warning: string | null;
  preBrief: string | null;
  oaFormat: Record<string, unknown> | null;

  startSession: (config: {
    sessionId: string;
    company: string;
    role: string;
    department: string;
    mode: "interview" | "oa" | "mock";
    preBrief?: string;
    oaFormat?: Record<string, unknown> | null;
  }) => void;
  endSession: () => void;
  setCurrentQuestion: (question: string | null) => void;
  appendToken: (token: string) => void;
  completeAnswer: (answer: string, confidence: number, warning?: string | null) => void;
  clearCurrentAnswer: () => void;
  addQAPair: (qa: QAPair) => void;
  setFeedback: (qaId: string, feedback: QAPair["feedback"]) => void;
  setStreaming: (streaming: boolean) => void;
  setConfidence: (confidence: number | null) => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessionId: null,
  isActive: false,
  company: "",
  role: "",
  department: "CSE",
  mode: "interview",
  startedAt: null,
  qaPairs: [],
  currentQuestion: null,
  currentAnswer: "",
  isStreaming: false,
  confidence: null,
  warning: null,
  preBrief: null,
  oaFormat: null,

  startSession: (config) =>
    set({
      sessionId: config.sessionId,
      isActive: true,
      company: config.company,
      role: config.role,
      department: config.department,
      mode: config.mode,
      startedAt: new Date().toISOString(),
      qaPairs: [],
      currentQuestion: null,
      currentAnswer: "",
      isStreaming: false,
      confidence: null,
      warning: null,
      preBrief: config.preBrief || null,
      oaFormat: config.oaFormat || null,
    }),

  endSession: () =>
    set({
      sessionId: null,
      isActive: false,
      currentQuestion: null,
      currentAnswer: "",
      isStreaming: false,
    }),

  setCurrentQuestion: (question) =>
    set({ currentQuestion: question, currentAnswer: "", confidence: null, warning: null }),

  appendToken: (token) =>
    set((state) => ({ currentAnswer: state.currentAnswer + token })),

  completeAnswer: (answer, confidence, warning = null) =>
    set({ currentAnswer: answer, confidence, warning, isStreaming: false }),

  clearCurrentAnswer: () =>
    set({ currentAnswer: "", currentQuestion: null, confidence: null, warning: null }),

  addQAPair: (qa) =>
    set((state) => ({ qaPairs: [...state.qaPairs, qa] })),

  setFeedback: (qaId, feedback) =>
    set((state) => ({
      qaPairs: state.qaPairs.map((qa) =>
        qa.id === qaId ? { ...qa, feedback } : qa
      ),
    })),

  setStreaming: (streaming) => set({ isStreaming: streaming }),

  setConfidence: (confidence) => set({ confidence }),
}));
