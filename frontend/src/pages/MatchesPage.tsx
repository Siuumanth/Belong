import { useEffect, useRef, useState } from "react";
import { matchApi, type MatchJob, type MatchResultItem } from "../lib/api";
import { useAuth } from "../lib/auth";
import { usePoll } from "../lib/usePoll";

// ─── Verdict helpers ──────────────────────────────────────────────────────────
const VERDICT_STYLES: Record<string, { dot: string; label: string; text: string }> = {
  strong_alignment: {
    dot: "bg-emerald-400",
    label: "text-emerald-400",
    text: "Strong alignment",
  },
  partial_alignment: {
    dot: "bg-amber-400",
    label: "text-amber-400",
    text: "Partial alignment",
  },
  conflict: { dot: "bg-rose-400", label: "text-rose-400", text: "Conflict" },
  unclear: { dot: "bg-zinc-500", label: "text-zinc-500", text: "Unclear" },
};

function verdictStyle(v?: string) {
  const key = (v ?? "").toLowerCase().replace(/\s+/g, "_");
  return (
    VERDICT_STYLES[key] ?? {
      dot: "bg-zinc-500",
      label: "text-zinc-500",
      text: v ?? "unclear",
    }
  );
}

// ─── Dimension row ────────────────────────────────────────────────────────────
function DimensionRow({
  name,
  result,
}: {
  name: string;
  result: { verdict?: string; evidence_a?: string; evidence_b?: string };
}) {
  const [open, setOpen] = useState(false);
  const style = verdictStyle(result.verdict);
  const hasEvidence = result.evidence_a || result.evidence_b;

  return (
    <li className="rounded-xl bg-ink/60 border border-line/60">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
      >
        <span className={`h-2 w-2 shrink-0 rounded-full ${style.dot}`} />
        <span className="flex-1 text-sm capitalize text-zinc-200">
          {name.replaceAll("_", " ")}
        </span>
        <span className={`text-xs ${style.label}`}>{style.text}</span>
        {hasEvidence && (
          <svg
            className={`h-3.5 w-3.5 shrink-0 text-zinc-600 transition-transform ${open ? "rotate-180" : ""}`}
            viewBox="0 0 12 12"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path d="M2 4l4 4 4-4" />
          </svg>
        )}
      </button>
      {open && hasEvidence && (
        <div className="border-t border-line/40 px-4 py-3 space-y-2 text-xs text-zinc-500">
          {result.evidence_a && (
            <p>
              <span className="text-zinc-400">You: </span>"{result.evidence_a}"
            </p>
          )}
          {result.evidence_b && (
            <p>
              <span className="text-zinc-400">Them: </span>"{result.evidence_b}"
            </p>
          )}
        </div>
      )}
    </li>
  );
}

// ─── Tag pill list ────────────────────────────────────────────────────────────
function TagList({
  label,
  items,
  tone,
}: {
  label: string;
  items?: string[];
  tone: string;
}) {
  if (!items?.length) return null;
  return (
    <div className="mt-4">
      <p className={`mb-2 text-xs uppercase tracking-wide ${tone}`}>{label}</p>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <span
            key={item}
            className="rounded-full border border-line px-3 py-1 text-xs text-zinc-400"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

// ─── Match card ───────────────────────────────────────────────────────────────
function MatchCard({ match, index }: { match: MatchResultItem; index: number }) {
  const [visible, setVisible] = useState(false);
  const ref = useRef<HTMLElement>(null);

  // Staggered entrance animation
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), index * 120);
    return () => clearTimeout(t);
  }, [index]);

  const dimensions = Object.entries(match.dimension_results ?? {});
  const overallVerdicts = dimensions.map(([, r]) => r.verdict ?? "unclear");
  const strongCount = overallVerdicts.filter((v) =>
    v.includes("strong"),
  ).length;
  const conflictCount = overallVerdicts.filter((v) =>
    v.includes("conflict"),
  ).length;

  return (
    <article
      ref={ref}
      className={`rounded-2xl border border-line bg-panel p-6 transition-all duration-500 ${
        visible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-zinc-500">Match</p>
          <p className="mt-1 font-mono text-xs text-zinc-600 break-all">
            {match.candidate_id}
          </p>
        </div>
        <div className="flex shrink-0 gap-2 text-xs">
          {strongCount > 0 && (
            <span className="rounded-full bg-emerald-400/10 px-2.5 py-1 text-emerald-400">
              {strongCount} strong
            </span>
          )}
          {conflictCount > 0 && (
            <span className="rounded-full bg-rose-400/10 px-2.5 py-1 text-rose-400">
              {conflictCount} conflict
            </span>
          )}
        </div>
      </div>

      {/* Dimensions */}
      {dimensions.length > 0 && (
        <ul className="mt-5 space-y-2">
          {dimensions.map(([name, result]) => (
            <DimensionRow key={name} name={name} result={result} />
          ))}
        </ul>
      )}

      <TagList
        label="Alignments"
        items={match.strong_alignments}
        tone="text-emerald-400"
      />
      <TagList
        label="Potential conflicts"
        items={match.potential_conflicts}
        tone="text-amber-400"
      />
      {(match.dealbreaker_violations?.length ?? 0) > 0 && (
        <TagList
          label="Dealbreakers triggered"
          items={match.dealbreaker_violations}
          tone="text-rose-400"
        />
      )}
      <TagList
        label="Needs more info"
        items={match.uncertainties}
        tone="text-zinc-500"
      />
    </article>
  );
}

// ─── Animated wait screen ─────────────────────────────────────────────────────
const WAIT_LINES = [
  "Applying hard filters…",
  "Running vector recall…",
  "Reasoning about compatibility…",
  "Ranking your matches…",
];

function WaitScreen({ jobStatus }: { jobStatus: string }) {
  const [lineIndex, setLineIndex] = useState(0);

  useEffect(() => {
    const t = setInterval(() => {
      setLineIndex((i) => (i + 1) % WAIT_LINES.length);
    }, 1800);
    return () => clearInterval(t);
  }, []);

  const label =
    jobStatus === "running"
      ? WAIT_LINES[lineIndex]
      : jobStatus === "pending"
        ? "Queued, starting soon…"
        : "Working…";

  return (
    <div className="flex flex-col items-center justify-center gap-6 py-20 text-center">
      {/* Pulsing ring */}
      <div className="relative flex h-16 w-16 items-center justify-center">
        <div className="absolute inset-0 animate-ping rounded-full bg-gold/20" />
        <div className="relative h-10 w-10 rounded-full bg-gold/30 flex items-center justify-center text-gold text-lg">
          ✦
        </div>
      </div>
      <div>
        <p className="font-display text-xl text-gold">Finding your matches</p>
        <p className="mt-2 h-5 text-sm text-zinc-500 transition-all duration-300">
          {label}
        </p>
      </div>
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
    matchApi
      .latest(userId)
      .then((res) => {
        if (!cancelled) {
          setMatches(res.matches ?? []);
          setHasLoaded(true);
        }
      })
      .catch(() => {
        if (!cancelled) setHasLoaded(true);
      });
    return () => { cancelled = true; };
  }, [userId]);

  // Polling hook for async match job
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const { status: pollStatus, data: pollData, start: startPoll, error: pollError } = usePoll<MatchJob>({
    fn: () => matchApi.job(activeJobId!),
    until: (job) => job.status === "completed" || job.status === "failed",
    interval: 2000,
    maxAttempts: 60,
    onDone: (job) => {
      if (job.status === "completed") {
        setMatches(job.matches ?? []);
      } else {
        setGlobalError("Matching job failed. Try again.");
      }
    },
    onError: () => setGlobalError("Polling timed out. Try again."),
  });

  // Start poll whenever we get a new jobId
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
    <section className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl">Matches</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Hard filters → vector recall → pairwise reasoning. No fake scores.
          </p>
        </div>
        <button
          type="button"
          onClick={runMatch}
          disabled={isPolling}
          className="rounded-full bg-gold px-5 py-2 text-sm font-medium text-ink hover:bg-[#e0b88a] disabled:opacity-50"
        >
          {isPolling ? "Running…" : matches.length > 0 ? "Refresh matches" : "Find matches"}
        </button>
      </div>

      {/* Error */}
      {(globalError ?? pollError) && (
        <p className="text-sm text-rose-400">{globalError ?? pollError}</p>
      )}

      {/* Wait screen */}
      {isPolling && <WaitScreen jobStatus={jobStatus} />}

      {/* Empty state */}
      {!isPolling && hasLoaded && matches.length === 0 && (
        <div className="rounded-2xl border border-dashed border-line p-12 text-center">
          <p className="text-zinc-500">No matches yet.</p>
          <p className="mt-1 text-sm text-zinc-600">
            Complete your profile and onboarding first, then hit{" "}
            <span className="text-zinc-400">Find matches</span>.
          </p>
        </div>
      )}

      {/* Match cards */}
      {!isPolling && (
        <div className="grid gap-5">
          {matches.map((match, i) => (
            <MatchCard key={match.candidate_id} match={match} index={i} />
          ))}
        </div>
      )}
    </section>
  );
}
