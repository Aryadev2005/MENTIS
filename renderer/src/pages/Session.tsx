import { useEffect, useRef, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, MicOff, Square, Radio, ChevronRight } from "lucide-react";
import { useSessionStore } from "../store/session.store";
import { useUserStore } from "../store/user.store";
import { useAudio } from "../hooks/useAudio";
import { useHotkeys, useElectronHotkeys } from "../hooks/useHotkeys";
import { AnswerCard } from "../components/overlay/AnswerCard";
import { ConfidenceBar } from "../components/overlay/ConfidenceBar";
import { HotkeyHint } from "../components/overlay/HotkeyHint";
import { useStreaming } from "../hooks/useStreaming";
import toast from "react-hot-toast";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export function Session() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const mode = (searchParams.get("mode") || "interview") as "interview" | "oa" | "mock";

  const { profile } = useUserStore();
  const session = useSessionStore();
  const audio = useAudio();
  const { isStreaming, text: streamText, startStream } = useStreaming();

  const [company, setCompany] = useState(profile?.target_companies?.[0] || "");
  const [role, setRole] = useState("Software Engineer");
  const [isSetup, setIsSetup] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [isDetecting, setIsDetecting] = useState(false);

  useElectronHotkeys();

  const headers = {
    "X-User-Id": profile?.id || "",
    "X-Department": profile?.department || "CSE",
    "X-User-Name": profile?.name || "",
  };

  useEffect(() => {
    const handleTranscript = async (e: Event) => {
      const text = (e as CustomEvent<string>).detail;
      setTranscript(text);
      await detectAndAnswer(text);
    };

    window.addEventListener("mentis:final-transcript", handleTranscript);
    return () => window.removeEventListener("mentis:final-transcript", handleTranscript);
  }, [session.sessionId]);

  const detectAndAnswer = async (text: string) => {
    if (!session.sessionId || isDetecting || text.length < 10) return;

    setIsDetecting(true);
    try {
      const res = await fetch(`${API_BASE}/interview/detect`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ transcript: text, session_id: session.sessionId }),
      });

      const detection = await res.json();
      if (!detection.is_question) return;

      session.setCurrentQuestion(detection.question);
      session.setStreaming(true);

      await startStream(
        `${API_BASE}/interview/answer/stream`,
        {
          question: detection.question,
          question_type: detection.question_type,
          session_id: session.sessionId,
          user_id: profile?.id,
          company,
          role,
          department: profile?.department,
        },
        { ...headers, "Content-Type": "application/json" }
      );
    } catch (e) {
      console.error("Detection/answer failed:", e);
    } finally {
      setIsDetecting(false);
    }
  };

  const startSession = async () => {
    if (!company || !role) {
      toast.error("Please enter company and role");
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/interview/session/start`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ company, role, department: profile?.department, mode }),
      });
      const data = await res.json();

      session.startSession({
        sessionId: data.session_id,
        company,
        role,
        department: profile?.department || "CSE",
        mode,
        preBrief: data.pre_session_brief,
        oaFormat: data.oa_format,
      });

      await audio.startCapture();
      setIsSetup(true);

      if (data.pre_session_brief) {
        toast.success(data.pre_session_brief, { duration: 6000 });
      }
    } catch (e) {
      toast.error("Failed to start session");
    }
  };

  const endSession = async () => {
    await audio.stopCapture();
    session.endSession();
    navigate("/");
  };

  if (!isSetup) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md bg-surface-card rounded-2xl p-6 border border-white/5"
        >
          <h2 className="text-xl font-bold text-text-primary mb-6">
            {mode === "interview" ? "Live Interview" : mode === "oa" ? "OA Mode" : "Mock Interview"}
          </h2>

          <div className="space-y-4">
            <div>
              <label className="text-xs text-text-muted mb-1.5 block">Company</label>
              <input
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="e.g. Google, Amazon, TCS"
                className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-xl text-text-primary text-sm focus:outline-none focus:border-brand-violet/50 placeholder:text-text-muted"
              />
            </div>
            <div>
              <label className="text-xs text-text-muted mb-1.5 block">Role</label>
              <input
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="e.g. Software Engineer"
                className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-xl text-text-primary text-sm focus:outline-none focus:border-brand-violet/50 placeholder:text-text-muted"
              />
            </div>
          </div>

          <motion.button
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            onClick={startSession}
            className="w-full mt-6 py-3 rounded-xl bg-gradient-brand text-white font-semibold text-sm flex items-center justify-center gap-2"
          >
            Start Session <ChevronRight className="w-4 h-4" />
          </motion.button>

          <div className="mt-4">
            <HotkeyHint />
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-base p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-state-error/10 border border-state-error/20 rounded-full">
            <motion.div
              className="w-2 h-2 rounded-full bg-state-error"
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 1.2, repeat: Infinity }}
            />
            <span className="text-xs font-medium text-state-error">LIVE</span>
          </div>
          <div>
            <p className="text-sm font-semibold text-text-primary">{company}</p>
            <p className="text-xs text-text-muted">{role} · {mode}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs text-text-muted">
            {audio.isCapturing ? (
              <>
                <Radio className="w-3.5 h-3.5 text-brand-teal" />
                <span>Listening...</span>
              </>
            ) : (
              <>
                <MicOff className="w-3.5 h-3.5 text-state-error" />
                <span>Audio off</span>
              </>
            )}
          </div>

          <button
            onClick={endSession}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-state-error/10 border border-state-error/20 rounded-xl text-state-error text-xs font-medium hover:bg-state-error/20 transition-colors"
          >
            <Square className="w-3 h-3" fill="currentColor" />
            End Session
          </button>
        </div>
      </div>

      {transcript && (
        <div className="mb-4 p-3 bg-white/2 rounded-xl border border-white/5">
          <p className="text-xs text-text-muted mb-1">Transcript</p>
          <p className="text-sm text-text-secondary">{transcript}</p>
        </div>
      )}

      <AnimatePresence>
        {(isStreaming || streamText) && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="mb-4"
          >
            <AnswerCard />
            {session.confidence !== null && (
              <div className="mt-2">
                <ConfidenceBar confidence={session.confidence} />
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="space-y-3 mt-6">
        {session.qaPairs.slice().reverse().map((qa) => (
          <div
            key={qa.id}
            className="p-4 bg-surface-card rounded-xl border border-white/5"
          >
            <p className="text-xs text-text-muted mb-1">{qa.question_type}</p>
            <p className="text-sm font-medium text-text-secondary mb-2">{qa.question}</p>
            <p className="text-sm text-text-primary">{qa.answer}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
