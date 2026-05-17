import { motion } from "framer-motion";

type Department = "CSE" | "ECE" | "Mechanical" | "Civil" | "Chemical" | "EEE" | "Other";

const DEPARTMENTS: Array<{ id: Department; label: string; icon: string; desc: string }> = [
  { id: "CSE", label: "Computer Science", icon: "💻", desc: "Software, AI, Data Science" },
  { id: "ECE", label: "Electronics & Comm", icon: "⚡", desc: "VLSI, Embedded, Signals" },
  { id: "Mechanical", label: "Mechanical", icon: "⚙️", desc: "Thermal, Manufacturing, Design" },
  { id: "Civil", label: "Civil", icon: "🏗️", desc: "Structural, Geotechnical, Transport" },
  { id: "Chemical", label: "Chemical", icon: "🧪", desc: "Process, Reaction, Heat Transfer" },
  { id: "EEE", label: "Electrical", icon: "🔌", desc: "Power Systems, Machines, Control" },
  { id: "Other", label: "Other Branch", icon: "📐", desc: "Other engineering disciplines" },
];

interface DepartmentSelectProps {
  value: Department;
  onChange: (dept: Department) => void;
}

export function DepartmentSelect({ value, onChange }: DepartmentSelectProps) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {DEPARTMENTS.map((dept, i) => (
        <motion.button
          key={dept.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.04 }}
          onClick={() => onChange(dept.id)}
          className={`
            p-3 rounded-xl border text-left transition-all
            ${value === dept.id
              ? "border-brand-violet bg-brand-violet/15"
              : "border-white/10 bg-white/2 hover:border-brand-violet/30 hover:bg-white/3"
            }
          `}
        >
          <div className="flex items-start gap-2">
            <span className="text-lg leading-none">{dept.icon}</span>
            <div>
              <p className={`text-sm font-medium ${value === dept.id ? "text-brand-violet" : "text-text-primary"}`}>
                {dept.label}
              </p>
              <p className="text-xs text-text-muted mt-0.5">{dept.desc}</p>
            </div>
          </div>
        </motion.button>
      ))}
    </div>
  );
}
