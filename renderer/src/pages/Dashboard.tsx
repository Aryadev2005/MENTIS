import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Zap, Play, Target, TrendingUp, Users, Settings } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { SkillRadar } from "../components/dashboard/SkillRadar";
import { PerformanceChart } from "../components/dashboard/PerformanceChart";
import { SessionHistory } from "../components/dashboard/SessionHistory";
import { useUserStore } from "../store/user.store";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export function Dashboard() {
  const { profile } = useUserStore();
  const navigate = useNavigate();
  const [radarData, setRadarData] = useState<null | { topics: any[]; department: string; overall: number }>(null);
  const [trendData, setTrendData] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [readiness, setReadiness] = useState<null | { readiness_score: number; company: string; message: string; weak_topics: any[] }>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!profile) return;

    const headers = {
      "X-User-Id": profile.id,
      "X-Department": profile.department || "CSE",
    };

    const fetchAll = async () => {
      setIsLoading(true);
      try {
        const [radarRes, trendRes] = await Promise.all([
          fetch(`${API_BASE}/analytics/radar/${profile.department || "CSE"}`, { headers }),
          fetch(`${API_BASE}/analytics/trend`, { headers }),
        ]);

        if (radarRes.ok) setRadarData(await radarRes.json());
        if (trendRes.ok) {
          const trend = await trendRes.json();
          setTrendData(trend);
          setSessions(trend.slice(-6).reverse());
        }

        if (profile.target_companies?.[0]) {
          const readinessRes = await fetch(
            `${API_BASE}/analytics/readiness/${profile.target_companies[0]}`,
            { headers }
          );
          if (readinessRes.ok) setReadiness(await readinessRes.json());
        }
      } catch (e) {
        console.error("Dashboard data fetch failed:", e);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAll();
  }, [profile]);

  return (
    <div className="min-h-screen bg-surface-base text-text-primary p-6">
      <header className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-brand flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" fill="white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-text-primary">MENTIS</h1>
            <p className="text-xs text-text-muted">Your Unfair Advantage</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted">
            Welcome, {profile?.name?.split(" ")[0] || "there"}
          </span>
          <div
            className="px-2 py-0.5 rounded-full text-xs font-medium"
            style={{
              backgroundColor: "rgba(108, 58, 255, 0.15)",
              color: "#6C3AFF",
              border: "1px solid rgba(108, 58, 255, 0.3)",
            }}
          >
            {profile?.plan?.toUpperCase() || "FREE"}
          </div>
        </div>
      </header>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <QuickActionCard
          icon={<Play className="w-5 h-5" />}
          title="Start Interview"
          desc="Live AI copilot"
          color="#6C3AFF"
          onClick={() => navigate("/session?mode=interview")}
        />
        <QuickActionCard
          icon={<Target className="w-5 h-5" />}
          title="OA Mode"
          desc="Solve any question"
          color="#00D4AA"
          onClick={() => navigate("/session?mode=oa")}
        />
        <QuickActionCard
          icon={<Users className="w-5 h-5" />}
          title="Group OA"
          desc="Up to 6 students"
          color="#F59E0B"
          onClick={() => navigate("/session?mode=group")}
          disabled={profile?.plan !== "pro"}
        />
      </div>

      {readiness && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 p-4 rounded-2xl border border-brand-violet/20 bg-gradient-card"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider mb-1">Company Readiness</p>
              <p className="text-sm text-text-primary font-medium">{readiness.message}</p>
              {readiness.weak_topics.length > 0 && (
                <p className="text-xs text-state-warning mt-1">
                  Weak: {readiness.weak_topics.map((t) => t.topic).join(", ")}
                </p>
              )}
            </div>
            <div className="text-4xl font-bold text-brand-violet">
              {readiness.readiness_score}%
            </div>
          </div>
        </motion.div>
      )}

      <div className="grid grid-cols-2 gap-4 mb-4">
        {radarData && (
          <SkillRadar
            topics={radarData.topics}
            department={radarData.department}
            overall={radarData.overall}
          />
        )}
        <PerformanceChart data={trendData} />
      </div>

      <SessionHistory sessions={sessions} />
    </div>
  );
}

function QuickActionCard({
  icon,
  title,
  desc,
  color,
  onClick,
  disabled = false,
}: {
  icon: React.ReactNode;
  title: string;
  desc: string;
  color: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <motion.button
      whileHover={disabled ? {} : { scale: 1.02 }}
      whileTap={disabled ? {} : { scale: 0.98 }}
      onClick={disabled ? undefined : onClick}
      className={`
        p-4 rounded-2xl border text-left transition-all
        ${disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer hover:border-opacity-60"}
      `}
      style={{
        backgroundColor: `${color}08`,
        borderColor: `${color}20`,
      }}
    >
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center mb-3"
        style={{ backgroundColor: `${color}15`, color }}
      >
        {icon}
      </div>
      <p className="text-sm font-semibold text-text-primary">{title}</p>
      <p className="text-xs text-text-muted mt-0.5">{desc}</p>
    </motion.button>
  );
}
