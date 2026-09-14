import { useEffect, useState } from "react";
import { Button, ErrorText } from "../components/ui";
import { matchApi, type MatchResultItem } from "../lib/api";
import { useAuth } from "../lib/auth";

function verdictTone(verdict: string | undefined) {
  const v = (verdict ?? "").toLowerCase().replace(/\s+/g, "_");
  if (v.includes("strong")) return "text-emerald-400";
  if (v.includes("conflict")) return "text-rose-400";
  if (v.includes("partial")) return "text-amber-300";
  return "text-zinc-400";
}

function MatchCard({ match }: { match: MatchResultItem }) {
  const dimensions = Object.entries(match.dimension_results ?? {});
  return (
    <article className="rounded-2xl border border-line bg-panel p-6">
      <p className="text-xs uppercase tracking-wide text-zinc-500">Candidate</p>
      <p className="mt-1 font-mono text-sm text-gold">{match.candidate_id}</p>

      {dimensions.length > 0 && (
        <ul className="mt-4 space-y-3">
          {dimensions.map(([name, result]) => (
            <li key={name} className="rounded-xl bg-ink p-3">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm capitalize text-zinc-200">{name.replaceAll("_", " ")}</span>
                <span className={`text-xs ${verdictTone(result.verdict)}`}>
                  {(result.verdict ?? "unclear").replaceAll("_", " ")}
                </span>
              </div>
              {(result.evidence_a || result.evidence_b) && (
                <div className="mt-2 space-y-1 text-xs text-zinc-500">
                  {result.evidence_a && <p>You: {result.evidence_a}</p>}
                  {result.evidence_b && <p>Them: {result.evidence_b}</p>}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      <TagList label="Alignments" items={match.strong_alignments} tone="text-emerald-400" />
      <TagList label="Conflicts" items={match.potential_conflicts} tone="text-rose-400" />
      <TagList label="Dealbreakers" items={match.dealbreaker_violations} tone="text-rose-300" />
      <TagList label="Uncertainties" items={match.uncertainties} tone="text-zinc-400" />
    </article>
  );
}

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
      <p className={`text-xs uppercase tracking-wide ${tone}`}>{label}</p>
      <ul className="mt-1 list-disc space-y-1 pl-4 text-sm text-zinc-400">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export function MatchesPage() {
  const { session } = useAuth();
  const userId = session!.userId;
  const [matches, setMatches] = useState<MatchResultItem[]>([]);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    matchApi
      .latest(userId)
      .then((res) => {
        if (!cancelled) setMatches(res.matches ?? []);
      })
      .catch(() => {
        /* no persisted matches yet */
      });
    return () => {
      cancelled = true;
    };
  }, [userId]);

  async function runMatch() {
    setBusy(true);
    setError(null);
    try {
      const accepted = await matchApi.createJob(userId, 5);
      setJobStatus(accepted.status);
      const jobId = accepted.job_id;
      for (let i = 0; i < 40; i += 1) {
        const job = await matchApi.job(jobId);
        setJobStatus(job.status);
        if (job.status === "completed") {
          setMatches(job.matches ?? []);
          break;
        }
        if (job.status === "failed") {
          setError("Matching job failed");
          break;
        }
        await new Promise((r) => setTimeout(r, 2000));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Matching failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl">Matches</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Hard filters, vector recall, then pairwise reasoning. No fake scores.
          </p>
        </div>
        <Button type="button" onClick={runMatch} disabled={busy}>
          {busy ? `Working… ${jobStatus ?? ""}` : "Find matches"}
        </Button>
      </div>
      <ErrorText message={error} />
      {matches.length === 0 && !busy && (
        <p className="rounded-2xl border border-dashed border-line p-8 text-zinc-500">
          No results yet. Finish profile + onboarding, then run a match job.
        </p>
      )}
      <div className="grid gap-4">
        {matches.map((match) => (
          <MatchCard key={match.candidate_id} match={match} />
        ))}
      </div>
    </section>
  );
}
