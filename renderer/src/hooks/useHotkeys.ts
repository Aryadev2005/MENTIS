import { useEffect, useCallback } from "react";

type HotkeyHandler = () => void;

interface HotkeyMap {
  [combo: string]: HotkeyHandler;
}

export function useHotkeys(hotkeys: HotkeyMap) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      const parts: string[] = [];

      if (event.metaKey || event.ctrlKey) parts.push("mod");
      if (event.shiftKey) parts.push("shift");
      if (event.altKey) parts.push("alt");
      parts.push(event.key.toLowerCase());

      const combo = parts.join("+");

      if (hotkeys[combo]) {
        event.preventDefault();
        hotkeys[combo]();
      }
    },
    [hotkeys]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);
}

export function useElectronHotkeys() {
  useEffect(() => {
    if (typeof window.mentis === "undefined") return;

    const unsubOA = window.mentis.hotkeys.onOACapture(() => {
      window.dispatchEvent(new CustomEvent("mentis:oa-capture"));
    });

    const unsubCopy = window.mentis.hotkeys.onCopyAnswer(() => {
      window.dispatchEvent(new CustomEvent("mentis:copy-answer"));
    });

    return () => {
      unsubOA();
      unsubCopy();
    };
  }, []);
}
