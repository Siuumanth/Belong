import { useEffect, useRef, useState } from "react";
import { matchApi, type CandidateMatch, type DimensionResult, type MatchResultItem, type OverallVerdict } from "../lib/api";
import { useAuth } from "../lib/auth";

// ─── Verdict helpers ──────────────────────────────────────────────────────────
type VStyle = { dot: string; badge: string; label: string; text: string };

const VERDICT_MAP: Record<string, VStyle> = {
  strong_alignment: { dot: "bg-[#d4a843]",  badge: "bg-[#d4a843]/10 text-[#d4a843] border-[#d4a843]/25",   label: "text-[#d4a843]",  text: "Strong alignment"  },
  partial_alignment: { dot: "bg-[#fb923c]", badge: "bg-[#fb923c]/10 text-[#fb923c] border-[#fb923c]/25",  label: "text-[#fb923c]", text: "Partial alignment" },
  conflict:          { dot: "bg-rose-400",  badge: "bg-rose-400/10 text-rose-400 border-rose-400/20",       label: "text-rose-400",  text: "Conflict"          },
  unclear:           { dot: "bg-zinc-500",  badge: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",       label: "text-zinc-400",  text: "Unclear"           },
};
function vs(v?: string): VStyle {
  return VERDICT_MAP[(v ?? "").toLowerCase().replace(/\s+/g, "_")] ?? VERDICT_MAP.unclear;
}

function OverallBadge({ verdict }: { verdict?: OverallVerdict | string }) {
  const s = vs(verdict);
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${s.badge}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {s.text}
    </span>
  );
}

// ─── Score bar ────────────────────────────────────────────────────────────────
function ScoreBar({ score }: { score: number }) {
  // combined_score is 0-1 cosine-based; scale for display
  const pct = Math.min(Math.round(score * 100), 100);
  const color = pct >= 70 ? "bg-[#d4a843]" : pct >= 40 ? "bg-[#fb923c]" : "bg-zinc-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 rounded-full bg-line">
        <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 shrink-0 text-right text-[10px] text-[#4a6080]">{(score * 100).toFixed(0)}%</span>
    </div>
  );
}

// ─── Dimension row (in analysis panel) ───────────────────────────────────────
function DimensionRow({ name, result }: { name: string; result: DimensionResult }) {
  const [open, setOpen] = useState(false);
  const s = vs(result.verdict);
  const hasDetail = result.reasoning || result.evidence_a || result.evidence_b ||
    (result.evidence_a_ids?.length ?? 0) > 0 || (result.evidence_b_ids?.length ?? 0) > 0;

  return (
    <li className="rounded-xl border border-line bg-ink/40 overflow-hidden">
      <button
        type="button"
        onClick={() => hasDetail && setOpen(o => !o)}
        className={`flex w-full items-center gap-3 px-4 py-3 text-left ${hasDetail ? "cursor-pointer" : "cursor-default"}`}
      >
        <span className={`h-2 w-2 shrink-0 rounded-full ${s.dot}`} />
        <span className="flex-1 text-sm capitalize text-[#c8d8f0]">{name.replaceAll("_", " ")}</span>
        <span className={`text-xs font-medium ${s.label}`}>{s.text}</span>
        {hasDetail && (
          <svg className={`h-3 w-3 shrink-0 text-[#4a6080] transition-transform ${open ? "rotate-180" : ""}`}
            viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <path d="M2 4l4 4 4-4" />
          </svg>
        )}
      </button>
      {open && hasDetail && (
        <div className="border-t border-line/50 px-4 py-3 space-y-2 text-xs">
          {result.reasoning && <p className="leading-relaxed text-[#8fa3bf]">{result.reasoning}</p>}
          {result.evidence_a && <p className="text-[#4a6080]"><span className="text-[#8fa3bf]">Your signal: </span>"{result.evidence_a}"</p>}
          {result.evidence_b && <p className="text-[#4a6080]"><span className="text-[#8fa3bf]">Their signal: </span>"{result.evidence_b}"</p>}
          {(result.evidence_a_ids ?? []).length > 0 && (
            <p className="font-mono text-[10px] text-[#4a6080]"><span className="text-[#5a7090]">Your IDs: </span>{result.evidence_a_ids!.join(", ")}</p>
          )}
          {(result.evidence_b_ids ?? []).length > 0 && (
            <p className="font-mono text-[10px] text-[#4a6080]"><span className="text-[#5a7090]">Their IDs: </span>{result.evidence_b_ids!.join(", ")}</p>
          )}
        </div>
      )}
    </li>
  );
}

// ─── Tag section ──────────────────────────────────────────────────────────────
function TagSection({ label, items, tone, icon }: { label: string; items?: string[]; tone: string; icon: string }) {
  if (!items?.length) return null;
  return (
    <div className="mt-4">
      <p className={`mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide ${tone}`}>
        <span>{icon}</span>{label}
      </p>
      <div className="flex flex-wrap gap-2">
        {items.map((item, i) => (
          <span key={i} className="rounded-full border border-line bg-ink/30 px-3 py-1 text-xs text-[#8fa3bf]">{item}</span>
        ))}
      </div>
    </div>
  );
}

// ─── Analysis panel (Stage 2 result shown inline under the candidate card) ───
function AnalysisPanel({ result }: { result: MatchResultItem }) {
  const dims = Object.entries(result.dimension_results ?? {});
  return (
    <div className="border-t border-line/60 bg-ink/20 px-6 py-5 space-y-4">
      {/* Overall reasoning — second-person voice */}
      {result.overall_reasoning && (
        <div className="rounded-xl border border-line/60 bg-ink/30 px-4 py-3">
          <p className="mb-1.5 text-[10px] uppercase tracking-widest text-[#4a6080]">Analysis</p>
          <p className="text-sm leading-relaxed text-[#8fa3bf]">{result.overall_reasoning}</p>
        </div>
      )}

      {/* Dimension breakdown */}
      {dims.length > 0 && (
        <div>
          <p className="mb-2 text-[10px] uppercase tracking-widest text-[#4a6080]">Dimensions</p>
          <ul className="space-y-2">
            {dims.map(([name, r]) => <DimensionRow key={name} name={name} result={r} />)}
          </ul>
        </div>
      )}

      <TagSection label="Complementary alignments" items={result.complementary_alignments} tone="text-indigo-400" icon="⟷" />
      <TagSection label="Shared alignments"        items={result.shared_alignments}        tone="text-[#d4a843]"   icon="≈"  />
      <TagSection label="Strong alignments"        items={result.strong_alignments}        tone="text-[#d4a843]"   icon="✦"  />
      <TagSection label="Potential conflicts"      items={result.potential_conflicts}      tone="text-[#fb923c]"   icon="△"  />
      {(result.dealbreaker_violations?.length ?? 0) > 0 && (
        <TagSection label="Dealbreaker violations" items={result.dealbreaker_violations}   tone="text-rose-400"    icon="✕"  />
      )}
      <TagSection label="Needs more info"          items={result.uncertainties}            tone="text-zinc-400"    icon="?"  />

      {result.updated_at && (
        <p className="pt-1 text-[10px] text-[#4a6080]">
          Analysed {new Date(result.updated_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
        </p>
      )}
    </div>
  );
}

// ─── Single candidate card ────────────────────────────────────────────────────
function CandidateCard({
  candidate,
  index,
  userId,
}: {
  candidate: CandidateMatch;
  index: number;
  userId: string;
}) {
  const [visible, setVisible]         = useState(false);
  const [analysing, setAnalysing]     = useState(false);
  const [analysis, setAnalysis]       = useState<MatchResultItem | null>(null);
  const [analysisErr, setAnalysisErr] = useState<string | null>(null);
  const [expanded, setExpanded]       = useState(false);
  const ref = useRef<HTMLElement>(null);

  // staggered entrance
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), index * 80);
    return () => clearTimeout(t);
  }, [index]);

  // Try to load an existing analysis on first expand
  async function loadOrAnalyze() {
    if (analysis) { setExpanded(e => !e); return; }
    setExpanded(true);
    setAnalysisErr(null);
    setAnalysing(true);

    // First try fetching an existing saved result (no LLM cost)
    try {
      const existing = await matchApi.pairDetail(candidate.user_id);
      setAnalysis(existing);
      setAnalysing(false);
      return;
    } catch {
      // 404 = no saved result yet, fall through to run LLM
    }

    // Run on-demand LLM analysis (Stage 2)
    try {
      const result = await matchApi.analyze(candidate.user_id, userId);
      setAnalysis(result);
    } catch (err) {
      setAnalysisErr(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setAnalysing(false);
    }
  }

  const initials = candidate.name
    ? candidate.name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase()
    : candidate.user_id.slice(0, 2).toUpperCase();

  const score = candidate.combined_score ?? 0;

  return (
    <article
      ref={ref}
      className={`card-hover overflow-hidden rounded-2xl border border-line bg-panel transition-all duration-500 ${
        visible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"
      }`}
    >
      {/* Card header */}
      <div className="flex items-start gap-4 p-5">
        {/* Avatar */}
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-blue/10 text-base font-semibold text-blue">
          {initials}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-semibold text-[#e8edf8]">
                {candidate.name ?? `User ${candidate.user_id.slice(0, 8)}`}
              </p>
              <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-[#4a6080]">
                {candidate.age && <span>{candidate.age}</span>}
                {candidate.gender && <span className="capitalize">{candidate.gender}</span>}
                {candidate.relationship_goal && (
                  <span className="capitalize">{candidate.relationship_goal.replace("-", " ")}</span>
                )}
                {candidate.distance_km != null && (
                  <span className="flex items-center gap-1">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" />
                    </svg>
                    {candidate.distance_km.toFixed(1)} km
                  </span>
                )}
              </div>
            </div>

            {/* Analysis badge or Analyze Deeper button */}
            {analysis ? (
              <OverallBadge verdict={analysis.overall_verdict} />
            ) : (
              <button
                type="button"
                onClick={loadOrAnalyze}
                disabled={analysing}
                className="shrink-0 rounded-xl border border-blue/30 bg-blue/8 px-3.5 py-1.5 text-xs font-semibold text-blue hover:bg-blue/15 disabled:opacity-50 transition-all"
              >
                {analysing ? (
                  <span className="flex items-center gap-1.5">
                    <svg className="animate-spin" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                    </svg>
                    Analysing…
                  </span>
                ) : "Analyse deeper →"}
              </button>
            )}
          </div>

          {/* Compatibility score bar */}
          {score > 0 && (
            <div className="mt-3">
              <div className="mb-1 flex justify-between text-[10px] text-[#4a6080]">
                <span>Compatibility score</span>
              </div>
              <ScoreBar score={score} />
            </div>
          )}

          {/* Similarity breakdown pills */}
          <div className="mt-3 flex flex-wrap gap-2 text-[10px]">
            {candidate.cosine_similarity != null && (
              <span className="rounded-full border border-line px-2.5 py-0.5 text-[#4a6080]">
                Forward {(candidate.cosine_similarity * 100).toFixed(0)}%
              </span>
            )}
            {candidate.reverse_cosine_similarity != null && (
              <span className="rounded-full border border-line px-2.5 py-0.5 text-[#4a6080]">
                Reverse {(candidate.reverse_cosine_similarity * 100).toFixed(0)}%
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Error state */}
      {analysisErr && (
        <div className="mx-5 mb-4 rounded-xl border border-rose-400/20 bg-rose-400/8 px-3 py-2 text-xs text-rose-400">
          {analysisErr}
          <button type="button" onClick={() => { setAnalysisErr(null); void loadOrAnalyze(); }} className="ml-2 underline">Retry</button>
        </div>
      )}

      {/* Analysing spinner */}
      {analysing && !analysisErr && (
        <div className="border-t border-line/50 px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="relative flex h-10 w-10 shrink-0 items-center justify-center">
              <div className="absolute inset-0 rounded-full border border-blue/20 animate-pulse-ring" />
              <svg className="animate-spin text-blue" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-medium text-[#e8edf8]">Running pairwise analysis…</p>
              <p className="text-xs text-[#4a6080]">LangGraph LLM reasoning — usually 5-15 seconds</p>
            </div>
          </div>
        </div>
      )}

      {/* Analysis result (expanded) */}
      {analysis && expanded && <AnalysisPanel result={analysis} />}

      {/* Toggle analysis visibility once loaded */}
      {analysis && !analysing && (
        <button
          type="button"
          onClick={() => setExpanded(e => !e)}
          className="flex w-full items-center justify-center gap-1.5 border-t border-line/50 py-2.5 text-xs text-[#4a6080] hover:text-[#8fa3bf] transition-colors"
        >
          <svg className={`h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`}
            viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <path d="M2 4l4 4 4-4" />
          </svg>
          {expanded ? "Hide analysis" : "Show analysis"}
        </button>
      )}
    </article>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────
function EmptyState({ hasProfile, hasEmbeddings }: { hasProfile: boolean; hasEmbeddings: boolean }) {
  return (
    <div className="rounded-2xl border border-dashed border-line p-16 text-center">
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-panel text-2xl">✦</div>
      {!hasProfile ? (
        <>
          <p className="font-medium text-[#8fa3bf]">Profile required</p>
          <p className="mt-1.5 text-sm text-[#4a6080]">Create your profile first before finding matches.</p>
        </>
      ) : !hasEmbeddings ? (
        <>
          <p className="font-medium text-[#8fa3bf]">Embeddings not ready</p>
          <p className="mt-1.5 text-sm text-[#4a6080]">
            Complete onboarding and wait for your embeddings to generate — usually under a minute.
          </p>
        </>
      ) : (
        <>
          <p className="font-medium text-[#8fa3bf]">No candidates found</p>
          <p className="mt-1.5 text-sm text-[#4a6080]">
            No one matched your hard filters (age, distance, gender preference) right now.
          </p>
        </>
      )}
    </div>
  );
}

// ─── Stage explainer header ───────────────────────────────────────────────────
function StageExplainer({ stage }: { stage: 1 | 2 }) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className={`flex items-center gap-2 rounded-xl px-3 py-1.5 text-xs font-medium ${
        stage === 1
          ? "bg-blue/10 text-blue border border-blue/20"
          : "bg-line text-[#4a6080] border border-line"
      }`}>
        <span className={`h-1.5 w-1.5 rounded-full ${stage >= 1 ? "bg-blue" : "bg-[#4a6080]"}`} />
        Stage 1 · Candidate retrieval
      </div>
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="text-[#4a6080]">
        <path d="M5 12h14M12 5l7 7-7 7" />
      </svg>
      <div className={`flex items-center gap-2 rounded-xl px-3 py-1.5 text-xs font-medium ${
        stage === 2
          ? "bg-violet/10 text-violet border border-violet/20"
          : "bg-line text-[#4a6080] border border-line"
      }`}>
        <span className={`h-1.5 w-1.5 rounded-full ${stage >= 2 ? "bg-violet" : "bg-[#4a6080]"}`} />
        Stage 2 · Analyse deeper (on-demand)
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
type PageState = "idle" | "loading" | "done" | "error";

export function MatchesPage() {
  const { session } = useAuth();
  const userId = session!.userId;

  const [candidates, setCandidates] = useState<CandidateMatch[]>([]);
  const [pageState, setPageState]   = useState<PageState>("idle");
  const [error, setError]           = useState<string | null>(null);
  const [lastFetched, setLastFetched] = useState<Date | null>(null);

  async function findCandidates() {
    setPageState("loading");
    setError(null);
    try {
      const res = await matchApi.candidates(userId);
      setCandidates(res.candidates ?? []);
      setLastFetched(new Date());
      setPageState("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not retrieve candidates");
      setPageState("error");
    }
  }

  const isLoading = pageState === "loading";

  return (
    <section className="space-y-6 py-2">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-light text-[#e8edf8]">Matches</h1>
          <p className="mt-1.5 text-sm text-[#8fa3bf]">
            Find candidates with hard filters + vector recall, then analyse any of them deeper on-demand.
          </p>
          {lastFetched && (
            <p className="mt-1 text-xs text-[#4a6080]">
              Last updated {lastFetched.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
            </p>
          )}
        </div>

        <div className="flex items-center gap-3">
          {candidates.length > 0 && (
            <span className="text-xs text-[#4a6080]">
              {candidates.length} candidate{candidates.length !== 1 ? "s" : ""}
            </span>
          )}
          <button
            type="button"
            onClick={findCandidates}
            disabled={isLoading}
            className="rounded-xl bg-blue px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-blue/20 hover:bg-blue-dim disabled:opacity-50 transition-all"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                </svg>
                Finding…
              </span>
            ) : candidates.length > 0 ? "Refresh candidates" : "Find matches"}
          </button>
        </div>
      </div>

      {/* Stage explainer */}
      <StageExplainer stage={pageState === "done" && candidates.length > 0 ? 1 : 1} />

      {/* How it works — only on idle */}
      {pageState === "idle" && (
        <div className="rounded-2xl border border-line bg-panel/50 p-6">
          <p className="mb-4 text-xs font-medium uppercase tracking-widest text-[#4a6080]">How it works</p>
          <div className="grid gap-5 sm:grid-cols-2">
            <div className="flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-blue/10 text-xs font-semibold text-blue">1</div>
              <div>
                <p className="text-sm font-medium text-[#e8edf8]">Find candidates <span className="text-[10px] font-normal text-[#4a6080] ml-1">~5-15ms</span></p>
                <p className="mt-0.5 text-xs leading-relaxed text-[#4a6080]">
                  SQL hard filters (age, distance, gender) + bidirectional pgvector recall rank the best candidates instantly. No LLM used.
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-violet/10 text-xs font-semibold text-violet">2</div>
              <div>
                <p className="text-sm font-medium text-[#e8edf8]">Analyse deeper <span className="text-[10px] font-normal text-[#4a6080] ml-1">~5-15s</span></p>
                <p className="mt-0.5 text-xs leading-relaxed text-[#4a6080]">
                  For any candidate you're curious about, click "Analyse deeper" to run pairwise LLM reasoning across 4 dimensions with direct signal citations.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
          <div className="relative flex h-16 w-16 items-center justify-center">
            <div className="absolute inset-0 rounded-full border border-blue/20 animate-pulse-ring" />
            <svg className="animate-spin text-blue" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
          </div>
          <div>
            <p className="font-display text-xl font-light text-[#e8edf8]">Retrieving candidates</p>
            <p className="mt-1 text-sm text-[#8fa3bf]">Applying hard filters + pgvector recall…</p>
          </div>
        </div>
      )}

      {/* Error */}
      {pageState === "error" && error && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-400/20 bg-rose-400/8 px-4 py-3">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="mt-0.5 shrink-0 text-rose-400">
            <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <div>
            <p className="text-sm font-medium text-rose-400">{error}</p>
            <button type="button" onClick={findCandidates} className="mt-1 text-xs text-rose-400/70 hover:text-rose-400 underline">
              Try again
            </button>
          </div>
        </div>
      )}

      {/* Empty state */}
      {pageState === "done" && candidates.length === 0 && (
        <EmptyState hasProfile={true} hasEmbeddings={true} />
      )}

      {/* Candidate cards */}
      {pageState === "done" && candidates.length > 0 && (
        <div className="space-y-4">
          {/* Legend */}
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-[#4a6080]">
            <span>Sorted by combined bidirectional score</span>
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-[#d4a843]" />Forward = your wants vs their self
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-blue" />Reverse = their wants vs your self
            </span>
          </div>

          <div className="grid gap-4">
            {candidates.map((c, i) => (
              <CandidateCard key={c.user_id} candidate={c} index={i} userId={userId} />
            ))}
          </div>

          {/* Stage 2 callout */}
          <div className="rounded-2xl border border-violet/20 bg-violet/5 px-5 py-4">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-violet/15 text-[10px] font-semibold text-violet">2</span>
              <div>
                <p className="text-sm font-medium text-[#e8edf8]">Ready to go deeper?</p>
                <p className="mt-0.5 text-xs leading-relaxed text-[#4a6080]">
                  Click <span className="text-[#8fa3bf]">"Analyse deeper →"</span> on any candidate to run the full LangGraph pairwise reasoning — emotional needs, core values, lifestyle, conflict style, and dealbreaker checks.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
