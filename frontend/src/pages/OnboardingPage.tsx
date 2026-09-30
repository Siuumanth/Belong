import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { onboardingApi, profileApi, type ChatMessage } from "../lib/api";
import { useAuth } from "../lib/auth";

const storageKey = (userId: string) => `belong_conversation_${userId}`;

// ─── Topic list (maps to the 6 core onboarding questions) ────────────────────
const TOPICS = [
  "Relationship goal",
  "Emotional needs",
  "Core values",
  "Lifestyle",
  "Conflict style",
  "Dealbreakers",
];

// ─── Typing indicator ─────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-4 py-3.5">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="block h-2 w-2 rounded-full bg-[#4a6080]"
          style={{
            animation: "dot-bounce 1.2s infinite",
            animationDelay: `${i * 0.18}s`,
          }}
        />
      ))}
    </div>
  );
}

// ─── Chat bubble ──────────────────────────────────────────────────────────────
function Bubble({ msg, visible }: { msg: ChatMessage; visible: boolean }) {
  const isUser = msg.role === "user";
  return (
    <div
      className={`flex transition-all duration-400 ${
        visible ? "translate-y-0 opacity-100" : "translate-y-3 opacity-0"
      } ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && (
        <div className="mr-2.5 mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue/15 text-xs font-semibold text-blue">
          B
        </div>
      )}
      <div
        className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
          isUser
            ? "rounded-br-sm bg-blue/20 text-[#e8edf8]"
            : "rounded-bl-sm bg-panel border border-line text-[#c8d8f0]"
        }`}
      >
        {msg.content}
      </div>
      {isUser && (
        <div className="ml-2.5 mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#1e2d45] text-xs font-semibold text-[#8fa3bf]">
          Y
        </div>
      )}
    </div>
  );
}

// ─── Progress stepper ─────────────────────────────────────────────────────────
function ProgressStepper({ assistantCount }: { assistantCount: number }) {
  // 6 core questions + up to 2 follow-ups per = ~8 assistant messages total
  const activeIdx = Math.min(Math.floor(assistantCount) - 1, TOPICS.length - 1);

  return (
    <div className="hidden lg:flex flex-col gap-2 w-48 shrink-0">
      <p className="mb-2 text-[10px] uppercase tracking-widest text-[#4a6080]">Topics</p>
      {TOPICS.map((topic, i) => {
        const done = i < activeIdx;
        const active = i === activeIdx;
        return (
          <div key={topic} className="flex items-center gap-2.5">
            <div
              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[9px] transition-all ${
                done
                  ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-400"
                  : active
                  ? "border-blue/50 bg-blue/15 text-blue"
                  : "border-line text-[#4a6080]"
              }`}
            >
              {done ? "✓" : i + 1}
            </div>
            <span
              className={`text-xs transition-colors ${
                done
                  ? "text-[#4a6080] line-through"
                  : active
                  ? "text-[#e8edf8]"
                  : "text-[#4a6080]"
              }`}
            >
              {topic}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Thin progress bar ────────────────────────────────────────────────────────
function ProgressBar({ count }: { count: number }) {
  const pct = Math.min((count / 8) * 100, 98);
  return (
    <div className="h-0.5 w-full rounded-full bg-line">
      <div
        className="h-full rounded-full bg-blue/70 transition-all duration-700"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

// ─── Completion screen ────────────────────────────────────────────────────────
function CompletionScreen({ onContinue }: { onContinue: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-20 text-center animate-float-up">
      <div className="relative flex h-20 w-20 items-center justify-center">
        <div className="absolute inset-0 rounded-full bg-emerald-400/10 animate-pulse-ring" />
        <div className="relative flex h-14 w-14 items-center justify-center rounded-full bg-emerald-400/15 text-3xl text-emerald-400">
          ✓
        </div>
      </div>
      <div>
        <h2 className="font-display text-3xl font-light text-[#e8edf8]">You're all set</h2>
        <p className="mt-3 max-w-sm text-sm leading-relaxed text-[#8fa3bf]">
          Your signals have been captured. We're building your compatibility
          profile — this usually takes under a minute.
        </p>
      </div>
      <div className="flex flex-col gap-3 items-center">
        <button
          type="button"
          onClick={onContinue}
          className="rounded-xl bg-blue px-8 py-3 text-sm font-semibold text-white shadow-lg shadow-blue/20 hover:bg-blue-dim hover:shadow-blue/30 transition-all hover:-translate-y-0.5"
        >
          See my matches →
        </button>
        <p className="text-xs text-[#4a6080]">
          Embeddings generate in the background
        </p>
      </div>
    </div>
  );
}

// ─── Landing state ────────────────────────────────────────────────────────────
function LandingState({
  onStart,
  busy,
  error,
}: {
  onStart: () => void;
  busy: boolean;
  error: string | null;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-8 py-20 text-center animate-float-up">
      <div className="relative flex h-20 w-20 items-center justify-center">
        <div className="absolute inset-0 rounded-full bg-blue/10 animate-pulse" />
        <div className="relative flex h-14 w-14 items-center justify-center rounded-full bg-blue/15 font-display text-2xl text-blue">
          B
        </div>
      </div>
      <div>
        <h1 className="font-display text-4xl font-light text-[#e8edf8]">
          Let's get to know you
        </h1>
        <p className="mt-3 max-w-sm text-sm leading-relaxed text-[#8fa3bf]">
          A short conversation — six topics, no checklists. Just tell us
          what's true for you. Takes about 5 minutes.
        </p>
      </div>

      <div className="flex flex-wrap justify-center gap-3 text-xs text-[#4a6080]">
        {TOPICS.map((t) => (
          <span key={t} className="rounded-full border border-line px-3 py-1">
            {t}
          </span>
        ))}
      </div>

      {error && (
        <p className="text-sm text-rose-400">{error}</p>
      )}

      <button
        type="button"
        onClick={onStart}
        disabled={busy}
        className="rounded-xl bg-blue px-10 py-3.5 text-sm font-semibold text-white shadow-lg shadow-blue/20 hover:bg-blue-dim disabled:opacity-50 transition-all hover:-translate-y-0.5"
      >
        {busy ? "Starting…" : "Begin conversation"}
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

  // Restore existing conversation
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

  // Animate messages in one-by-one
  useEffect(() => {
    if (visibleCount >= messages.length) return;
    const t = setTimeout(() => setVisibleCount((c) => c + 1), 80);
    return () => clearTimeout(t);
  }, [visibleCount, messages.length]);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [visibleCount, typing]);

  // Re-focus input after AI replies
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

    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
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

  // ── Landing ──
  if (!conversationId && status === "idle") {
    return (
      <div className="mx-auto max-w-xl">
        <LandingState onStart={startSession} busy={busy} error={error} />
      </div>
    );
  }

  // ── Completed ──
  if (status === "completed") {
    return (
      <div className="mx-auto max-w-xl">
        <CompletionScreen onContinue={() => navigate("/matches")} />
      </div>
    );
  }

  // ── Chat ──
  return (
    <div className="mx-auto flex max-w-5xl gap-8" style={{ height: "calc(100vh - 88px)" }}>
      {/* Side stepper */}
      <ProgressStepper assistantCount={assistantCount} />

      {/* Chat panel */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Top bar */}
        <div className="flex items-center justify-between pb-3">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-blue animate-pulse" />
            <span className="text-xs uppercase tracking-widest text-[#4a6080]">
              Conversation in progress
            </span>
          </div>
          <button
            type="button"
            onClick={resetSession}
            className="text-xs text-[#4a6080] hover:text-[#8fa3bf] transition-colors"
          >
            Start over
          </button>
        </div>

        {/* Progress bar */}
        <ProgressBar count={assistantCount} />

        {/* Messages */}
        <div className="flex-1 overflow-y-auto py-6 space-y-4 pr-1">
          {messages.slice(0, visibleCount).map((msg, i) => (
            <Bubble key={`${msg.role}-${i}`} msg={msg} visible={i < visibleCount} />
          ))}
          {typing && (
            <div className="flex justify-start">
              <div className="mr-2.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue/15 text-xs font-semibold text-blue">
                B
              </div>
              <div className="rounded-2xl rounded-bl-sm bg-panel border border-line">
                <TypingIndicator />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-line pt-4 pb-2">
          {error && <p className="mb-2 text-sm text-rose-400">{error}</p>}
          <form onSubmit={send} className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              rows={2}
              className="flex-1 resize-none rounded-2xl border border-line bg-panel px-4 py-3 text-sm text-[#e8edf8] outline-none placeholder:text-[#4a6080] focus:border-blue/40 focus:ring-1 focus:ring-blue/10 transition-all"
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
              className="mb-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-blue text-white shadow-md shadow-blue/20 hover:bg-blue-dim disabled:opacity-40 transition-all"
              aria-label="Send"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M1.5 1.5l13 6.5-13 6.5V9.5l9-1.5-9-1.5V1.5z" />
              </svg>
            </button>
          </form>
          <p className="mt-2 text-center text-[10px] text-[#4a6080]">
            Enter to send · Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  );
}
