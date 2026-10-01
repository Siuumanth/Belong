import { useEffect, useRef, useState } from "react";
import { matchApi, type MatchJob, type MatchResultItem, type OverallVerdict, type DimensionResult } from "../lib/api";
import { useAuth } from "../lib/auth";
import { usePoll } from "../lib/usePoll";

// ─── Verdict config ───────────────────────────────────────────────────────────
type VerdictStyle = { dot: string; badge: string; label: string; text: string };

const VERDICT_MAP: Record<string, VerdictStyle> = {
  strong_alignment: {
    dot: "bg-[#d4a843]",
    badge: "bg-[#d4a843]/10 text-[#d4a843] border-[#d4a843]/25",
    label: "text-[#d4a843]",
    text: "Strong alignment",
  },
  partial_alignment: {
    dot: "bg-[#fb923c]",
    badge: "bg-[#fb923c]/10 text-[#fb923c] border-[#fb923c]/25",
    label: "text-[#fb923c]",
    text: "Partial alignment",
  },
  conflict: {
    dot: "bg-rose-400",
    badge: "bg-rose-400/10 text-rose-400 border-rose-400/20",
    label: "text-rose-400",
    text: "Conflict",
  },
  unclear: {
    dot: "bg-zinc-500",
    badge: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
    label: "text-zinc-400",
    text: "Unclear",
  },
};

function verdictStyle(v?: string): VerdictStyle {
  const key = (v ?? "").toLowerCase().replace(/\s+/g, "_");
  return VERDICT_MAP[key] ?? VERDICT_MAP.unclear;
}

// helper: get display ID / name
function matchDisplayId(m: MatchResultItem): string {
  return m.user_b_id ?? m.candidate_id ?? "unknown";
}
function matchLabel(m: MatchResultItem): string {
  if (m.user_b_name) return m.user_b_name;
  const id = matchDisplayId(m);
  return id.length > 13 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id;
}
function matchInitials(m: MatchResultItem): string {
  if (m.user_b_name) {
    return m.user_b_name
      .split(" ")
      .map((w) => w[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();
  }
  return matchDisplayId(m).slice(0, 2).toUpperCase();
}

// ─── Overall verdict badge ────────────────────────────────────────────────────
function OverallBadge({ verdict }: { verdict?: OverallVerdict | string }) {
  const s = verdictStyle(verdict);
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${s.badge}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {s.text}
    </span>
  );
}

// ─── Dimension row ────────────────────────────────────────────────────────────
function DimensionRow({ name, result }: { name: string; result: DimensionResult }) {
  const [open, setOpen] = useState(false);
  const s = verdictStyle(result.verdict);
  const hasDetail =
    result.reasoning ||
    result.evidence_a ||
    result.evidence_b ||
    (result.evidence_a_ids?.length ?? 0) > 0 ||
    (result.evidence_b_ids?.length ?? 0) > 0;

  return (
    <li className="rounded-xl border border-line bg-ink/40 overflow-hidden">
      <button
        type="button"
        onClick={() => hasDetail && setOpen((o) => !o)}
        className={`flex w-full items-center gap-3 px-4 py-3 text-left ${hasDetail ? "cursor-pointer" : "cursor-default"}`}
      >
        <span className={`h-2 w-2 shrink-0 rounded-full ${s.dot}`} />
        <span className="flex-1 text-sm capitalize text-[#c8d8f0]">
          {name.replaceAll("_", " ")}
        </span>
        <span className={`text-xs font-medium ${s.label}`}>{s.text}</span>
        {hasDetail && (
          <svg className={`h-3 w-3 shrink-0 text-[#4a6080] transition-transform ${open ? "rotate-180" : ""}`}
            viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <path d="M2 4l4 4 4-4" />
          </svg>
        )}
      </button>
      {open && hasDetail && (
        <div className="border-t border-line/50 px-4 py-3 space-y-2.5 text-xs">
          {result.reasoning && (
            <p className="leading-relaxed text-[#8fa3bf]">{result.reasoning}</p>
          )}
          {result.evidence_a && (
            <p className="text-[#4a6080]">
              <span className="text-[#8fa3bf]">Your signal: </span>"{result.evidence_a}"
            </p>
          )}
          {result.evidence_b && (
            <p className="text-[#4a6080]">
              <span className="text-[#8fa3bf]">Their signal: </span>"{result.evidence_b}"
            </p>
          )}
          {(result.evidence_a_ids ?? []).length > 0 && (
            <p className="font-mono text-[10px] text-[#4a6080]">
              <span className="text-[#5a7090]">Your IDs: </span>{result.evidence_a_ids!.join(", ")}
            </p>
          )}
          {(result.evidence_b_ids ?? []).length > 0 && (
            <p className="font-mono text-[10px] text-[#4a6080]">
              <span className="text-[#5a7090]">Their IDs: </span>{result.evidence_b_ids!.join(", ")}
            </p>
          )}
        </div>
      )}
    </li>
  );
}

// ─── Tag section ──────────────────────────────────────────────────────────────
function TagSection({ label, items, tone, icon }: {
  label: string; items?: string[]; tone: string; icon: string;
}) {
  if (!items?.length) return null;
  return (
    <div className="mt-4">
      <p className={`mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide ${tone}`}>
        <span>{icon}</span>{label}
      </p>
      <div className="flex flex-wrap gap-2">
        {items.map((item, i) => (
          <span key={i} className="rounded-full border border-line bg-ink/30 px-3 py-1 text-xs text-[#8fa3bf] leading-relaxed">
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

// ─── Overall reasoning block ──────────────────────────────────────────────────
function ReasoningBlock({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = text.length > 220;
  const display = isLong && !expanded ? `${text.slice(0, 220)}…` : text;
  return (
    <div className="mt-4 rounded-xl border border-line/60 bg-ink/30 px-4 py-3">
      <p className="mb-1.5 text-[10px] uppercase tracking-widest text-[#4a6080]">Reasoning</p>
      <p className="text-sm leading-relaxed text-[#8fa3bf]">{display}</p>
      {isLong && (
        <button type="button" onClick={() => setExpanded((e) => !e)}
          className="mt-2 text-xs text-blue hover:underline">
          {expanded ? "Show less" : "Read more"}
        </button>
      )}
    </div>
  );
}

// ─── Detail modal ─────────────────────────────────────────────────────────────
function DetailModal({ resultId, onClose }: { resultId: string; onClose: () => void }) {
  const [match, setMatch] = useState<MatchResultItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    matchApi.detail(resultId)
      .then((m) => { setMatch(m); setLoading(false); })
      .catch((e) => { setError(e instanceof Error ? e.message : "Failed to load"); setLoading(false); });
  }, [resultId]);

  // close on backdrop click
  function onBackdrop(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 backdrop-blur-sm overflow-y-auto py-8 px-4"
      onClick={onBackdrop}
    >
      <div className="relative w-full max-w-2xl rounded-3xl border border-line bg-panel shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-line px-6 py-4">
          <p className="text-sm font-semibold text-[#e8edf8]">Match detail</p>
          <button type="button" onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded-lg text-[#4a6080] hover:bg-line hover:text-[#e8edf8] transition-colors">
            ✕
          </button>
        </div>

        <div className="p-6">
          {loading && (
            <div className="flex h-40 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-blue" />
            </div>
          )}
          {error && <p className="text-sm text-rose-400">{error}</p>}
          {match && (
            <div className="space-y-5">
              {/* Identity */}
              <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-blue/10 text-lg font-semibold text-blue">
                  {matchInitials(match)}
                </div>
                <div>
                  <p className="font-semibold text-[#e8edf8]">{matchLabel(match)}</p>
                  <div className="mt-1"><OverallBadge verdict={match.overall_verdict} /></div>
                </div>
              </div>

              {/* Overall reasoning — second-person voice */}
              {match.overall_reasoning && <ReasoningBlock text={match.overall_reasoning} />}

              {/* Dimensions */}
              {Object.entries(match.dimension_results ?? {}).length > 0 && (
                <div>
                  <p className="mb-2 text-[10px] uppercase tracking-widest text-[#4a6080]">Dimensions</p>
                  <ul className="space-y-2">
                    {Object.entries(match.dimension_results!).map(([name, result]) => (
                      <DimensionRow key={name} name={name} result={result} />
                    ))}
                  </ul>
                </div>
              )}

              <TagSection label="Complementary alignments" items={match.complementary_alignments} tone="text-indigo-400" icon="⟷" />
              <TagSection label="Shared alignments" items={match.shared_alignments} tone="text-[#d4a843]" icon="≈" />
              <TagSection label="Strong alignments" items={match.strong_alignments} tone="text-[#d4a843]" icon="✦" />
              <TagSection label="Potential conflicts" items={match.potential_conflicts} tone="text-[#fb923c]" icon="△" />
              {(match.dealbreaker_violations?.length ?? 0) > 0 && (
                <TagSection label="Dealbreaker violations" items={match.dealbreaker_violations} tone="text-rose-400" icon="✕" />
              )}
              <TagSection label="Needs more info" items={match.uncertainties} tone="text-zinc-400" icon="?" />

              {/* Timestamps */}
              {match.created_at && (
                <p className="text-[10px] text-[#4a6080]">
                  Generated {new Date(match.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Match card (summary) ─────────────────────────────────────────────────────
function MatchCard({ match, index }: { match: MatchResultItem; index: number }) {
  const [visible, setVisible] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), index * 100);
    return () => clearTimeout(t);
  }, [index]);

  const dimensions = Object.entries(match.dimension_results ?? {});
  const verdicts = dimensions.map(([, r]) => r.verdict ?? "unclear");
  const strongCount = verdicts.filter((v) => v.includes("strong")).length;
  const partialCount = verdicts.filter((v) => v.includes("partial")).length;
  const conflictCount = verdicts.filter((v) => v.includes("conflict")).length;

  const resultId = match.id ?? null;

  return (
    <>
      <article
        ref={ref}
        className={`card-hover rounded-2xl border border-line bg-panel transition-all duration-500 ${
          visible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"
        }`}
      >
        {/* Card header */}
        <div className="flex items-start gap-4 p-6 pb-4">
          {/* Avatar */}
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-blue/10 text-base font-semibold text-blue">
            {matchInitials(match)}
          </div>

          <div className="flex-1 min-w-0">
            {/* Name or truncated ID */}
            <p className="font-semibold text-[#e8edf8]">{matchLabel(match)}</p>
            {match.user_b_name && (
              <p className="mt-0.5 font-mono text-[10px] text-[#4a6080] break-all">
                {matchDisplayId(match)}
              </p>
            )}
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <OverallBadge verdict={match.overall_verdict} />
            </div>
          </div>

          {/* Dimension summary pills */}
          <div className="hidden sm:flex shrink-0 flex-col items-end gap-1 text-[10px]">
            {strongCount > 0 && (
              <span className="rounded-full bg-[#d4a843]/10 px-2.5 py-0.5 text-[#d4a843]">{strongCount} strong</span>
            )}
            {partialCount > 0 && (
              <span className="rounded-full bg-[#fb923c]/10 px-2.5 py-0.5 text-[#fb923c]">{partialCount} partial</span>
            )}
            {conflictCount > 0 && (
              <span className="rounded-full bg-rose-400/10 px-2.5 py-0.5 text-rose-400">{conflictCount} conflict</span>
            )}
          </div>
        </div>

        {/* Overall reasoning preview — second-person voice */}
        {match.overall_reasoning && (
          <div className="px-6">
            <p className="text-sm leading-relaxed text-[#8fa3bf] line-clamp-3">
              {match.overall_reasoning}
            </p>
          </div>
        )}

        {/* Dimension dots bar */}
        {dimensions.length > 0 && (
          <div className="mt-4 px-6">
            <div className="flex flex-wrap gap-2">
              {dimensions.map(([name, result]) => {
                const s = verdictStyle(result.verdict);
                return (
                  <span key={name} className="flex items-center gap-1.5 rounded-full border border-line/60 bg-ink/30 px-2.5 py-1 text-[11px] text-[#8fa3bf] capitalize">
                    <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
                    {name.replaceAll("_", " ")}
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="mt-4 flex items-center justify-between border-t border-line/50 px-6 py-3">
          <div className="flex flex-wrap gap-3 text-xs text-[#4a6080]">
            {(match.complementary_alignments?.length ?? 0) > 0 && (
              <span>{match.complementary_alignments!.length} complementary</span>
            )}
            {(match.shared_alignments?.length ?? 0) > 0 && (
              <span>{match.shared_alignments!.length} shared</span>
            )}
            {(match.dealbreaker_violations?.length ?? 0) > 0 && (
              <span className="text-rose-400">{match.dealbreaker_violations!.length} dealbreaker{match.dealbreaker_violations!.length > 1 ? "s" : ""}</span>
            )}
          </div>
          {resultId && (
            <button
              type="button"
              onClick={() => setShowDetail(true)}
              className="text-xs text-blue hover:underline"
            >
              Full analysis →
            </button>
          )}
        </div>
      </article>

      {showDetail && resultId && (
        <DetailModal resultId={resultId} onClose={() => setShowDetail(false)} />
      )}
    </>
  );
}

// ─── Wait screen ──────────────────────────────────────────────────────────────
const WAIT_LINES = [
  "Applying hard filters…",
  "Running pgvector recall…",
  "Reasoning about compatibility…",
  "Ranking your matches…",
];

function WaitScreen({ jobStatus }: { jobStatus: string }) {
  const [lineIndex, setLineIndex] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setLineIndex((i) => (i + 1) % WAIT_LINES.length), 2000);
    return () => clearInterval(t);
  }, []);
  const label = jobStatus === "running" ? WAIT_LINES[lineIndex]
    : jobStatus === "pending" ? "Queued, starting soon…" : "Working…";
  return (
    <div className="flex flex-col items-center justify-center gap-8 py-24 text-center">
      <div className="relative flex h-20 w-20 items-center justify-center">
        <div className="absolute inset-0 rounded-full border border-blue/20 animate-pulse-ring" />
        <div className="relative h-14 w-14 rounded-full bg-blue/10 border border-blue/20 flex items-center justify-center">
          <svg className="animate-spin text-blue" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
          </svg>
        </div>
      </div>
      <div>
        <p className="font-display text-2xl font-light text-[#e8edf8]">Finding your matches</p>
        <p className="mt-2 h-5 text-sm text-[#8fa3bf] transition-all duration-500">{label}</p>
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        {["Hard filters", "Vector recall", "LLM reasoning"].map((stage, i) => (
          <span key={stage} className={`rounded-full border px-3 py-1 text-xs transition-all duration-500 ${
            i === lineIndex % 3 ? "border-blue/40 bg-blue/10 text-blue" : "border-line text-[#4a6080]"
          }`}>{stage}</span>
        ))}
      </div>
    </div>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────
function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-line p-16 text-center">
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-panel text-2xl">✦</div>
      <p className="font-medium text-[#8fa3bf]">No matches yet</p>
      <p className="mt-2 text-sm text-[#4a6080]">
        Complete your profile and onboarding first, then run a match.
      </p>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export function MatchesPage() {
  const { session } = useAuth();
  const userId = session!.userId;

  const [matches, setMatches] = useState<MatchResultItem[]>([]);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);

  // Load persisted matches on mount
  useEffect(() => {
    let cancelled = false;
    matchApi.latest(userId)
      .then((res) => {
        if (!cancelled) { setMatches(res.matches ?? []); setHasLoaded(true); }
      })
      .catch(() => { if (!cancelled) setHasLoaded(true); });
    return () => { cancelled = true; };
  }, [userId]);

  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const { status: pollStatus, data: pollData, start: startPoll, error: pollError } = usePoll<MatchJob>({
    fn: () => matchApi.job(activeJobId!),
    until: (job) => job.status === "completed" || job.status === "failed",
    interval: 2500,
    maxAttempts: 60,
    onDone: (job) => {
      if (job.status === "completed") {
        // Fetch the rich results from the job-results endpoint
        matchApi.jobResults(activeJobId!)
          .then((res) => setMatches(res.matches ?? []))
          .catch(() => {
            // Fall back to latest if job-results fails
            matchApi.latest(userId).then((res) => setMatches(res.matches ?? [])).catch(() => {});
          });
      } else {
        setGlobalError("Matching job failed — try again.");
      }
    },
    onError: () => setGlobalError("Polling timed out — try again."),
  });

  useEffect(() => {
    if (activeJobId) startPoll();
  }, [activeJobId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function runMatch() {
    setGlobalError(null);
    try {
      const accepted = await matchApi.createJob(userId, 5);
      setActiveJobId(accepted.job_id);
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : "Could not start matching");
    }
  }

  const isPolling = pollStatus === "polling";
  const jobStatus = isPolling && pollData ? pollData.status : "";

  return (
    <section className="space-y-6 py-2">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-light text-[#e8edf8]">Matches</h1>
          <p className="mt-1.5 text-sm text-[#8fa3bf]">
            Hard filters → vector recall → pairwise reasoning. Addressed directly to you.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {matches.length > 0 && (
            <span className="text-xs text-[#4a6080]">
              {matches.length} result{matches.length !== 1 ? "s" : ""}
            </span>
          )}
          <button
            type="button"
            onClick={runMatch}
            disabled={isPolling}
            className="rounded-xl bg-blue px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-blue/20 hover:bg-blue-dim disabled:opacity-50 transition-all"
          >
            {isPolling ? "Running…" : matches.length > 0 ? "Refresh matches" : "Find matches"}
          </button>
        </div>
      </div>

      {/* Pipeline legend */}
      <div className="flex flex-wrap gap-2">
        {[
          { label: "Hard filters", icon: "⊘" },
          { label: "Vector recall", icon: "◎" },
          { label: "LLM reasoning", icon: "◈" },
        ].map((s) => (
          <span key={s.label} className="flex items-center gap-1.5 rounded-full border border-line px-3 py-1 text-xs text-[#4a6080]">
            <span>{s.icon}</span>{s.label}
          </span>
        ))}
      </div>

      {/* Error */}
      {(globalError ?? pollError) && (
        <div className="flex items-center gap-2 rounded-xl border border-rose-400/20 bg-rose-400/8 px-4 py-3 text-sm text-rose-400">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {globalError ?? pollError}
        </div>
      )}

      {/* Wait screen */}
      {isPolling && <WaitScreen jobStatus={jobStatus} />}

      {/* Empty state */}
      {!isPolling && hasLoaded && matches.length === 0 && <EmptyState />}

      {/* Match cards */}
      {!isPolling && (
        <div className="grid gap-5">
          {matches.map((match, i) => (
            <MatchCard
              key={match.id ?? match.match_id ?? match.user_b_id ?? match.candidate_id ?? i}
              match={match}
              index={i}
            />
          ))}
        </div>
      )}
    </section>
  );
}
