import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, CheckCircle, AlertCircle, FileText, X, Loader2 } from "lucide-react";

interface ParsedResume {
  name: string;
  email: string;
  skills: Array<{ skill: string; proficiency_level: string }>;
  experiences: Array<{ company: string; role: string; duration: string }>;
  projects: Array<{ name: string; tech_stack: string[] }>;
  skill_summary: string;
}

interface ResumeUploadProps {
  userId: string;
  apiBase: string;
  onParsed: (parsed: ParsedResume) => void;
  onSkip: () => void;
}

export function ResumeUpload({ userId, apiBase, onParsed, onSkip }: ResumeUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [parsed, setParsed] = useState<ParsedResume | null>(null);

  const handleFile = useCallback((f: File) => {
    const allowed = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"];
    if (!allowed.includes(f.type) && !f.name.endsWith(".pdf") && !f.name.endsWith(".docx")) {
      setError("Please upload a PDF or DOCX file.");
      return;
    }
    if (f.size > 5 * 1024 * 1024) {
      setError("File too large. Maximum 5MB.");
      return;
    }
    setFile(f);
    setError(null);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const dropped = e.dataTransfer.files[0];
      if (dropped) handleFile(dropped);
    },
    [handleFile]
  );

  const upload = async () => {
    if (!file) return;
    setIsUploading(true);
    setError(null);

    try {
      const form = new FormData();
      form.append("file", file);

      const res = await fetch(`${apiBase}/user/onboarding/step/4/resume`, {
        method: "POST",
        headers: { "X-User-Id": userId },
        body: form,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }

      const data = await res.json();
      setParsed(data.parsed);
      onParsed(data.parsed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed. Try again.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <AnimatePresence mode="wait">
        {!parsed ? (
          <motion.div key="upload" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <label>
              <input
                type="file"
                accept=".pdf,.docx,.doc"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
              />
              <div
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                className={`
                  cursor-pointer p-8 rounded-xl border-2 border-dashed text-center transition-all
                  ${isDragging ? "border-brand-violet bg-brand-violet/10" : ""}
                  ${file && !error ? "border-brand-teal/50 bg-brand-teal/5" : ""}
                  ${error ? "border-state-error/50 bg-state-error/5" : ""}
                  ${!file && !isDragging && !error ? "border-white/10 hover:border-brand-violet/40 hover:bg-white/2" : ""}
                `}
              >
                {file && !error ? (
                  <div className="flex items-center justify-center gap-3 text-brand-teal">
                    <FileText className="w-6 h-6" />
                    <div className="text-left">
                      <p className="text-sm font-medium">{file.name}</p>
                      <p className="text-xs text-text-muted">{(file.size / 1024).toFixed(0)} KB</p>
                    </div>
                    <button
                      onClick={(e) => { e.preventDefault(); setFile(null); }}
                      className="p-1 rounded-lg hover:bg-white/10"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <>
                    <Upload className="w-8 h-8 text-text-muted mx-auto mb-3" />
                    <p className="text-sm font-medium text-text-secondary">
                      {isDragging ? "Drop it!" : "Drag & drop your resume"}
                    </p>
                    <p className="text-xs text-text-muted mt-1">PDF or DOCX · Max 5MB</p>
                  </>
                )}
              </div>
            </label>

            {error && (
              <div className="flex items-center gap-2 text-state-error text-xs mt-2">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                {error}
              </div>
            )}

            <div className="flex gap-2 mt-3">
              <button
                onClick={onSkip}
                className="flex-1 py-2.5 rounded-xl border border-white/10 text-text-muted text-sm hover:bg-white/3 transition-colors"
              >
                Skip for now
              </button>
              <motion.button
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                onClick={upload}
                disabled={!file || isUploading}
                className="flex-1 py-2.5 rounded-xl bg-gradient-brand text-white text-sm font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Upload & Parse →"}
              </motion.button>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="parsed"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-3"
          >
            <div className="p-3 bg-brand-teal/5 border border-brand-teal/20 rounded-xl flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-brand-teal shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-brand-teal">Resume parsed successfully!</p>
                <p className="text-xs text-text-muted mt-0.5">
                  {parsed.skills?.length || 0} skills · {parsed.experiences?.length || 0} experiences · {parsed.projects?.length || 0} projects
                </p>
              </div>
            </div>

            <div className="bg-surface-elevated rounded-xl p-3 border border-white/5">
              <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Detected Skills</p>
              <div className="flex flex-wrap gap-1.5">
                {parsed.skills?.slice(0, 12).map((s) => (
                  <span
                    key={s.skill}
                    className="px-2 py-0.5 bg-brand-violet/10 text-brand-violet border border-brand-violet/20 rounded-full text-xs"
                  >
                    {s.skill}
                  </span>
                ))}
              </div>
            </div>

            <button
              onClick={() => setParsed(null)}
              className="text-xs text-text-muted hover:text-text-secondary"
            >
              Upload a different file
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
