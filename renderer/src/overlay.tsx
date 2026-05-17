import { StrictMode, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import "./globals.css";
import { AnswerCard } from "./components/overlay/AnswerCard";
import { useOverlayStore } from "./store/overlay.store";

function OverlayApp() {
  const { appendToken, setComplete, clear, isVisible } = useOverlayStore();
  const autoDismissRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (typeof window.mentis === "undefined") return;

    const unsubToken = window.mentis.answer.onStreamToken((token) => {
      appendToken(token);
      if (autoDismissRef.current) clearTimeout(autoDismissRef.current);
    });

    const unsubComplete = window.mentis.answer.onComplete(({ answer, confidence }) => {
      setComplete(answer, confidence);
      autoDismissRef.current = setTimeout(() => clear(), 60000);
    });

    const unsubClear = window.mentis.answer.onClear(() => {
      clear();
      if (autoDismissRef.current) clearTimeout(autoDismissRef.current);
    });

    return () => {
      unsubToken();
      unsubComplete();
      unsubClear();
    };
  }, [appendToken, setComplete, clear]);

  if (!isVisible) return null;

  return (
    <div className="p-3 w-full">
      <AnswerCard compact />
    </div>
  );
}

const container = document.getElementById("overlay-root");
if (!container) throw new Error("Overlay root not found");

createRoot(container).render(
  <StrictMode>
    <OverlayApp />
  </StrictMode>
);
