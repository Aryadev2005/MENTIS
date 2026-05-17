import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Camera, Loader2, CheckCircle, AlertTriangle, XCircle,
  Code2, Brain, ChevronDown, ChevronUp, Copy, ThumbsUp,
} from "lucide-react";
import { useSessionStore } from "../../store/session.store";
import { useUserStore } from "../../store/user.store";

interface OASolution {
  question_type: string;
  approach: string | null;
  answer: string;
  explanation: string;
  code: string | null;
  time_complexity: string | null;
  confidence: number;
  confidence_color: "green" | "yellow" | "red";
  confidence_label: string;
  warning: string | null;
  similar_found: boolean;
}

interface OASolverProps {
  apiBase: string;
}

const TYPE_LABELS: Record<string, string> = {
  coding: "Coding Problem",
  mcq_aptitude: "Aptitude MCQ",
  mcq_technical_cs: "CS Technical",
  mcq_technical_ece: "ECE Technical",
  mcq_technical_mech: "Mech Technical",
  mcq_technical_civil: "Civil Technical",
  mcq_technical_chem: "Chem Technical",
  debugging: "Debugging",
  output_prediction: "Output Prediction",
};

const CONFIDENCE_COLORS = {
  green: { bg: "bg-state-success/10", border: "border-state-success/30", text: "text-state-success" },
  yellow: { bg: "bg-state-warning/10", border: "border-state-warning/30", text: "text-state-warning" },
  red: { bg: "bg-state-error/10", border: "border-state-error/30", text: "text-state-error" },
};

export function OASolver({ apiBase }: OASolverProps) {
  const { profile } = useUserStore();
  const session = useSessionStore();
  const [solution, setSolution] = useState<OASolution | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [isSolving, setIsSolving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCode, setShowCode] = useState(false);
  const [contributed, setContributed] = useState(false);
  const [autoDismissTimer, setAutoDismissTimer] = useState<number | null>(null);

  useEffect(() => {
    const handleOACapture = () => captureAndSolve();
    window.addEventListener("mentis:oa-capture", handleOACapture);
    return () => window.removeEventListener("mentis:oa-capture", handleOACapture);
  }, [session.sessionId]);

  useEffect(() => {
    if (solution) {
      const timer = window.setTimeout(() => setSolution(null), 60000);
      setAutoDismissTimer(timer);
      return () => clearTimeout(timer);
    }
  }, [solution]);

  const captureAndSolve = async () => {
    if (isCapturing || isSolving) return;
    setError(null);
    setSolution(null);
    setContributed(false);

    setIsCapturing(true);
    let screenshotB64 = "";

    try {
      if (typeof window.mentis !== "undefined") {
        const dataUrl = await window.mentis.screen.captureCurrent();
        screenshotB64 = dataUrl.replace(/^data:image\/[a-z]+;base64,/, "");
      } else {
        setError("Screen capture requires the Electron app.");
        return;
      }
    } catch (err) {
      setError("Screen capture failed. Make sure MENTIS has screen recording permission.");
      return;
    } finally {
      setIsCapturing(false);
    }

    setIsSolving(true);
    try {
      const res = await fetch(`${apiBase}/oa/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          screenshot_b64: screenshotB64,
          session_id: session.sessionId || "standalone",
          user_id: profile?.id || "",
          department: profile?.department || "CSE",
          company: session.company || undefined,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "OA solve failed");
      }

      const sol: OASolution = await res.json();
      setSolution(sol);
    } catch (err) {
      setError(err instanceof Error ? err.message : "OA solve failed. Try again.");
    } finally {
      setIsSolving(false);
    }
  };

  const copyAnswer = () => {
    if (!solution) return;
    const text = solution.code
      ? `${solution.answer}\n\n${solution.code}`
      : solution.answer;
    navigator.clipboard.writeText(text);
  };

  const contribute = async () => {
    if (!solution || !session.sessionId || contributed) return;
    try {
      await fetch(`${apiBase}/oa/contribute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question_text: solution.explanation.slice(0, 500),
          question_type: solution.question_type,
          answer: solution.answer,
          company: session.company || "Unknown",
          department: profile?.department || "CSE",
          user_id: profile?.id || "",
          session_id: session.sessionId,
        }),
      });
      setContributed(true);
    } catch {
      // non-blocking
    }
  };

  const colors = solution ? CONFIDENCE_COLORS[solution.confidence_color] : null;

  return (
    <div className="space-y-3">
      <motion.button
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.98 }}
        onClick={captureAndSolve}
        disabled={isCapturing || isSolving}
        className={`
          w-full py-4 rounded-2xl border-2 border-dashed font-semibold text-sm
          flex items-center justify-center gap-3 transition-all
          ${isCapturing || isSolving
            ? "border-brand-violet/40 bg-brand-violet/5 text-brand-violet cursor-not-allowed"
            : "border-brand-violet/30 hover:border-brand-violet hover:bg-brand-violet/10 text-text-secondary hover:text-brand-violet"
          }
        `}
      >
        {isCapturing ? (
          <>
            <Camera className="w-5 h-5 animate-pulse" />
            Capturing screen...
          </>
        ) : isSolving ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Solving with AI...</span>
          </>
        ) : (
          <>
            <Camera className="w-5 h-5" />
            <span>Capture & Solve OA Question</span>
            <kbd className="text-xs px-1.5 py-0.5 bg-white/5 border border-white/10 rounded font-mono">
              ⌘⇧S
            </kbd>
          </>
        )}
      </motion.button>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-start gap-2 p-3 bg-state-error/10 border border-state-error/20 rounded-xl"
        >
          <XCircle className="w-4 h-4 text-state-error shrink-0 mt-0.5" />
          <p className="text-sm text-state-error">{error}</p>
        </motion.div>
      )}

      <AnimatePresence>
        {solution && colors && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className={`rounded-2xl border p-4 space-y-3 ${colors.bg} ${colors.border}`}
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Brain className="w-4 h-4 text-brand-violet" />
                  <span className="text-xs font-semibold text-brand-violet uppercase tracking-wide">
                    {TYPE_LABELS[solution.question_type] || solution.question_type}
                  </span>
                  {solution.similar_found && (
                    <span className="text-xs px-1.5 py-0.5 bg-brand-teal/15 text-brand-teal border border-brand-teal/20 rounded-full">
                      Matched from DB
                    </span>
                  )}
                </div>
                <div className={`flex items-center gap-1.5 text-sm font-semibold ${colors.text}`}>
                  {solution.confidence_color === "green" ? (
                    <CheckCircle className="w-4 h-4" />
                  ) : solution.confidence_color === "yellow" ? (
                    <AlertTriangle className="w-4 h-4" />
                  ) : (
                    <XCircle className="w-4 h-4" />
                  )}
                  {solution.confidence}% confidence · {solution.confidence_label}
                </div>
              </div>

              <div className="flex items-center gap-1.5">
                <button onClick={copyAnswer} className="p-1.5 rounded-lg hover:bg-white/10 text-text-muted hover:text-text-primary transition-colors">
                  <Copy className="w-4 h-4" />
                </button>
                <button onClick={() => setSolution(null)} className="p-1.5 rounded-lg hover:bg-white/10 text-text-muted hover:text-text-primary transition-colors">
                  <XCircle className="w-4 h-4" />
                </button>
              </div>
            </div>

            {solution.approach && (
              <div className="bg-black/20 rounded-xl p-3">
                <p className="text-xs text-text-muted mb-1 uppercase tracking-wider font-semibold">Approach</p>
                <p className="text-sm text-text-primary leading-relaxed">{solution.approach}</p>
              </div>
            )}

            <div>
              <p className="text-sm text-text-primary leading-relaxed whitespace-pre-wrap">{solution.answer}</p>
            </div>

            {solution.time_complexity && (
              <div className="flex items-center gap-2 text-xs text-text-muted">
                <span className="font-mono bg-white/5 px-2 py-0.5 rounded">
                  Time: {solution.time_complexity}
                </span>
              </div>
            )}

            {solution.code && (
              <div>
                <button
                  onClick={() => setShowCode(!showCode)}
                  className="flex items-center gap-1.5 text-xs text-brand-teal font-medium mb-2"
                >
                  <Code2 className="w-3.5 h-3.5" />
                  {showCode ? "Hide Code" : "Show Code"}
                  {showCode ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>

                <AnimatePresence>
                  {showCode && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="bg-black/40 rounded-xl p-3 border border-white/5 overflow-x-auto">
                        <pre className="text-xs font-mono text-brand-teal whitespace-pre-wrap leading-relaxed">
                          {solution.code}
                        </pre>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}

            {solution.warning && (
              <div className="flex items-start gap-2 bg-state-warning/10 rounded-lg px-2.5 py-2 border border-state-warning/20">
                <AlertTriangle className="w-3.5 h-3.5 text-state-warning mt-0.5 shrink-0" />
                <p className="text-xs text-state-warning/90">{solution.warning}</p>
              </div>
            )}

            <div className="flex items-center justify-between pt-1 border-t border-white/5">
              <p className="text-xs text-text-muted">Auto-dismisses in 60s</p>
              {!contributed ? (
                <button
                  onClick={contribute}
                  className="flex items-center gap-1.5 text-xs text-text-muted hover:text-brand-teal transition-colors"
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                  This appeared in my OA
                </button>
              ) : (
                <span className="text-xs text-brand-teal flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" /> Contributed to DB!
                </span>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
