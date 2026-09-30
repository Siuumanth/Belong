import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { onboardingApi, profileApi, type ChatMessage } from "../lib/api";
import { useAuth } from "../lib/auth";

const storageKey = (userId: string) => `belong_conversation_${userId}`;

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
  const activeIdx = Math.min(assistantCount - 1, TOPICS.length - 1);
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
                  ? "border-[#d4a843]/40 bg-[#d4a843]/10 text-[#d4a843]"
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
                  ? "text-[#eaedfa]"
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

// ─── Progress bar ─────────────────────────────────────────────────────────────
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

// ─── Completion banner (shown above chat when onboarding is done) ─────────────
function CompletionBanner({ onRedo, onMatches }: { onRedo: () => void; onMatches: () => void }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-[#d4a843]/25 bg-[#d4a843]/8 px-5 py-3.5">
      <div className="flex items-center gap-3">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#d4a843]/15 text-sm text-[#d4a843]">✓</span>
        <div>
          <p className="text-sm font-medium text-[#d4a843]">Onboarding complete</p>
          <p className="text-xs text-[#8fa3bf]">Your compatibility signals have been captured.</p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <button
          type="button"
          onClick={onMatches}
          className="rounded-xl bg-blue px-4 py-1.5 text-xs font-semibold text-white hover:bg-blue-dim transition-colors"
        >
          See matches →
        </button>
        <button
          type="button"
          onClick={onRedo}
          className="rounded-xl border border-line px-3 py-1.5 text-xs text-[#4a6080] hover:text-[#8fa3bf] transition-colors"
        >
          Redo
        </button>
      </div>
    </div>
  );
}

// ─── Completion screen (no chat history available) ────────────────────────────
function CompletionScreen({ onContinue, onRedo }: { onContinue: () => void; onRedo: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-20 text-center animate-float-up">
      <div className="relative flex h-20 w-20 items-center justify-center">
        <div className="absolute inset-0 rounded-full bg-[#d4a843]/10 animate-pulse-ring" />
        <div className="relative flex h-14 w-14 items-center justify-center rounded-full bg-[#d4a843]/15 text-3xl text-[#d4a843]">
          ✓
        </div>
      </div>
      <div>
        <h2 className="font-display text-3xl font-light text-[#e8edf8]">Onboarding complete</h2>
        <p className="mt-3 max-w-sm text-sm leading-relaxed text-[#8fa3bf]">
          Your signals have been captured and your compatibility profile is ready.
        </p>
      </div>
      <div className="flex flex-col gap-3 items-center">
        <button
          type="button"
          onClick={onContinue}
          className="rounded-xl bg-blue px-8 py-3 text-sm font-semibold text-white shadow-lg shadow-blue/20 hover:bg-blue-dim transition-all hover:-translate-y-0.5"
        >
          See my matches →
        </button>
        <button
          type="button"
          onClick={onRedo}
          className="text-xs text-[#4a6080] hover:text-[#8fa3bf] transition-colors"
        >
          Redo onboarding
        </button>
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
        <h1 className="font-display text-4xl font-light text-[#e8edf8]">Let's get to know you</h1>
        <p className="mt-3 max-w-sm text-sm leading-relaxed text-[#8fa3bf]">
          A short conversation — six topics, no checklists. Just tell us what's true for you.
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-3 text-xs text-[#4a6080]">
        {TOPICS.map((t) => (
          <span key={t} className="rounded-full border border-line px-3 py-1">{t}</span>
        ))}
      </div>
      {error && <p className="text-sm text-rose-400">{error}</p>}
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

// ─── Loading screen ───────────────────────────────────────────────────────────
function LoadingScreen() {
  return (
    <div className="flex h-60 items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-blue" />
        <span className="text-xs text-[#4a6080]">Loading conversation…</span>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
// View states (explicit — avoids multi-boolean race conditions):
// "loading"     — have a conversationId in localStorage, fetching history from API
// "landing"     — no conversation, waiting for user to click Begin
// "chat"        — conversation active, user is typing answers
// "completed"   — onboarding finished
type ViewState = "loading" | "landing" | "chat" | "completed";

export function OnboardingPage() {
  const { session } = useAuth();
  const userId = session!.userId;
  const navigate = useNavigate();

  const [view, setView] = useState<ViewState>("loading");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [visibleCount, setVisibleCount] = useState(0);
  const [typing, setTyping] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // ── On mount: check backend state before showing anything ─────────────────
  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const storedId = localStorage.getItem(storageKey(userId));

      // Helper: load a conversation state and update component state
      async function loadConversation(convId: string): Promise<boolean> {
        try {
          const state = await onboardingApi.state(convId);
          if (cancelled) return false;
          const msgs: ChatMessage[] = (state.messages ?? []).map((m) => ({
            role: String(m.role ?? "assistant"),
            content: String(m.content ?? ""),
            question_id: m.question_id ?? null,
            created_at: m.created_at ? String(m.created_at) : undefined,
          }));
          // Save the ID to localStorage so future reloads are fast
          localStorage.setItem(storageKey(userId), convId);
          setMessages(msgs);
          setVisibleCount(msgs.length);
          setConversationId(convId);
          setView(state.status === "completed" ? "completed" : "chat");
          return true;
        } catch (err) {
          if (err && typeof err === "object" && "status" in err && (err as { status: number }).status === 404) {
            localStorage.removeItem(storageKey(userId));
          }
          return false;
        }
      }

      // Step 1 — try stored ID first (fast path)
      if (storedId) {
        const ok = await loadConversation(storedId);
        if (ok || cancelled) return;
      }

      // Step 2 — no stored ID or it failed, look up by user ID from backend
      try {
        const state = await onboardingApi.latestForUser(userId);
        if (cancelled) return;
        const convId = state.conversation_id;
        const msgs: ChatMessage[] = (state.messages ?? []).map((m) => ({
          role: String(m.role ?? "assistant"),
          content: String(m.content ?? ""),
          question_id: m.question_id ?? null,
          created_at: m.created_at ? String(m.created_at) : undefined,
        }));
        console.log("[onboarding bootstrap] latestForUser →", {
          convId,
          status: state.status,
          messageCount: msgs.length,
          rawMessages: state.messages,
        });
        localStorage.setItem(storageKey(userId), convId);
        setMessages(msgs);
        setVisibleCount(msgs.length);
        setConversationId(convId);
        setView(state.status === "completed" ? "completed" : "chat");
        return;
      } catch (e) {
        console.log("[onboarding bootstrap] latestForUser failed →", e);
        // No conversation in DB at all — fall through
      }

      // Step 3 — no conversation anywhere, go to landing
      if (!cancelled) setView("landing");
    }

    void bootstrap();
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Animate messages in one-by-one ────────────────────────────────────────
  useEffect(() => {
    if (visibleCount >= messages.length) return;
    const t = setTimeout(() => setVisibleCount((c) => c + 1), 80);
    return () => clearTimeout(t);
  }, [visibleCount, messages.length]);

  // ── Auto-scroll ───────────────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [visibleCount, typing]);

  // ── Re-focus input ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!typing && view === "chat") {
      inputRef.current?.focus();
    }
  }, [typing, view]);

  // ─── Start a new session ──────────────────────────────────────────────────
  async function startSession() {
    setBusy(true);
    setError(null);
    try {
      const res = await onboardingApi.start(userId);
      localStorage.setItem(storageKey(userId), res.conversation_id);
      setConversationId(res.conversation_id);
      // backend returns first_question, fallback to message for future compat
      const firstText = res.first_question ?? res.message ?? "";
      const firstMsg: ChatMessage = {
        role: "assistant",
        content: firstText,
        question_id: res.question_id,
      };
      setMessages([firstMsg]);
      setVisibleCount(0);
      setView("chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start onboarding");
    } finally {
      setBusy(false);
    }
  }

  // ─── Send a message ───────────────────────────────────────────────────────
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

    // Hard timeout — LLM calls can be slow
    const timeoutId = setTimeout(() => {
      setTyping(false);
      setBusy(false);
      setError("The server took too long to respond. Please try again.");
    }, 90_000);

    try {
      const reply = await onboardingApi.send(conversationId, text);
      clearTimeout(timeoutId);
      setTyping(false);
      // backend returns assistant_response, fallback to message for future compat
      const replyText = reply.assistant_response ?? reply.message;
      if (replyText) {
        const assistantMsg: ChatMessage = {
          role: "assistant",
          content: replyText,
          question_id: reply.question_id,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      }
      // backend uses "completed"; "in_progress" kept for forward compat
      if (reply.status === "completed") {
        profileApi.triggerEmbedding(userId).catch(() => {/* best-effort */});
        setView("completed");
      }
    } catch (err) {
      clearTimeout(timeoutId);
      setTyping(false);
      setError(err instanceof Error ? err.message : "Message failed — please try again.");
    } finally {
      setBusy(false);
    }
  }

  // ─── Reset session ────────────────────────────────────────────────────────
  function resetSession() {
    localStorage.removeItem(storageKey(userId));
    setConversationId(null);
    setMessages([]);
    setVisibleCount(0);
    setView("landing");
    setTyping(false);
    setDraft("");
    setError(null);
  }

  const assistantCount = messages.filter((m) => m.role === "assistant").length;

  // ── Render by explicit view state ─────────────────────────────────────────
  if (view === "loading") return <LoadingScreen />;

  if (view === "landing") {
    return (
      <div className="mx-auto max-w-xl">
        <LandingState onStart={startSession} busy={busy} error={error} />
      </div>
    );
  }

  if (view === "completed") {
    // Always show chat layout with completion banner when we have a conversation
    // Fall back to standalone screen only if truly no messages AND no conversation ID
    const showChat = messages.length > 0 || conversationId !== null;

    if (showChat) {
      return (
        <div className="mx-auto flex max-w-5xl gap-8" style={{ height: "calc(100vh - 88px)" }}>
          <ProgressStepper assistantCount={assistantCount} />

          <div className="flex flex-1 flex-col min-w-0">
            {/* Completion banner */}
            <div className="pb-3">
              <CompletionBanner
                onRedo={resetSession}
                onMatches={() => navigate("/matches")}
              />
            </div>

            {messages.length === 0 ? (
              <div className="flex flex-1 items-center justify-center">
                <p className="text-sm text-[#4a6080]">No message history available.</p>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-1">
                {messages.slice(0, visibleCount).map((msg, i) => (
                  <Bubble key={`${msg.role}-${i}`} msg={msg} visible={i < visibleCount} />
                ))}
                <div ref={bottomRef} />
              </div>
            )}
          </div>
        </div>
      );
    }

    // No conversation at all — standalone screen
    return (
      <div className="mx-auto max-w-xl">
        <CompletionScreen
          onContinue={() => navigate("/matches")}
          onRedo={resetSession}
        />
      </div>
    );
  }

  // view === "chat"
  return (
    <div className="mx-auto flex max-w-5xl gap-8" style={{ height: "calc(100vh - 88px)" }}>
      <ProgressStepper assistantCount={assistantCount} />

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
          {error && (
            <div className="mb-2 flex items-center justify-between gap-3 rounded-xl border border-rose-400/20 bg-rose-400/8 px-3 py-2">
              <p className="text-sm text-rose-400">{error}</p>
              <button
                type="button"
                onClick={() => setError(null)}
                className="shrink-0 text-xs text-rose-400/60 hover:text-rose-400 transition-colors"
              >
                ✕
              </button>
            </div>
          )}
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
