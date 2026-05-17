import { motion } from "framer-motion";
import { Building2, Clock, Target } from "lucide-react";

interface Session {
  session_id: string;
  date: string;
  company: string;
  average_confidence: number;
  qa_count: number;
}

interface SessionHistoryProps {
  sessions: Session[];
}

export function SessionHistory({ sessions }: SessionHistoryProps) {
  return (
    <div className="bg-surface-card rounded-2xl p-6 border border-white/5">
      <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-4">
        Recent Sessions
      </h3>

      {sessions.length === 0 ? (
        <p className="text-text-muted text-sm text-center py-6">No sessions yet.</p>
      ) : (
        <div className="space-y-2">
          {sessions.slice(0, 6).map((session, i) => (
            <motion.div
              key={session.session_id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="flex items-center justify-between p-3 rounded-xl bg-white/2 border border-white/4 hover:border-brand-violet/20 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-brand-violet/10 flex items-center justify-center">
                  <Building2 className="w-4 h-4 text-brand-violet" />
                </div>
                <div>
                  <p className="text-sm font-medium text-text-primary">{session.company}</p>
                  <p className="text-xs text-text-muted">
                    {new Date(session.date).toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "short",
                    })}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1 text-xs text-text-muted">
                  <Target className="w-3 h-3" />
                  {session.qa_count} Q&As
                </div>
                <div
                  className="text-sm font-semibold"
                  style={{
                    color:
                      session.average_confidence >= 85
                        ? "#00D4AA"
                        : session.average_confidence >= 65
                        ? "#F59E0B"
                        : "#EF4444",
                  }}
                >
                  {session.average_confidence}%
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
