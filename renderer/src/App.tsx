import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { Dashboard } from "./pages/Dashboard";
import { Setup } from "./pages/Setup";
import { Session } from "./pages/Session";
import { Analytics } from "./pages/Analytics";
import { useUserStore } from "./store/user.store";
import { useElectronHotkeys } from "./hooks/useHotkeys";
import { useEffect } from "react";

function AppContent() {
  const { profile } = useUserStore();
  useElectronHotkeys();

  useEffect(() => {
    if (typeof window.mentis !== "undefined") {
      window.mentis.answer.onStreamToken((token) => {
        window.dispatchEvent(new CustomEvent("mentis:stream-token", { detail: token }));
      });

      window.mentis.answer.onComplete(({ answer, confidence }) => {
        window.dispatchEvent(
          new CustomEvent("mentis:answer-complete", { detail: { answer, confidence } })
        );
      });
    }
  }, []);

  if (!profile) {
    return <Navigate to="/setup" replace />;
  }

  if (!profile.onboarding_complete) {
    return <Navigate to="/setup" replace />;
  }

  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/session" element={<Session />} />
      <Route path="/analytics" element={<Analytics />} />
      <Route path="/setup" element={<Setup />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: "#1A1A26",
            color: "#F0F0FF",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: "12px",
            fontSize: "13px",
          },
          success: {
            iconTheme: { primary: "#00D4AA", secondary: "#0A0A0F" },
          },
          error: {
            iconTheme: { primary: "#EF4444", secondary: "#0A0A0F" },
          },
        }}
      />
    </BrowserRouter>
  );
}
