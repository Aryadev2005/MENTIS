import { motion, AnimatePresence } from "framer-motion";
import { Copy, X, AlertTriangle, CheckCircle, Zap } from "lucide-react";
import { useOverlayStore } from "../../store/overlay.store";

interface AnswerCardProps {
  compact?: boolean;
}

export function AnswerCard({ compact = false }: AnswerCardProps) {
  const { streamText, confidence, warning, isStreaming, oaSolution, mode, clear } =
    useOverlayStore();

  const text = mode === "oa" ? oaSolution?.answer : streamText;
  const conf = mode === "oa" ? oaSolution?.confidence : confidence;
  const warn = mode === "oa" ? oaSolution?.warning : warning;

  if (!text && !isStreaming) return null;

  const copyToClipboard = () => {
    if (text) navigator.clipboard.writeText(text);
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -12, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -8, scale: 0.97 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
        className={`
          relative rounded-2xl border border-white/10 shadow-card-elevated
          bg-surface-overlay backdrop-blur-md
          ${compact ? "p-3" : "p-4"}
        `}
        style={{
          background: "rgba(10, 10, 15, 0.92)",
          backdropFilter: "blur(20px)",
        }}
      >
        <div className="absolute top-0 left-0 right-0 h-0.5 rounded-t-2xl bg-gradient-brand opacity-80" />

        <div className="flex items-center justify-between mb-2.5">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-brand-violet" fill="currentColor" />
              <span className="text-xs font-semibold text-brand-violet tracking-wide uppercase">
                MENTIS
              </span>
            </div>
            {isStreaming && (
              <div className="flex gap-0.5">
                {[0, 1, 2].map((i) => (
                  <motion.div
                    key={i}
                    className="w-1 h-1 rounded-full bg-brand-teal"
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
                  />
                ))}
              </div>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            {conf !== null && conf !== undefined && (
              <ConfidencePill confidence={conf} />
            )}
            <button
              onClick={copyToClipboard}
              className="p-1 rounded-lg hover:bg-white/5 transition-colors text-text-muted hover:text-text-secondary"
            >
              <Copy className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={clear}
              className="p-1 rounded-lg hover:bg-white/5 transition-colors text-text-muted hover:text-text-secondary"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className={`text-text-primary leading-relaxed ${compact ? "text-xs" : "text-sm"}`}>
          {text}
          {isStreaming && (
            <motion.span
              className="inline-block w-0.5 h-4 bg-brand-violet ml-0.5 align-middle"
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.6, repeat: Infinity }}
            />
          )}
        </div>

        {warn && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            className="mt-2.5 flex items-start gap-2 bg-state-warning/10 rounded-lg px-2.5 py-2 border border-state-warning/20"
          >
            <AlertTriangle className="w-3.5 h-3.5 text-state-warning mt-0.5 shrink-0" />
            <p className="text-xs text-state-warning/90 leading-snug">{warn}</p>
          </motion.div>
        )}

        {mode === "oa" && oaSolution?.code && (
          <div className="mt-2.5 bg-black/30 rounded-lg p-2.5 border border-white/5">
            <p className="text-xs font-mono text-brand-teal whitespace-pre-wrap leading-relaxed">
              {oaSolution.code}
            </p>
          </div>
        )}

        <div className="absolute bottom-0 right-0 w-16 h-16 opacity-5 pointer-events-none">
          <div className="w-full h-full rounded-tl-full bg-gradient-brand" />
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

function ConfidencePill({ confidence }: { confidence: number }) {
  const color =
    confidence >= 85 ? "#00D4AA" : confidence >= 65 ? "#F59E0B" : "#EF4444";
  const label =
    confidence >= 85 ? "High" : confidence >= 65 ? "Medium" : "Low";

  return (
    <div
      className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ backgroundColor: `${color}15`, color, border: `1px solid ${color}30` }}
    >
      <CheckCircle className="w-2.5 h-2.5" />
      {confidence}% {label}
    </div>
  );
}
