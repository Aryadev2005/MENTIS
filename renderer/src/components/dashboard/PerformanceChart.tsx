import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

interface DataPoint {
  date: string;
  average_confidence: number;
  company?: string;
  qa_count: number;
}

interface PerformanceChartProps {
  data: DataPoint[];
}

export function PerformanceChart({ data }: PerformanceChartProps) {
  const formatted = data.map((d) => ({
    ...d,
    label: new Date(d.date).toLocaleDateString("en-IN", { month: "short", day: "numeric" }),
  }));

  return (
    <div className="bg-surface-card rounded-2xl p-6 border border-white/5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">
            Improvement Trend
          </h3>
          <p className="text-xs text-text-muted mt-0.5">Answer quality over time</p>
        </div>
      </div>

      {data.length === 0 ? (
        <div className="h-48 flex items-center justify-center text-text-muted text-sm">
          No session data yet. Start your first session!
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={formatted} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis
              dataKey="label"
              tick={{ fill: "#A0A0C0", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: "#A0A0C0", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <ReferenceLine y={70} stroke="#F59E0B" strokeDasharray="4 4" strokeOpacity={0.4} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1A1A26",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                color: "#F0F0FF",
                fontSize: "12px",
              }}
              formatter={(value: number) => [`${value}%`, "Confidence"]}
            />
            <Line
              type="monotone"
              dataKey="average_confidence"
              stroke="#6C3AFF"
              strokeWidth={2.5}
              dot={{ fill: "#6C3AFF", r: 3, strokeWidth: 0 }}
              activeDot={{ fill: "#00D4AA", r: 5, strokeWidth: 0 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
