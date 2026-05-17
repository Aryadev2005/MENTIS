import { useState } from "react";
import { Sparkles, Loader2 } from "lucide-react";

interface JDKeywords {
  technical: string[];
  behavioral: string[];
  domain: string[];
}

interface JobDescriptionInputProps {
  value: string;
  onChange: (jd: string) => void;
  onKeywordsExtracted?: (keywords: JDKeywords) => void;
  apiBase: string;
  userId: string;
}

export function JobDescriptionInput({
  value,
  onChange,
  onKeywordsExtracted,
  apiBase,
  userId,
}: JobDescriptionInputProps) {
  const [isExtracting, setIsExtracting] = useState(false);
  const [keywords, setKeywords] = useState<JDKeywords | null>(null);

  const extractKeywords = async () => {
    if (!value.trim() || value.length < 100) return;
    setIsExtracting(true);

    try {
      const res = await fetch(`${apiBase}/interview/jd/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-User-Id": userId },
        body: JSON.stringify({ jd_text: value }),
      });

      if (res.ok) {
        const data = await res.json();
        setKeywords(data.keywords);
        onKeywordsExtracted?.(data.keywords);
      }
    } catch {
      // Non-blocking — JD extraction is optional
    } finally {
      setIsExtracting(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="relative">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Paste the job description here (optional but recommended)&#10;&#10;We'll extract key competencies and tailor your interview answers accordingly..."
          rows={6}
          className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-xl text-text-primary text-sm focus:outline-none focus:border-brand-violet/50 placeholder:text-text-muted resize-none leading-relaxed"
        />
        <p className="absolute bottom-2 right-3 text-xs text-text-muted">{value.length}/5000</p>
      </div>

      {value.length >= 100 && (
        <button
          onClick={extractKeywords}
          disabled={isExtracting}
          className="flex items-center gap-2 px-3 py-2 bg-brand-violet/10 border border-brand-violet/20 rounded-xl text-brand-violet text-xs font-medium hover:bg-brand-violet/20 transition-colors disabled:opacity-50"
        >
          {isExtracting ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Sparkles className="w-3.5 h-3.5" />
          )}
          Extract Key Competencies
        </button>
      )}

      {keywords && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Extracted Keywords</p>
          {Object.entries(keywords).map(([category, words]) =>
            words.length > 0 ? (
              <div key={category}>
                <p className="text-xs text-text-muted capitalize mb-1">{category}</p>
                <div className="flex flex-wrap gap-1">
                  {words.map((w: string) => (
                    <span key={w} className="px-2 py-0.5 bg-white/5 border border-white/10 rounded-full text-xs text-text-secondary">
                      {w}
                    </span>
                  ))}
                </div>
              </div>
            ) : null
          )}
        </div>
      )}
    </div>
  );
}
