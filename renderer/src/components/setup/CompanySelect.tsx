import { useState } from "react";
import { Search, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const COMPANY_GROUPS = {
  "Product Companies": [
    "Amazon", "Google", "Microsoft", "Flipkart", "Swiggy", "Zepto",
    "Meesho", "Razorpay", "Groww", "Juspay", "Zerodha", "PhonePe",
    "CRED", "Ola", "Uber India",
  ],
  "Mass Recruiters": [
    "TCS", "Infosys", "Wipro", "Accenture", "Cognizant",
    "Capgemini", "HCL", "Tech Mahindra",
  ],
  "Core Engineering": [
    "L&T", "Tata Motors", "Mahindra", "Bosch India", "Cummins",
    "ABB", "Siemens India", "BHEL", "ONGC", "DRDO", "ISRO", "NTPC",
  ],
  "Consulting & Finance": [
    "Deloitte", "EY", "McKinsey", "BCG", "Goldman Sachs",
    "JP Morgan", "Morgan Stanley", "Aon",
  ],
};

interface CompanySelectProps {
  selected: string[];
  onChange: (companies: string[]) => void;
  maxSelect?: number;
}

export function CompanySelect({ selected, onChange, maxSelect = 8 }: CompanySelectProps) {
  const [query, setQuery] = useState("");

  const toggle = (company: string) => {
    if (selected.includes(company)) {
      onChange(selected.filter((c) => c !== company));
    } else if (selected.length < maxSelect) {
      onChange([...selected, company]);
    }
  };

  const filteredGroups = Object.entries(COMPANY_GROUPS)
    .map(([group, companies]) => ({
      group,
      companies: query
        ? companies.filter((c) => c.toLowerCase().includes(query.toLowerCase()))
        : companies,
    }))
    .filter((g) => g.companies.length > 0);

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search companies..."
          className="w-full pl-9 pr-3 py-2 bg-white/5 border border-white/10 rounded-xl text-text-primary text-sm focus:outline-none focus:border-brand-violet/50 placeholder:text-text-muted"
        />
      </div>

      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selected.map((c) => (
            <motion.div
              key={c}
              layout
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="flex items-center gap-1 px-2.5 py-1 bg-brand-violet/15 border border-brand-violet/30 rounded-full text-brand-violet text-xs font-medium"
            >
              {c}
              <button onClick={() => toggle(c)} className="ml-0.5 hover:text-white">
                <X className="w-3 h-3" />
              </button>
            </motion.div>
          ))}
        </div>
      )}

      <div className="max-h-56 overflow-y-auto space-y-3 scrollbar-thin">
        {filteredGroups.map(({ group, companies }) => (
          <div key={group}>
            <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-1.5">{group}</p>
            <div className="flex flex-wrap gap-1.5">
              {companies.map((company) => {
                const isSelected = selected.includes(company);
                const atMax = !isSelected && selected.length >= maxSelect;
                return (
                  <button
                    key={company}
                    onClick={() => toggle(company)}
                    disabled={atMax}
                    className={`
                      px-3 py-1.5 rounded-lg border text-xs font-medium transition-all
                      ${isSelected
                        ? "border-brand-violet bg-brand-violet/15 text-brand-violet"
                        : atMax
                          ? "border-white/5 bg-white/2 text-text-muted cursor-not-allowed opacity-40"
                          : "border-white/10 bg-white/2 text-text-secondary hover:border-brand-violet/30 hover:bg-white/3"
                      }
                    `}
                  >
                    {company}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-text-muted">{selected.length}/{maxSelect} companies selected</p>
    </div>
  );
}
