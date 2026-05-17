import { motion } from "framer-motion";

interface ConfidenceBarProps {
  confidence: number;
  showLabel?: boolean;
}

export function ConfidenceBar({ confidence, showLabel = true }: ConfidenceBarProps) {
  const color =
    confidence >= 85 ? "#00D4AA" : confidence >= 65 ? "#F59E0B" : "#EF4444";

  const label =
    confidence >= 85 ? "High Confidence" : confidence >= 65 ? "Medium Confidence" : "Low — Verify";

  return (
    <div className="space-y-1">
      {showLabel && (
        <div className="flex justify-between items-center text-xs">
          <span className="text-text-muted">Confidence</span>
          <span className="font-semibold" style={{ color }}>
            {confidence}% · {label}
          </span>
        </div>
      )}
      <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={{ width: `${confidence}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}
