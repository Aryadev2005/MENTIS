import { useCallback, useEffect, useRef, useState } from "react";

interface AudioCaptureState {
  isCapturing: boolean;
  error: string | null;
  partialTranscript: string;
  finalTranscripts: string[];
}

const SAMPLE_RATE = 16000;
const CHANNELS = 1;

export function useAudio() {
  const [state, setState] = useState<AudioCaptureState>({
    isCapturing: false,
    error: null,
    partialTranscript: "",
    finalTranscripts: [],
  });

  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);

  const onTranscriptPartial = useCallback((text: string) => {
    setState((s) => ({ ...s, partialTranscript: text }));
  }, []);

  const onTranscriptFinal = useCallback((text: string) => {
    setState((s) => ({
      ...s,
      partialTranscript: "",
      finalTranscripts: [...s.finalTranscripts, text],
    }));

    window.dispatchEvent(new CustomEvent("mentis:final-transcript", { detail: text }));
  }, []);

  useEffect(() => {
    if (typeof window.mentis === "undefined") return;

    const unsubPartial = window.mentis.audio.onTranscriptPartial(onTranscriptPartial);
    const unsubFinal = window.mentis.audio.onTranscriptFinal(onTranscriptFinal);

    return () => {
      unsubPartial();
      unsubFinal();
    };
  }, [onTranscriptPartial, onTranscriptFinal]);

  const startCapture = useCallback(async (sourceId?: string) => {
    try {
      if (typeof window.mentis !== "undefined") {
        await window.mentis.audio.startCapture({
          sourceId,
          sampleRate: SAMPLE_RATE,
          channels: CHANNELS,
        });
      } else {
        const constraints: MediaStreamConstraints = {
          audio: {
            sampleRate: SAMPLE_RATE,
            channelCount: CHANNELS,
            echoCancellation: false,
            noiseSuppression: false,
          },
        };

        mediaStreamRef.current = await navigator.mediaDevices.getUserMedia(constraints);
        audioContextRef.current = new AudioContext({ sampleRate: SAMPLE_RATE });
        const source = audioContextRef.current.createMediaStreamSource(mediaStreamRef.current);

        processorRef.current = audioContextRef.current.createScriptProcessor(4096, 1, 1);
        processorRef.current.onaudioprocess = (e) => {
          const float32Data = e.inputBuffer.getChannelData(0);
          const int16Data = new Int16Array(float32Data.length);
          for (let i = 0; i < float32Data.length; i++) {
            int16Data[i] = Math.max(-32768, Math.min(32767, float32Data[i] * 32768));
          }
          window.mentis?.audio && void window.mentis.audio;
        };

        source.connect(processorRef.current);
        processorRef.current.connect(audioContextRef.current.destination);
      }

      setState((s) => ({ ...s, isCapturing: true, error: null }));
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to start audio capture";
      setState((s) => ({ ...s, error: msg }));
    }
  }, []);

  const stopCapture = useCallback(async () => {
    try {
      if (typeof window.mentis !== "undefined") {
        await window.mentis.audio.stopCapture();
      }

      processorRef.current?.disconnect();
      audioContextRef.current?.close();
      mediaStreamRef.current?.getTracks().forEach((t) => t.stop());

      mediaStreamRef.current = null;
      audioContextRef.current = null;
      processorRef.current = null;
    } finally {
      setState((s) => ({ ...s, isCapturing: false }));
    }
  }, []);

  const clearTranscripts = useCallback(() => {
    setState((s) => ({ ...s, finalTranscripts: [], partialTranscript: "" }));
  }, []);

  return {
    ...state,
    startCapture,
    stopCapture,
    clearTranscripts,
  };
}
