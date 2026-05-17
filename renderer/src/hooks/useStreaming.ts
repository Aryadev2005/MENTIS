import { useCallback, useRef, useState } from "react";

interface StreamingOptions {
  onToken?: (token: string) => void;
  onComplete?: (fullText: string) => void;
  onError?: (error: Error) => void;
}

export function useStreaming(options: StreamingOptions = {}) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [text, setText] = useState("");
  const [error, setError] = useState<Error | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const textRef = useRef("");

  const startStream = useCallback(
    async (url: string, body: unknown, headers: Record<string, string> = {}) => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      abortControllerRef.current = new AbortController();
      setIsStreaming(true);
      setError(null);
      setText("");
      textRef.current = "";

      try {
        const response = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...headers,
          },
          body: JSON.stringify(body),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6).trim();
              if (data === "[DONE]") break;
              if (data) {
                textRef.current += data;
                setText(textRef.current);
                options.onToken?.(data);
              }
            }
          }
        }

        options.onComplete?.(textRef.current);
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        options.onError?.(error);
      } finally {
        setIsStreaming(false);
      }
    },
    [options]
  );

  const stop = useCallback(() => {
    abortControllerRef.current?.abort();
    setIsStreaming(false);
  }, []);

  const reset = useCallback(() => {
    stop();
    setText("");
    textRef.current = "";
    setError(null);
  }, [stop]);

  return { isStreaming, text, error, startStream, stop, reset };
}
