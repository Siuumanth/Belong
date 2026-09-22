import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ErrorText } from "../components/ui";
import { onboardingApi, profileApi, type ChatMessage } from "../lib/api";
import { useAuth } from "../lib/auth";

const storageKey = (userId: string) => `belong_conversation_${userId}`;

// ─── Typing indicator (three bouncing dots) ──────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex items-end gap-1 px-4 py-3">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="block h-2 w-2 rounded-full bg-zinc-500"
          style={{
            animation: "bounce 1.2s infinite",
            animationDelay: `${i * 0.2}s`,
          }}
        />
      ))}
    </div>
  );
}

// ─── Single chat bubble ───────────────────────────────────────────────────────
function Bubble({ msg, visible }: { msg: ChatMessage; visible: boolean }) {
  const isUser = msg.role === "user";
  return (
    <div
      className={`flex transition-all duration-500 ${
        visible ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0"
      } ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && (
        <div className="mr-2 mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gold/20 text-xs text-gold">
          B
        </div>
      )}
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "rounded-br-sm bg-gold/20 text-zinc-100"
            : "rounded-bl-sm bg-[#1e1b18] text-zinc-200"
        }`}
      >
        {msg.content}
      </div>
    </div>
  );
}

// ─── Subtle progress bar at the top ──────────────────────────────────────────
// The onboarding has ~6 core topics; each assistant message advances it
function ProgressBar({ count }: { count: number }) {
  // assistantCount / 8 approximates progress (6 questions + up to 2 follow-ups max)
  const pct = Math.min((count / 8) * 100, 95);
  return (
    <div className="h-0.5 w-full bg-line">
      <div
        className="h-full bg-gold/60 transition-all duration-700"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

// ─── Completion screen ────────────────────────────────────────────────────────
function CompletionScreen({ onContinue }: { onContinue: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-16 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gold/15 text-3xl">
        ✦
      </div>
      <div>
        <h2 className="font-display text-2xl text-gold">You're all set</h2>
        <p className="mt-2 max-w-xs text-sm text-zinc-400">
          Your signals have been captured. We're building your compatibility
          profile now.
        </p>
      </div>
      <button
        type="button"
        onClick={onContinue}
        className="rounded-full bg-gold px-6 py-2.5 text-sm font-medium text-ink hover:bg-[#e0b88a]"
      >
        See my matches →
      </button>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export function OnboardingPage() {
  const { session } = useAuth();
  const userId = session!.userId;
  const navigate = useNavigate();

  const [conversationId, setConversationId] = useState<string | null>(
    () => localStorage.getItem(storageKey(userId)),
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [visibleCount, setVisibleCount] = useState(0);
  const [status, setStatus] = useState<"idle" | "in_progress" | "completed">("idle");
  const [typing, setTyping] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Restore existing conversation on mount
  useEffect(() => {
    if (!conversationId) return;
    let cancelled = false;
    onboardingApi
      .state(conversationId)
      .then((state) => {
        if (cancelled) return;
        const msgs = state.messages ?? [];
        setMessages(msgs);
        setVisibleCount(msgs.length);
        setStatus(state.status as "idle" | "in_progress" | "completed");
      })
      .catch(() => {
        if (cancelled) return;
        localStorage.removeItem(storageKey(userId));
        setConversationId(null);
      });
    return () => { cancelled = true; };
  }, [conversationId, userId]);

  // Animate new messages in one-by-one
  useEffect(() => {
    if (visibleCount >= messages.length) return;
    const t = setTimeout(() => setVisibleCount((c) => c + 1), 80);
    return () => clearTimeout(t);
  }, [visibleCount, messages.length]);

  // Auto-scroll to bottom when messages or typing indicator changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [visibleCount, typing]);

  useEffect(() => {
    if (!typing && status === "in_progress") {
      inputRef.current?.focus();
    }
  }, [typing, status]);

  async function startSession() {
    setBusy(true);
    setError(null);
    try {
      const res = await onboardingApi.start(userId);
      localStorage.setItem(storageKey(userId), res.conversation_id);
      setConversationId(res.conversation_id);
      setStatus("in_progress");
      const firstMsg: ChatMessage = {
        role: "assistant",
        content: res.message,
        question_id: res.question_id,
      };
      setMessages([firstMsg]);
      setVisibleCount(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start onboarding");
    } finally {
      setBusy(false);
    }
  }

  async function send(e: FormEvent) {
    e.preventDefault();
    if (!conversationId || !draft.trim() || busy) return;
    const text = draft.trim();
    setDraft("");
    setBusy(true);
    setError(null);

    // Optimistically add user message
    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);

    // Show typing indicator while waiting for reply
    setTyping(true);
    try {
      const reply = await onboardingApi.send(conversationId, text);
      setTyping(false);
      setStatus(reply.status);
      if (reply.message) {
        const assistantMsg: ChatMessage = {
          role: "assistant",
          content: reply.message,
          question_id: reply.question_id,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      }
      // On completion: trigger embedding job in background
      if (reply.status === "completed") {
        profileApi.triggerEmbedding(userId).catch(() => {/* best-effort */});
      }
    } catch (err) {
      setTyping(false);
      setError(err instanceof Error ? err.message : "Message failed");
    } finally {
      setBusy(false);
    }
  }

  function resetSession() {
    localStorage.removeItem(storageKey(userId));
    setConversationId(null);
    setMessages([]);
    setVisibleCount(0);
    setStatus("idle");
    setTyping(false);
    setDraft("");
    setError(null);
  }

  const assistantCount = messages.filter((m) => m.role === "assistant").length;

  // ── Landing state (no session yet) ──────────────────────────────────────────
  if (!conversationId && status === "idle") {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center gap-8 text-center">
        <div>
          <p className="font-display text-4xl text-gold">Let's get to know you</p>
          <p className="mt-3 max-w-sm text-sm text-zinc-400">
            A short conversation — six topics, no checklists. Just tell us
            what's true for you.
          </p>
        </div>
        <ErrorText message={error} />
        <button
          type="button"
          onClick={startSession}
          disabled={busy}
          className="rounded-full bg-gold px-8 py-3 text-sm font-medium text-ink hover:bg-[#e0b88a] disabled:opacity-50"
        >
          {busy ? "Starting…" : "Begin conversation"}
        </button>
      </div>
    );
  }

  // ── Completed state ──────────────────────────────────────────────────────────
  if (status === "completed") {
    return (
      <div className="mx-auto max-w-xl">
        <CompletionScreen onContinue={() => navigate("/matches")} />
      </div>
    );
  }

  // ── Chat state ────────────────────────────────────────────────────────────────
  return (
    <div className="mx-auto flex max-w-xl flex-col" style={{ height: "calc(100vh - 80px)" }}>
      {/* Top bar */}
      <div className="flex items-center justify-between px-1 pb-3">
        <p className="text-xs uppercase tracking-widest text-zinc-500">
          Getting to know you
        </p>
        <button
          type="button"
          onClick={resetSession}
          className="text-xs text-zinc-600 hover:text-zinc-400"
        >
          Start over
        </button>
      </div>

      {/* Progress bar */}
      <ProgressBar count={assistantCount} />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-6 pr-1 space-y-4">
        {messages.slice(0, visibleCount).map((msg, i) => (
          <Bubble key={`${msg.role}-${i}`} msg={msg} visible={i < visibleCount} />
        ))}
        {typing && (
          <div className="flex justify-start">
            <div className="mr-2 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gold/20 text-xs text-gold">
              B
            </div>
            <div className="rounded-2xl rounded-bl-sm bg-[#1e1b18]">
              <TypingIndicator />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-line pt-4 pb-2">
        <ErrorText message={error} />
        <form onSubmit={send} className="mt-2 flex items-end gap-2">
          <textarea
            ref={inputRef}
            rows={2}
            className="flex-1 resize-none rounded-2xl border border-line bg-[#1a1714] px-4 py-3 text-sm text-zinc-100 outline-none placeholder:text-zinc-600 focus:border-gold/40"
            placeholder="Answer in your own words…"
            value={draft}
            disabled={busy}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send(e as unknown as FormEvent);
              }
            }}
          />
          <button
            type="submit"
            disabled={busy || !draft.trim()}
            className="mb-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gold text-ink hover:bg-[#e0b88a] disabled:opacity-40"
            aria-label="Send"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M1.5 1.5l13 6.5-13 6.5V9.5l9-1.5-9-1.5V1.5z" />
            </svg>
          </button>
        </form>
        <p className="mt-2 text-center text-xs text-zinc-600">
          Enter to send · Shift+Enter for new line
        </p>
      </div>

      {/* Bounce keyframe */}
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40% { transform: translateY(-5px); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
