import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Crosshair, Square, RotateCcw, Check, X, ZoomIn } from "lucide-react";

interface Region {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface QuestionCaptureProps {
  onCapture: (imageB64: string) => void;
  onCancel: () => void;
}

type CaptureState = "idle" | "selecting" | "preview" | "confirmed";

export function QuestionCapture({ onCapture, onCancel }: QuestionCaptureProps) {
  const [state, setState] = useState<CaptureState>("idle");
  const [region, setRegion] = useState<Region | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const startPoint = useRef<{ x: number; y: number } | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const selectionRef = useRef<HTMLDivElement>(null);

  const startSelection = useCallback(() => {
    setState("selecting");
    setRegion(null);
    setPreviewUrl(null);
  }, []);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if (state !== "selecting") return;
    startPoint.current = { x: e.clientX, y: e.clientY };
    setRegion({ x: e.clientX, y: e.clientY, width: 0, height: 0 });
  }, [state]);

  const onMouseMove = useCallback((e: React.MouseEvent) => {
    if (state !== "selecting" || !startPoint.current) return;
    const start = startPoint.current;
    const x = Math.min(e.clientX, start.x);
    const y = Math.min(e.clientY, start.y);
    const width = Math.abs(e.clientX - start.x);
    const height = Math.abs(e.clientY - start.y);
    setRegion({ x, y, width, height });
  }, [state]);

  const onMouseUp = useCallback(async (e: React.MouseEvent) => {
    if (state !== "selecting" || !startPoint.current || !region) return;
    startPoint.current = null;

    if (region.width < 20 || region.height < 20) {
      setState("selecting");
      return;
    }

    setIsCapturing(true);
    try {
      if (typeof window.mentis !== "undefined") {
        const dataUrl = await window.mentis.screen.captureRegion(
          region.x,
          region.y,
          region.width,
          region.height
        );
        setPreviewUrl(dataUrl);
        setState("preview");
      } else {
        const canvas = document.createElement("canvas");
        canvas.width = region.width;
        canvas.height = region.height;
        const ctx = canvas.getContext("2d")!;
        ctx.fillStyle = "#1a1a2e";
        ctx.fillRect(0, 0, region.width, region.height);
        ctx.fillStyle = "#6C3AFF44";
        ctx.font = "14px monospace";
        ctx.fillText("Screen capture demo", 20, 40);
        setPreviewUrl(canvas.toDataURL());
        setState("preview");
      }
    } finally {
      setIsCapturing(false);
    }
  }, [state, region]);

  const confirmCapture = useCallback(() => {
    if (!previewUrl) return;
    setState("confirmed");
    const b64 = previewUrl.replace(/^data:image\/[a-z]+;base64,/, "");
    onCapture(b64);
  }, [previewUrl, onCapture]);

  const reset = useCallback(() => {
    setState("idle");
    setRegion(null);
    setPreviewUrl(null);
    startPoint.current = null;
  }, []);

  return (
    <div className="space-y-3">
      <AnimatePresence mode="wait">
        {state === "idle" && (
          <motion.div
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="space-y-2"
          >
            <button
              onClick={startSelection}
              className="w-full py-3 rounded-xl border border-dashed border-brand-teal/30 hover:border-brand-teal hover:bg-brand-teal/5 text-text-secondary hover:text-brand-teal text-sm font-medium flex items-center justify-center gap-2 transition-all"
            >
              <Crosshair className="w-4 h-4" />
              Select Question Region
            </button>
            <p className="text-xs text-text-muted text-center">
              Draw a box around the question on screen
            </p>
          </motion.div>
        )}

        {state === "selecting" && (
          <motion.div
            key="selecting"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="relative"
          >
            <div
              ref={overlayRef}
              className="fixed inset-0 z-50 cursor-crosshair"
              style={{ background: "rgba(0,0,0,0.35)" }}
              onMouseDown={onMouseDown}
              onMouseMove={onMouseMove}
              onMouseUp={onMouseUp}
            >
              {region && region.width > 0 && region.height > 0 && (
                <div
                  ref={selectionRef}
                  className="absolute border-2 border-brand-violet bg-brand-violet/10"
                  style={{
                    left: region.x,
                    top: region.y,
                    width: region.width,
                    height: region.height,
                  }}
                >
                  <div className="absolute -top-5 left-0 text-xs text-white bg-brand-violet px-1.5 py-0.5 rounded whitespace-nowrap">
                    {Math.round(region.width)} × {Math.round(region.height)}
                  </div>
                </div>
              )}

              <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-black/80 text-white text-xs px-4 py-2 rounded-full backdrop-blur-sm flex items-center gap-2">
                <Square className="w-3.5 h-3.5 text-brand-violet" />
                Click and drag to select the question area
                <button
                  onClick={(e) => { e.stopPropagation(); onCancel(); }}
                  className="ml-2 text-text-muted hover:text-white"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            </div>

            {isCapturing && (
              <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50">
                <div className="bg-surface-card rounded-xl p-4 text-sm text-text-secondary">
                  Capturing region...
                </div>
              </div>
            )}
          </motion.div>
        )}

        {state === "preview" && previewUrl && (
          <motion.div
            key="preview"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-3"
          >
            <div className="flex items-center gap-2 mb-1">
              <ZoomIn className="w-3.5 h-3.5 text-brand-teal" />
              <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
                Captured Region
              </span>
            </div>

            <div className="rounded-xl overflow-hidden border border-white/10 bg-black/30">
              <img
                src={previewUrl}
                alt="Captured region"
                className="w-full object-contain max-h-48"
              />
            </div>

            <div className="flex gap-2">
              <button
                onClick={confirmCapture}
                className="flex-1 flex items-center justify-center gap-2 py-2 bg-brand-violet hover:bg-brand-violet/80 text-white text-sm font-medium rounded-xl transition-colors"
              >
                <Check className="w-4 h-4" />
                Use This
              </button>
              <button
                onClick={reset}
                className="flex items-center justify-center gap-2 px-3 py-2 border border-white/10 hover:bg-white/5 text-text-secondary text-sm rounded-xl transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                Retake
              </button>
              <button
                onClick={onCancel}
                className="flex items-center justify-center gap-2 px-3 py-2 border border-white/10 hover:bg-white/5 text-text-muted text-sm rounded-xl transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        )}

        {state === "confirmed" && (
          <motion.div
            key="confirmed"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center justify-center gap-2 py-3 text-brand-teal text-sm"
          >
            <Check className="w-4 h-4" />
            Sent to AI solver...
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
