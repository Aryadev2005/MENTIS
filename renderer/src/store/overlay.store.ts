import { create } from "zustand";

interface OASolution {
  question_type: string;
  answer: string;
  explanation: string;
  code: string | null;
  approach: string | null;
  time_complexity: string | null;
  confidence: number;
  confidence_color: "green" | "yellow" | "red";
  confidence_label: string;
  warning: string | null;
  similar_found: boolean;
}

interface OverlayState {
  isVisible: boolean;
  isStreaming: boolean;
  streamText: string;
  confidence: number | null;
  warning: string | null;
  oaSolution: OASolution | null;
  mode: "interview" | "oa";
  autoDismissMs: number;

  show: () => void;
  hide: () => void;
  toggle: () => void;
  appendToken: (token: string) => void;
  setComplete: (answer: string, confidence: number, warning?: string | null) => void;
  setOASolution: (solution: OASolution) => void;
  clear: () => void;
  setMode: (mode: "interview" | "oa") => void;
  setAutoDismiss: (ms: number) => void;
}

export const useOverlayStore = create<OverlayState>((set, get) => ({
  isVisible: false,
  isStreaming: false,
  streamText: "",
  confidence: null,
  warning: null,
  oaSolution: null,
  mode: "interview",
  autoDismissMs: 60000,

  show: () => set({ isVisible: true }),
  hide: () => set({ isVisible: false }),
  toggle: () => set((state) => ({ isVisible: !state.isVisible })),

  appendToken: (token) =>
    set((state) => ({
      streamText: state.streamText + token,
      isStreaming: true,
      isVisible: true,
    })),

  setComplete: (answer, confidence, warning = null) =>
    set({
      streamText: answer,
      confidence,
      warning,
      isStreaming: false,
      isVisible: true,
    }),

  setOASolution: (solution) =>
    set({ oaSolution: solution, isVisible: true, mode: "oa", isStreaming: false }),

  clear: () =>
    set({
      streamText: "",
      confidence: null,
      warning: null,
      oaSolution: null,
      isStreaming: false,
    }),

  setMode: (mode) => set({ mode }),
  setAutoDismiss: (ms) => set({ autoDismissMs: ms }),
}));
