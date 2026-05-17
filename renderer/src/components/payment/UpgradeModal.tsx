import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Zap, Star, Sparkles, Check, Loader2 } from "lucide-react";
import { useUserStore } from "../../store/user.store";

interface Plan {
  id: string;
  name: string;
  price: number;
  period: string;
  features: string[];
  recommended?: boolean;
  icon: typeof Zap;
  color: string;
}

const PLANS: Plan[] = [
  {
    id: "student",
    name: "Student",
    price: 499,
    period: "month",
    icon: Zap,
    color: "brand-violet",
    features: [
      "Unlimited interview sessions",
      "100 OA solves/month",
      "Full company coverage (50+)",
      "Resume-tailored answers",
      "Session analytics",
      "JD keyword extraction",
    ],
    recommended: true,
  },
  {
    id: "pro",
    name: "Pro",
    price: 999,
    period: "month",
    icon: Star,
    color: "brand-teal",
    features: [
      "Everything in Student",
      "Unlimited OA solves",
      "Group OA mode (up to 6)",
      "Priority AI models",
      "Long-term memory (1 year)",
      "LangSmith trace export",
      "Early access to new features",
    ],
  },
  {
    id: "oa_pass",
    name: "OA Pass",
    price: 199,
    period: "one-time",
    icon: Sparkles,
    color: "state-warning",
    features: [
      "100 OA solves (never expires)",
      "All branches supported",
      "Question bank access",
      "No subscription needed",
    ],
  },
];

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  apiBase: string;
  highlightPlan?: string;
}

declare global {
  interface Window {
    Razorpay: new (options: unknown) => { open(): void };
  }
}

export function UpgradeModal({ isOpen, onClose, apiBase, highlightPlan = "student" }: UpgradeModalProps) {
  const { profile, setPlan } = useUserStore();
  const [selectedPlan, setSelectedPlan] = useState(highlightPlan);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpgrade = async () => {
    if (!selectedPlan || !profile?.id) return;
    setIsLoading(true);
    setError(null);

    try {
      const token = typeof window !== "undefined"
        ? sessionStorage.getItem("mentis_clerk_token") || ""
        : "";

      const orderRes = await fetch(`${apiBase}/payment/create-order`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ plan: selectedPlan }),
      });

      if (!orderRes.ok) {
        throw new Error("Failed to create payment order");
      }

      const { order_id, amount, currency, key_id } = await orderRes.json();

      if (!window.Razorpay) {
        const script = document.createElement("script");
        script.src = "https://checkout.razorpay.com/v1/checkout.js";
        document.head.appendChild(script);
        await new Promise((resolve) => (script.onload = resolve));
      }

      const plan = PLANS.find((p) => p.id === selectedPlan)!;

      const rzp = new window.Razorpay({
        key: key_id,
        amount,
        currency,
        name: "MENTIS",
        description: `${plan.name} Plan — Your Unfair Advantage`,
        order_id,
        prefill: {
          email: profile?.email || "",
          name: profile?.name || "",
        },
        theme: { color: "#6C3AFF" },
        handler: async (response: {
          razorpay_order_id: string;
          razorpay_payment_id: string;
          razorpay_signature: string;
        }) => {
          try {
            const verifyRes = await fetch(`${apiBase}/payment/verify`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`,
              },
              body: JSON.stringify({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
                plan: selectedPlan,
              }),
            });

            if (verifyRes.ok) {
              setPlan(selectedPlan as "free" | "student" | "pro" | "oa_pass");
              onClose();
            }
          } catch {
            setError("Payment verified but plan upgrade failed. Contact support.");
          }
        },
      });

      rzp.open();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Payment failed. Try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          onClick={(e) => e.target === e.currentTarget && onClose()}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.92, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            className="w-full max-w-2xl bg-surface-base border border-white/10 rounded-3xl overflow-hidden"
          >
            <div className="p-6 border-b border-white/5">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-bold text-text-primary">Upgrade MENTIS</h2>
                  <p className="text-sm text-text-secondary mt-0.5">
                    Unlock your full competitive advantage
                  </p>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 rounded-xl hover:bg-white/5 text-text-muted hover:text-text-primary transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="p-6 grid grid-cols-3 gap-3">
              {PLANS.map((plan) => {
                const Icon = plan.icon;
                const isSelected = selectedPlan === plan.id;
                return (
                  <motion.button
                    key={plan.id}
                    onClick={() => setSelectedPlan(plan.id)}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className={`relative text-left p-4 rounded-2xl border-2 transition-all ${
                      isSelected
                        ? "border-brand-violet bg-brand-violet/10"
                        : "border-white/10 bg-white/2 hover:border-white/20"
                    }`}
                  >
                    {plan.recommended && (
                      <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 text-[10px] font-bold px-2 py-0.5 bg-brand-violet text-white rounded-full whitespace-nowrap">
                        RECOMMENDED
                      </span>
                    )}

                    <Icon className={`w-5 h-5 mb-3 text-${plan.color}`} />
                    <p className="font-bold text-text-primary">{plan.name}</p>
                    <div className="mt-1 mb-3">
                      <span className="text-xl font-bold text-text-primary">₹{plan.price}</span>
                      <span className="text-xs text-text-muted">/{plan.period}</span>
                    </div>

                    <ul className="space-y-1.5">
                      {plan.features.map((f) => (
                        <li key={f} className="flex items-start gap-1.5 text-xs text-text-secondary">
                          <Check className="w-3 h-3 text-brand-teal shrink-0 mt-0.5" />
                          {f}
                        </li>
                      ))}
                    </ul>
                  </motion.button>
                );
              })}
            </div>

            <div className="p-6 pt-0 space-y-3">
              {error && (
                <p className="text-xs text-state-error text-center">{error}</p>
              )}

              <button
                onClick={handleUpgrade}
                disabled={isLoading}
                className="w-full py-3.5 bg-brand-violet hover:bg-brand-violet/80 text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-60"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    Upgrade to {PLANS.find((p) => p.id === selectedPlan)?.name}
                  </>
                )}
              </button>

              <p className="text-xs text-text-muted text-center">
                Secure payment via Razorpay · Cancel anytime · Indian cards & UPI accepted
              </p>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
