import { useEffect, useState, type FormEvent } from "react";
import { Button, ErrorText, GhostButton, inputClass } from "../components/ui";
import { onboardingApi, type ChatMessage } from "../lib/api";
import { useAuth } from "../lib/auth";

const storageKey = (userId: string) => `belong_conversation_${userId}`;

export function OnboardingPage() {
  const { session } = useAuth();
  const userId = session!.userId;
  const [conversationId, setConversationId] = useState<string | null>(
    () => localStorage.getItem(storageKey(userId)),
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState("idle");
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!conversationId) return;
    let cancelled = false;
    onboardingApi
      .state(conversationId)
      .then((state) => {
        if (cancelled) return;
        setMessages(state.messages ?? []);
        setStatus(state.status);
      })
      .catch(() => {
        if (!cancelled) {
          localStorage.removeItem(storageKey(userId));
          setConversationId(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [conversationId, userId]);

  async function startSession() {
    setBusy(true);
    setError(null);
    try {
      const sessionRes = await onboardingApi.start(userId);
      localStorage.setItem(storageKey(userId), sessionRes.conversation_id);
      setConversationId(sessionRes.conversation_id);
      setStatus("in_progress");
      setMessages([
        {
          role: "assistant",
          content: sessionRes.message,
          question_id: sessionRes.question_id,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start onboarding");
    } finally {
      setBusy(false);
    }
  }

  async function send(e: FormEvent) {
    e.preventDefault();
    if (!conversationId || !draft.trim()) return;
    const text = draft.trim();
    setDraft("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setBusy(true);
    setError(null);
    try {
      const reply = await onboardingApi.send(conversationId, text);
      setStatus(reply.status);
      if (reply.message) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: reply.message ?? "",
            question_id: reply.question_id,
          },
        ]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Message failed");
    } finally {
      setBusy(false);
    }
  }

  const done = status === "completed";

  return (
    <section className="space-y-6">
      <div>
        <h1 className="font-display text-3xl">Onboarding</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Six broad questions, with follow-ups only when an answer is thin or contradictory.
        </p>
      </div>

      {!conversationId ? (
        <div className="rounded-2xl border border-line bg-panel p-8">
          <p className="text-zinc-400">Start a conversation to extract your profile signals.</p>
          <div className="mt-4">
            <Button type="button" onClick={startSession} disabled={busy}>
              {busy ? "Starting…" : "Begin"}
            </Button>
          </div>
          <ErrorText message={error} />
        </div>
      ) : (
        <div className="rounded-2xl border border-line bg-panel p-6">
          <div className="mb-4 flex items-center justify-between">
            <p className="text-xs uppercase tracking-wide text-zinc-500">{status}</p>
            <GhostButton
              type="button"
              onClick={() => {
                localStorage.removeItem(storageKey(userId));
                setConversationId(null);
                setMessages([]);
                setStatus("idle");
              }}
            >
              New session
            </GhostButton>
          </div>
          <div className="space-y-3">
            {messages.map((msg, i) => (
              <div
                key={`${msg.role}-${i}`}
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
                  msg.role === "user"
                    ? "ml-auto bg-gold/15 text-zinc-100"
                    : "bg-ink text-zinc-300"
                }`}
              >
                {msg.content}
              </div>
            ))}
          </div>
          {done ? (
            <p className="mt-6 text-sm text-emerald-400">Onboarding complete. Signals are being stored on your profile.</p>
          ) : (
            <form className="mt-6 flex gap-2" onSubmit={send}>
              <input
                className={inputClass}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Answer in your own words"
                disabled={busy}
              />
              <Button type="submit" disabled={busy || !draft.trim()}>
                Send
              </Button>
            </form>
          )}
          <div className="mt-3">
            <ErrorText message={error} />
          </div>
        </div>
      )}
    </section>
  );
}
