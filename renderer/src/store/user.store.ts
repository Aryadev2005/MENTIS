import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface Skill {
  skill: string;
  proficiency_level: "beginner" | "intermediate" | "advanced";
  years: number | null;
}

interface UserProfile {
  id: string;
  clerk_id: string;
  email: string;
  name: string;
  phone: string | null;
  college: string | null;
  graduation_year: number | null;
  cgpa: number | null;
  department: "CSE" | "ECE" | "Mechanical" | "Civil" | "Chemical" | "EEE" | "Other" | null;
  current_role: "fresher" | "1-3yrs" | "3-5yrs" | "5+yrs" | null;
  preferred_language: "Python" | "Java" | "C++" | "JavaScript" | null;
  plan: "free" | "student" | "pro" | "oa_pass";
  onboarding_complete: boolean;
  resume_parsed: boolean;
  target_companies: string[] | null;
  calibration_score: number | null;
  skills: Skill[];
  resume_summary: string | null;
  sessions_used: number;
  oa_solves_used: number;
}

interface UserState {
  profile: UserProfile | null;
  isLoading: boolean;
  error: string | null;

  setProfile: (profile: UserProfile) => void;
  updateProfile: (updates: Partial<UserProfile>) => void;
  clearProfile: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setPlan: (plan: "free" | "student" | "pro" | "oa_pass") => void;
  canStartSession: () => boolean;
  canSolveOA: () => boolean;
  canUseGroupMode: () => boolean;
}

const PLAN_LIMITS = {
  free: { sessions: 3, oa_solves: 10 },
  student: { sessions: Infinity, oa_solves: 100 },
  pro: { sessions: Infinity, oa_solves: Infinity },
  oa_pass: { sessions: 3, oa_solves: 5 },
};

export const useUserStore = create<UserState>()(
  persist(
    (set, get) => ({
      profile: null,
      isLoading: false,
      error: null,

      setProfile: (profile) => set({ profile, error: null }),

      updateProfile: (updates) =>
        set((state) => ({
          profile: state.profile ? { ...state.profile, ...updates } : null,
        })),

      clearProfile: () => set({ profile: null }),

      setLoading: (loading) => set({ isLoading: loading }),

      setError: (error) => set({ error }),

      setPlan: (plan) =>
        set((state) => ({
          profile: state.profile ? { ...state.profile, plan } : null,
        })),

      canStartSession: () => {
        const { profile } = get();
        if (!profile) return false;
        const limits = PLAN_LIMITS[profile.plan];
        return profile.sessions_used < limits.sessions;
      },

      canSolveOA: () => {
        const { profile } = get();
        if (!profile) return false;
        const limits = PLAN_LIMITS[profile.plan];
        return profile.oa_solves_used < limits.oa_solves;
      },

      canUseGroupMode: () => {
        const { profile } = get();
        return profile?.plan === "pro";
      },
    }),
    {
      name: "mentis-user",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ profile: state.profile }),
    }
  )
);
