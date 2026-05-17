import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

interface RadarTopic {
  topic: string;
  score: number;
  attempts: number;
}

interface SkillRadarProps {
  topics: RadarTopic[];
  department: string;
  overall: number;
}

export function SkillRadar({ topics, department, overall }: SkillRadarProps) {
  const data = topics.map((t) => ({
    subject: t.topic,
    score: t.score,
    fullMark: 100,
  }));

  const grade =
    overall >= 85 ? "S" : overall >= 70 ? "A" : overall >= 55 ? "B" : overall >= 40 ? "C" : "D";

  return (
    <div className="bg-surface-card rounded-2xl p-6 border border-white/5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">
            Skill Radar
          </h3>
          <p className="text-xs text-text-muted mt-0.5">{department} · All topics</p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-brand-violet">{grade}</div>
          <div className="text-xs text-text-muted">{overall}% overall</div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <RadarChart data={data} margin={{ top: 10, right: 30, left: 30, bottom: 10 }}>
          <PolarGrid stroke="rgba(255,255,255,0.06)" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: "#A0A0C0", fontSize: 11 }}
          />
          <Radar
            name="Score"
            dataKey="score"
            stroke="#6C3AFF"
            fill="#6C3AFF"
            fillOpacity={0.2}
            strokeWidth={2}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1A1A26",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "8px",
              color: "#F0F0FF",
              fontSize: "12px",
            }}
            formatter={(value: number) => [`${value}%`, "Score"]}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
