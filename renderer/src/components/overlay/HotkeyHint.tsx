const isMac = navigator.platform.toUpperCase().includes("MAC");
const Mod = isMac ? "⌘" : "Ctrl";

const HOTKEYS = [
  { combo: `${Mod}⇧H`, label: "Toggle overlay" },
  { combo: `${Mod}⇧S`, label: "OA capture" },
  { combo: `${Mod}⇧C`, label: "Copy answer" },
];

export function HotkeyHint() {
  return (
    <div className="flex items-center gap-3 flex-wrap">
      {HOTKEYS.map((hk) => (
        <div key={hk.combo} className="flex items-center gap-1.5 text-xs text-text-muted">
          <kbd className="px-1.5 py-0.5 bg-white/5 border border-white/10 rounded text-text-secondary font-mono text-xs">
            {hk.combo}
          </kbd>
          <span>{hk.label}</span>
        </div>
      ))}
    </div>
  );
}
