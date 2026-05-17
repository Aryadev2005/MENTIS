import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { SkillRadar } from "../components/dashboard/SkillRadar";
import { PerformanceChart } from "../components/dashboard/PerformanceChart";
import { useUserStore } from "../store/user.store";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export function Analytics() {
  const { profile } = useUserStore();
  const [radarData, setRadarData] = useState<any>(null);
  const [trendData, setTrendData] = useState<any[]>([]);
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [readiness, setReadiness] = useState<any>(null);

  useEffect(() => {
    if (!profile) return;

    const headers = {
      "X-User-Id": profile.id,
      "X-Department": profile.department || "CSE",
    };

    Promise.all([
      fetch(`${API_BASE}/analytics/radar/${profile.department || "CSE"}`, { headers }).then((r) => r.json()),
      fetch(`${API_BASE}/analytics/trend`, { headers }).then((r) => r.json()),
      fetch(`${API_BASE}/analytics/heatmap?days=90`, { headers }).then((r) => r.json()),
    ]).then(([radar, trend, heat]) => {
      setRadarData(radar);
      setTrendData(trend);
      setHeatmap(heat);
    });

    if (profile.target_companies?.[0]) {
      fetch(`${API_BASE}/analytics/readiness/${profile.target_companies[0]}`, { headers })
        .then((r) => r.json())
        .then(setReadiness);
    }
  }, [profile]);

  return (
    <div className="min-h-screen bg-surface-base text-text-primary p-6">
      <h1 className="text-xl font-bold mb-6">Performance Analytics</h1>

      {readiness && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 p-5 rounded-2xl bg-gradient-card border border-brand-violet/20"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider mb-1">{readiness.company} Readiness</p>
              <p className="text-sm text-text-primary">{readiness.message}</p>
              {readiness.weak_topics.length > 0 && (
                <p className="text-xs text-state-warning mt-1.5">
                  Focus on: {readiness.weak_topics.map((t: any) => t.topic).join(" · ")}
                </p>
              )}
            </div>
            <div className="text-5xl font-black text-brand-violet">{readiness.readiness_score}%</div>
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

      {heatmap.length > 0 && (
        <div className="bg-surface-card rounded-2xl p-6 border border-white/5">
          <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-4">
            Session Heatmap
          </h3>
          <HeatmapGrid data={heatmap} />
        </div>
      )}
    </div>
  );
}

function HeatmapGrid({ data }: { data: { date: string; count: number; level: number }[] }) {
  const colors = ["#1A1A26", "#6C3AFF30", "#6C3AFF60", "#6C3AFF90", "#6C3AFF"];

  return (
    <div className="flex flex-wrap gap-1">
      {data.map((d) => (
        <div
          key={d.date}
          title={`${d.date}: ${d.count} session${d.count !== 1 ? "s" : ""}`}
          className="w-3 h-3 rounded-sm cursor-pointer transition-transform hover:scale-125"
          style={{ backgroundColor: colors[d.level] || colors[0] }}
        />
      ))}
    </div>
  );
}
