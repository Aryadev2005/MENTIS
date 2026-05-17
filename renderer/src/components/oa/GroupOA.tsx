import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Users, Wifi, WifiOff, Copy, Hash, X, Shield } from "lucide-react";
import { useUserStore } from "../../store/user.store";

interface GroupMember {
  user_id: string;
  joined_at: number;
}

interface GroupOAProps {
  apiBase: string;
  onSolutionReceived?: (solution: unknown) => void;
}

type ConnectionState = "disconnected" | "connecting" | "connected" | "error";

export function GroupOA({ apiBase, onSolutionReceived }: GroupOAProps) {
  const { profile } = useUserStore();
  const [groupCode, setGroupCode] = useState("");
  const [inputCode, setInputCode] = useState("");
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [memberCount, setMemberCount] = useState(0);
  const [isEncrypted, setIsEncrypted] = useState(false);
  const [solutionCount, setSolutionCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const wsUrl = apiBase.replace(/^http/, "ws");

  const generateCode = () => {
    const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    return Array.from({ length: 6 }, () => chars[Math.floor(Math.random() * chars.length)]).join("");
  };

  const connect = useCallback((code: string) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    setConnectionState("connecting");
    setError(null);

    const userId = profile?.id || `anon-${Date.now()}`;
    const ws = new WebSocket(`${wsUrl}/oa/group/${code}`);
    ws.onopen = () => {};

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case "joined":
            setConnectionState("connected");
            setGroupCode(code);
            setMemberCount(data.member_count);
            setIsEncrypted(data.encryption ?? false);
            break;

          case "member_joined":
          case "member_left":
            setMemberCount(data.member_count);
            break;

          case "solution":
          case "answer_broadcast":
            setSolutionCount((n) => n + 1);
            onSolutionReceived?.(data.solution);
            break;

          case "encrypted_solution":
            setSolutionCount((n) => n + 1);
            onSolutionReceived?.({ encrypted: true, token: data.token });
            break;

          case "error":
            setError(data.message);
            setConnectionState("error");
            break;
        }
      } catch {
        // non-JSON frame
      }
    };

    ws.onerror = () => {
      setConnectionState("error");
      setError("Connection failed. Check your network.");
    };

    ws.onclose = (e) => {
      if (connectionState === "connected") {
        setConnectionState("disconnected");
        setGroupCode("");
        setMemberCount(0);
      }
    };

    wsRef.current = ws;

    const ping = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 25000);

    ws.addEventListener("close", () => clearInterval(ping));
  }, [wsUrl, profile?.id, onSolutionReceived]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setConnectionState("disconnected");
    setGroupCode("");
    setMemberCount(0);
    setSolutionCount(0);
    setIsEncrypted(false);
  }, []);

  const createAndJoin = () => {
    const code = generateCode();
    setInputCode(code);
    connect(code);
  };

  const joinExisting = () => {
    if (inputCode.trim().length < 4) return;
    connect(inputCode.trim().toUpperCase());
  };

  const copyCode = () => {
    navigator.clipboard.writeText(groupCode);
  };

  useEffect(() => () => wsRef.current?.close(), []);

  if (connectionState === "connected") {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border border-brand-teal/20 bg-brand-teal/5 p-4 space-y-3"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wifi className="w-4 h-4 text-brand-teal" />
            <span className="text-sm font-semibold text-brand-teal">Group OA Active</span>
            {isEncrypted && (
              <span className="flex items-center gap-1 text-xs px-1.5 py-0.5 bg-brand-teal/10 border border-brand-teal/20 rounded-full text-brand-teal">
                <Shield className="w-3 h-3" /> E2E Encrypted
              </span>
            )}
          </div>
          <button
            onClick={disconnect}
            className="p-1.5 rounded-lg hover:bg-white/10 text-text-muted hover:text-text-primary transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex-1 flex items-center gap-2 bg-black/20 rounded-xl px-3 py-2">
            <Hash className="w-3.5 h-3.5 text-text-muted" />
            <span className="text-sm font-mono text-text-primary tracking-widest">{groupCode}</span>
          </div>
          <button
            onClick={copyCode}
            className="p-2 rounded-xl hover:bg-white/10 text-text-muted hover:text-brand-teal transition-colors"
          >
            <Copy className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center justify-between text-xs text-text-muted">
          <div className="flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5" />
            <span>{memberCount}/6 members connected</span>
          </div>
          <span>{solutionCount} solutions shared</span>
        </div>

        <div className="flex gap-1">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className={`h-1.5 flex-1 rounded-full transition-colors ${
                i < memberCount ? "bg-brand-teal" : "bg-white/10"
              }`}
            />
          ))}
        </div>
      </motion.div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-1">
        <Users className="w-4 h-4 text-text-muted" />
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
          Group OA Mode
        </span>
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={inputCode}
          onChange={(e) => setInputCode(e.target.value.toUpperCase())}
          placeholder="Enter group code"
          maxLength={8}
          className="flex-1 px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-text-primary text-sm font-mono tracking-wider focus:outline-none focus:border-brand-violet/50 placeholder:text-text-muted"
        />
        <button
          onClick={joinExisting}
          disabled={inputCode.trim().length < 4 || connectionState === "connecting"}
          className="px-3 py-2 bg-brand-violet/10 border border-brand-violet/20 hover:bg-brand-violet/20 text-brand-violet text-sm font-medium rounded-xl transition-colors disabled:opacity-40"
        >
          Join
        </button>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex-1 h-px bg-white/5" />
        <span className="text-xs text-text-muted">or</span>
        <div className="flex-1 h-px bg-white/5" />
      </div>

      <button
        onClick={createAndJoin}
        disabled={connectionState === "connecting"}
        className="w-full py-2.5 border border-dashed border-brand-teal/30 hover:border-brand-teal hover:bg-brand-teal/5 text-text-secondary hover:text-brand-teal text-sm font-medium rounded-xl transition-all flex items-center justify-center gap-2"
      >
        <Users className="w-4 h-4" />
        Create New Group
      </button>

      {connectionState === "connecting" && (
        <p className="text-xs text-text-muted text-center animate-pulse">Connecting...</p>
      )}

      {error && (
        <p className="text-xs text-state-error flex items-center gap-1.5">
          <WifiOff className="w-3.5 h-3.5" /> {error}
        </p>
      )}

      <p className="text-xs text-text-muted leading-relaxed">
        Share your screen solutions with up to 6 study group members instantly.
        {isEncrypted && " End-to-end encrypted."}
      </p>
    </div>
  );
}
