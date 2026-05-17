import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronRight, Upload, CheckCircle, Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useUserStore } from "../store/user.store";
import toast from "react-hot-toast";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const DEPARTMENTS = ["CSE", "ECE", "Mechanical", "Civil", "Chemical", "EEE", "Other"] as const;
const COMPANIES = [
  "Amazon", "Google", "Microsoft", "TCS", "Infosys", "Wipro", "Accenture",
  "Flipkart", "Swiggy", "Razorpay", "CRED", "Zepto", "Meesho", "PhonePe",
  "L&T", "Tata Motors", "Bosch India", "DRDO", "ISRO",
];
const ROLES = ["fresher", "1-3yrs", "3-5yrs", "5+yrs"] as const;
const LANGUAGES = ["Python", "Java", "C++", "JavaScript"] as const;

interface StepData {
  name: string;
  email: string;
  phone: string;
  college: string;
  graduation_year: string;
  cgpa: string;
  department: string;
  target_companies: string[];
  current_role: string;
  preferred_language: string;
}

export function Setup() {
  const { profile } = useUserStore();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [parsedResume, setParsedResume] = useState<Record<string, unknown> | null>(null);
  const [data, setData] = useState<StepData>({
    name: profile?.name || "",
    email: profile?.email || "",
    phone: "",
    college: "",
    graduation_year: "",
    cgpa: "",
    department: "CSE",
    target_companies: [],
    current_role: "fresher",
    preferred_language: "Python",
  });

  const headers = {
    "X-User-Id": profile?.id || "",
    "Content-Type": "application/json",
  };

  const update = (key: keyof StepData, value: unknown) =>
    setData((d) => ({ ...d, [key]: value }));

  const next = () => setStep((s) => Math.min(s + 1, 9));
  const back = () => setStep((s) => Math.max(s - 1, 1));

  const submitStep = async (stepNum: number, body: unknown) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/user/onboarding/step/${stepNum}`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("Failed");
      next();
    } catch {
      toast.error("Something went wrong. Try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const uploadResume = async () => {
    if (!resumeFile) return;
    setIsLoading(true);
    try {
      const form = new FormData();
      form.append("file", resumeFile);
      const res = await fetch(`${API_BASE}/user/onboarding/step/4/resume`, {
        method: "POST",
        headers: { "X-User-Id": profile?.id || "" },
        body: form,
      });
      const data = await res.json();
      setParsedResume(data.parsed);
      next();
    } catch {
      toast.error("Resume upload failed. Check file format.");
    } finally {
      setIsLoading(false);
    }
  };

  const complete = async () => {
    setIsLoading(true);
    try {
      await fetch(`${API_BASE}/user/onboarding/complete`, {
        method: "POST",
        headers,
      });
      toast.success("Setup complete! Your unfair advantage is ready.");
      navigate("/");
    } catch {
      toast.error("Failed to complete setup");
    } finally {
      setIsLoading(false);
    }
  };

  const STEPS = [
    {
      title: "Your Details",
      subtitle: "Let's get to know you",
      content: (
        <div className="space-y-4">
          <Input label="Full Name" value={data.name} onChange={(v) => update("name", v)} placeholder="Arya Dev Chatterjee" />
          <Input label="Email" value={data.email} onChange={(v) => update("email", v)} placeholder="you@example.com" type="email" />
          <Input label="Phone (optional)" value={data.phone} onChange={(v) => update("phone", v)} placeholder="+91 9876543210" />
          <StepButton onClick={() => submitStep(1, { name: data.name, email: data.email, phone: data.phone || undefined })} loading={isLoading} />
        </div>
      ),
    },
    {
      title: "Academic Background",
      subtitle: "Tell us about your education",
      content: (
        <div className="space-y-4">
          <Input label="College" value={data.college} onChange={(v) => update("college", v)} placeholder="IIT Bombay" />
          <Input label="Graduation Year" value={data.graduation_year} onChange={(v) => update("graduation_year", v)} placeholder="2025" type="number" />
          <Input label="CGPA" value={data.cgpa} onChange={(v) => update("cgpa", v)} placeholder="8.5" type="number" />
          <StepButton onClick={() => submitStep(2, { college: data.college, graduation_year: parseInt(data.graduation_year), cgpa: parseFloat(data.cgpa) })} loading={isLoading} />
        </div>
      ),
    },
    {
      title: "Your Department",
      subtitle: "We'll tailor questions for your branch",
      content: (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            {DEPARTMENTS.map((d) => (
              <button
                key={d}
                onClick={() => update("department", d)}
                className={`px-4 py-3 rounded-xl border text-sm font-medium transition-all ${
                  data.department === d
                    ? "border-brand-violet bg-brand-violet/15 text-brand-violet"
                    : "border-white/10 bg-white/2 text-text-secondary hover:border-brand-violet/30"
                }`}
              >
                {d}
              </button>
            ))}
          </div>
          <StepButton onClick={() => submitStep(3, { department: data.department })} loading={isLoading} />
        </div>
      ),
    },
    {
      title: "Upload Resume",
      subtitle: "AI will extract your skills and experience",
      content: (
        <div className="space-y-4">
          <label className="block w-full cursor-pointer">
            <input
              type="file"
              accept=".pdf,.docx,.doc"
              className="hidden"
              onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
            />
            <div className={`p-8 rounded-xl border-2 border-dashed text-center transition-all ${resumeFile ? "border-brand-teal/50 bg-brand-teal/5" : "border-white/10 hover:border-brand-violet/30"}`}>
              {resumeFile ? (
                <div className="flex items-center justify-center gap-2 text-brand-teal">
                  <CheckCircle className="w-5 h-5" />
                  <span className="text-sm font-medium">{resumeFile.name}</span>
                </div>
              ) : (
                <>
                  <Upload className="w-8 h-8 text-text-muted mx-auto mb-2" />
                  <p className="text-sm text-text-secondary">Drop your resume here</p>
                  <p className="text-xs text-text-muted mt-1">PDF or DOCX · Max 5MB</p>
                </>
              )}
            </div>
          </label>

          {parsedResume && (
            <div className="p-3 bg-brand-teal/5 border border-brand-teal/20 rounded-xl text-xs text-brand-teal">
              ✓ Parsed: {Array.isArray((parsedResume as any).skills) ? `${(parsedResume as any).skills.length} skills detected` : "Resume extracted successfully"}
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={() => next()}
              className="flex-1 py-2.5 rounded-xl border border-white/10 text-text-muted text-sm hover:bg-white/3 transition-colors"
            >
              Skip for now
            </button>
            <StepButton onClick={uploadResume} loading={isLoading} label="Upload & Continue" className="flex-1" />
          </div>
        </div>
      ),
    },
    {
      title: "Target Companies",
      subtitle: "We'll optimize your prep accordingly",
      content: (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto">
            {COMPANIES.map((c) => (
              <button
                key={c}
                onClick={() => {
                  const selected = data.target_companies;
                  update("target_companies", selected.includes(c) ? selected.filter((x) => x !== c) : [...selected, c]);
                }}
                className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
                  data.target_companies.includes(c)
                    ? "border-brand-violet bg-brand-violet/15 text-brand-violet"
                    : "border-white/10 bg-white/2 text-text-secondary hover:border-brand-violet/30"
                }`}
              >
                {c}
              </button>
            ))}
          </div>
          <StepButton onClick={() => submitStep(5, { target_companies: data.target_companies })} loading={isLoading} />
        </div>
      ),
    },
    {
      title: "Experience Level",
      subtitle: "So we calibrate the right difficulty",
      content: (
        <div className="space-y-3">
          {ROLES.map((r) => (
            <button
              key={r}
              onClick={() => update("current_role", r)}
              className={`w-full px-4 py-3 rounded-xl border text-sm font-medium transition-all text-left ${
                data.current_role === r
                  ? "border-brand-violet bg-brand-violet/15 text-brand-violet"
                  : "border-white/10 bg-white/2 text-text-secondary hover:border-brand-violet/30"
              }`}
            >
              {r === "fresher" ? "Fresher (0 years)" : `${r} experience`}
            </button>
          ))}
          <StepButton onClick={() => submitStep(6, { current_role: data.current_role })} loading={isLoading} />
        </div>
      ),
    },
    {
      title: "Preferred Language",
      subtitle: "For coding questions",
      content: (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            {LANGUAGES.map((l) => (
              <button
                key={l}
                onClick={() => update("preferred_language", l)}
                className={`px-4 py-3 rounded-xl border text-sm font-medium transition-all ${
                  data.preferred_language === l
                    ? "border-brand-violet bg-brand-violet/15 text-brand-violet"
                    : "border-white/10 bg-white/2 text-text-secondary hover:border-brand-violet/30"
                }`}
              >
                {l}
              </button>
            ))}
          </div>
          <StepButton onClick={() => submitStep(7, { preferred_language: data.preferred_language })} loading={isLoading} />
        </div>
      ),
    },
    { title: "Calibration Test", subtitle: "3 quick questions to assess your level", content: <CalibrationStep headers={headers} department={data.department} onComplete={next} /> },
    {
      title: "You're All Set! 🚀",
      subtitle: "MENTIS is ready to give you your unfair advantage",
      content: (
        <div className="space-y-4 text-center">
          <div className="w-16 h-16 rounded-2xl bg-gradient-brand flex items-center justify-center mx-auto">
            <CheckCircle className="w-8 h-8 text-white" />
          </div>
          <p className="text-sm text-text-secondary">Your profile is configured. The AI copilot is ready for your next interview or OA.</p>
          <StepButton onClick={complete} loading={isLoading} label="Launch MENTIS →" />
        </div>
      ),
    },
  ];

  const currentStep = STEPS[step - 1];

  return (
    <div className="min-h-screen bg-surface-base flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-1 mb-8">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className="flex-1 h-1 rounded-full transition-all duration-300"
              style={{ backgroundColor: i < step ? "#6C3AFF" : "rgba(255,255,255,0.08)" }}
            />
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
            className="bg-surface-card rounded-2xl p-6 border border-white/5"
          >
            <p className="text-xs text-brand-violet font-semibold uppercase tracking-widest mb-1">
              Step {step} of {STEPS.length}
            </p>
            <h2 className="text-xl font-bold text-text-primary mb-1">{currentStep.title}</h2>
            <p className="text-sm text-text-muted mb-6">{currentStep.subtitle}</p>
            {currentStep.content}
          </motion.div>
        </AnimatePresence>

        {step > 1 && step < 9 && (
          <button onClick={back} className="mt-3 text-xs text-text-muted hover:text-text-secondary transition-colors">
            ← Back
          </button>
        )}
      </div>
    </div>
  );
}

function Input({ label, value, onChange, placeholder, type = "text" }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; type?: string }) {
  return (
    <div>
      <label className="text-xs text-text-muted mb-1.5 block">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-xl text-text-primary text-sm focus:outline-none focus:border-brand-violet/50 placeholder:text-text-muted transition-colors"
      />
    </div>
  );
}

function StepButton({ onClick, loading, label = "Continue", className = "" }: { onClick: () => void; loading?: boolean; label?: string; className?: string }) {
  return (
    <motion.button
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
      onClick={onClick}
      disabled={loading}
      className={`w-full py-3 rounded-xl bg-gradient-brand text-white font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-60 ${className}`}
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <>{label} <ChevronRight className="w-4 h-4" /></>}
    </motion.button>
  );
}

function CalibrationStep({ headers, department, onComplete }: { headers: Record<string, string>; department: string; onComplete: () => void }) {
  const [questions, setQuestions] = useState<any[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/user/onboarding/calibration/${department}`, { headers })
      .then((r) => r.json())
      .then((d) => { setQuestions(d.questions || []); setLoading(false); });
  }, [department]);

  const submit = async () => {
    setSubmitting(true);
    const answerList = Object.entries(answers).map(([question_id, answer]) => ({
      question_id,
      answer,
      time_taken_seconds: 30,
    }));

    await fetch(`${API_BASE}/user/onboarding/step/8/calibration`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ answers: answerList }),
    });

    setSubmitting(false);
    onComplete();
  };

  if (loading) return <div className="text-center text-text-muted text-sm py-8">Loading questions...</div>;

  return (
    <div className="space-y-4">
      {questions.map((q: any, i: number) => (
        <div key={q.id} className="space-y-2">
          <p className="text-sm text-text-primary font-medium">{i + 1}. {q.question}</p>
          <div className="grid grid-cols-2 gap-2">
            {q.options?.map((opt: string) => (
              <button
                key={opt}
                onClick={() => setAnswers((a) => ({ ...a, [q.id]: opt }))}
                className={`px-3 py-2 rounded-lg border text-xs text-left transition-all ${
                  answers[q.id] === opt
                    ? "border-brand-violet bg-brand-violet/15 text-brand-violet"
                    : "border-white/10 bg-white/2 text-text-secondary hover:border-brand-violet/20"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      ))}
      <StepButton onClick={submit} loading={submitting} label="Submit Answers" />
    </div>
  );
}
