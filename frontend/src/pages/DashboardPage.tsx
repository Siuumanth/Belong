import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { profileApi, type Profile } from "../lib/api";
import { useAuth } from "../lib/auth";

// ─── Quick-action card ────────────────────────────────────────────────────────
function QuickCard({
  to,
  icon,
  title,
  subtitle,
  cta,
  done,
}: {
  to: string;
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  cta: string;
  done?: boolean;
}) {
  return (
    <Link
      to={to}
      className="card-hover group flex flex-col gap-4 rounded-2xl border border-line bg-panel p-6 transition-all"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue/10 text-blue">
          {icon}
        </div>
        {done && (
          <span className="flex items-center gap-1 rounded-full border border-emerald-400/30 bg-emerald-400/8 px-2.5 py-0.5 text-[10px] text-emerald-400">
            <span>✓</span> Done
          </span>
        )}
      </div>
      <div>
        <p className="font-semibold text-[#e8edf8]">{title}</p>
        <p className="mt-1 text-sm leading-relaxed text-[#8fa3bf]">{subtitle}</p>
      </div>
      <div className="mt-auto flex items-center gap-1.5 text-sm text-blue group-hover:gap-2.5 transition-all">
        {cta}
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path d="M5 12h14M12 5l7 7-7 7" />
        </svg>
      </div>
    </Link>
  );
}

// ─── Stat pill ────────────────────────────────────────────────────────────────
function StatPill({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-xl border border-line bg-panel px-5 py-3">
      <span className="text-lg font-semibold text-[#e8edf8]">{value}</span>
      <span className="text-xs text-[#4a6080]">{label}</span>
    </div>
  );
}

// ─── Pipeline step ────────────────────────────────────────────────────────────
function PipelineStep({
  label,
  active,
  done,
}: {
  label: string;
  active?: boolean;
  done?: boolean;
}) {
  return (
    <div className="flex flex-col items-center gap-1.5">
      <div
        className={`flex h-9 w-9 items-center justify-center rounded-full border text-xs transition-all ${
          done
            ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-400"
            : active
            ? "border-blue/50 bg-blue/15 text-blue"
            : "border-line text-[#4a6080]"
        }`}
      >
        {done ? "✓" : active ? "◎" : "·"}
      </div>
      <span className={`text-[10px] text-center leading-tight ${done ? "text-[#8fa3bf]" : active ? "text-[#e8edf8]" : "text-[#4a6080]"}`}>
        {label}
      </span>
    </div>
  );
}

function PipelineConnector({ done }: { done?: boolean }) {
  return (
    <div className={`h-px flex-1 transition-colors ${done ? "bg-emerald-400/30" : "bg-line"}`} />
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export function DashboardPage() {
  const { session } = useAuth();
  const userId = session!.userId;

  const [profile, setProfile] = useState<Profile | null | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    profileApi
      .get(userId)
      .then((p) => { if (!cancelled) setProfile(p); })
      .catch(() => { if (!cancelled) setProfile(null); });
    return () => { cancelled = true; };
  }, [userId]);

  const hasProfile = !!profile;
  const hasSignals = hasProfile && !!profile.profile && Object.keys(profile.profile).length > 0;

  const greeting = profile?.name
    ? `Hey, ${profile.name}`
    : session?.username
    ? `Hey, ${session.username}`
    : "Hey there";

  return (
    <div className="space-y-8 py-2">
      {/* Greeting */}
      <div>
        <h1 className="font-display text-3xl font-light text-[#e8edf8] lg:text-4xl">
          {greeting} <span className="text-gradient-blue">✦</span>
        </h1>
        <p className="mt-2 text-sm text-[#8fa3bf]">
          Here's where you are in your Belong journey.
        </p>
      </div>

      {/* Setup pipeline */}
      <div className="rounded-2xl border border-line bg-panel p-6">
        <p className="mb-5 text-xs font-medium uppercase tracking-widest text-[#4a6080]">Setup pipeline</p>
        <div className="flex items-center gap-0">
          <PipelineStep label="Create profile" done={hasProfile} active={!hasProfile} />
          <PipelineConnector done={hasProfile} />
          <PipelineStep label="Onboarding" done={hasSignals} active={hasProfile && !hasSignals} />
          <PipelineConnector done={hasSignals} />
          <PipelineStep label="Find matches" active={hasSignals} done={false} />
        </div>
        {!hasProfile && (
          <p className="mt-4 text-xs text-[#4a6080]">
            Start by filling out your profile — takes about a minute.
          </p>
        )}
        {hasProfile && !hasSignals && (
          <p className="mt-4 text-xs text-[#4a6080]">
            Profile done. Complete the onboarding conversation to unlock matching.
          </p>
        )}
        {hasSignals && (
          <p className="mt-4 text-xs text-emerald-400">
            All set — you can run a match any time.
          </p>
        )}
      </div>

      {/* Stats */}
      {hasProfile && (
        <div className="flex flex-wrap gap-3">
          <StatPill label="Age" value={profile!.age} />
          <StatPill label="Goal" value={profile!.relationship_goal} />
          <StatPill
            label="Max distance"
            value={profile!.max_distance_km ? `${profile!.max_distance_km} km` : "—"}
          />
          <StatPill
            label="Signals"
            value={hasSignals ? Object.keys(profile!.profile!).length : "0"}
          />
        </div>
      )}

      {/* Quick actions */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <QuickCard
          to="/profile"
          icon={
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
            </svg>
          }
          title="Profile"
          subtitle="Set your age, location, orientation, and preferences. These become hard filters."
          cta={hasProfile ? "Edit profile" : "Create profile"}
          done={hasProfile}
        />
        <QuickCard
          to="/onboarding"
          icon={
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          }
          title="Onboarding"
          subtitle="A short AI conversation across six topics that builds your compatibility signal profile."
          cta={hasSignals ? "Redo conversation" : "Start conversation"}
          done={hasSignals}
        />
        <QuickCard
          to="/matches"
          icon={
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
            </svg>
          }
          title="Matches"
          subtitle="Run the 3-stage pipeline: hard filters, vector recall, and pairwise LLM reasoning."
          cta="View matches"
        />
      </div>

      {/* How the pipeline works — inline reminder */}
      <div className="rounded-2xl border border-line bg-panel/50 px-6 py-5">
        <p className="mb-3 text-xs font-medium uppercase tracking-widest text-[#4a6080]">
          How matching works
        </p>
        <div className="grid gap-3 sm:grid-cols-3 text-sm">
          {[
            {
              step: "1",
              title: "Hard filters",
              body: "Age, distance, orientation, and goal — SQL-level exclusions before anything else runs.",
            },
            {
              step: "2",
              title: "Vector recall",
              body: "pgvector cosine similarity retrieves semantically compatible candidates from embedding space.",
            },
            {
              step: "3",
              title: "LLM reasoning",
              body: "Each pair is evaluated across dimensions — emotional needs, values, lifestyle, conflict style.",
            },
          ].map((s) => (
            <div key={s.step} className="flex gap-3">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue/10 text-[10px] font-semibold text-blue">
                {s.step}
              </span>
              <div>
                <p className="font-medium text-[#c8d8f0]">{s.title}</p>
                <p className="mt-0.5 text-xs leading-relaxed text-[#4a6080]">{s.body}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
