import { Link } from "react-router-dom";
import { useAuth } from "../lib/auth";

// ─── Icon components ──────────────────────────────────────────────────────────
function IconFilter() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
    </svg>
  );
}
function IconVector() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12" />
    </svg>
  );
}
function IconBrain() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.5 2a2.5 2.5 0 0 1 5 0v1a2.5 2.5 0 0 1-5 0V2z" />
      <path d="M4 7.5A2.5 2.5 0 0 1 6.5 5H8a1 1 0 0 0 1-1V2.5" />
      <path d="M20 7.5A2.5 2.5 0 0 0 17.5 5H16a1 1 0 0 1-1-1V2.5" />
      <path d="M4 7.5v1A2.5 2.5 0 0 0 6.5 11h1" />
      <path d="M20 7.5v1A2.5 2.5 0 0 1 17.5 11h-1" />
      <path d="M4 14a2.5 2.5 0 0 0 2.5 2.5H9" />
      <path d="M20 14a2.5 2.5 0 0 1-2.5 2.5H15" />
      <path d="M9 16.5V18a3 3 0 0 0 6 0v-1.5" />
      <path d="M9 11h6" />
    </svg>
  );
}
function IconChat() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}
function IconStar() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  );
}

// ─── Step number badge ────────────────────────────────────────────────────────
function StepBadge({ n }: { n: number }) {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-blue/30 bg-blue/10 text-xs font-semibold text-blue">
      {n}
    </div>
  );
}

// ─── Feature card ─────────────────────────────────────────────────────────────
function FeatureCard({
  icon,
  title,
  body,
  accent,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  accent: string;
}) {
  return (
    <div className={`card-hover rounded-2xl border border-line bg-panel p-6 flex flex-col gap-4`}>
      <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${accent}`}>
        {icon}
      </div>
      <div>
        <h3 className="font-semibold text-[#e8edf8]">{title}</h3>
        <p className="mt-1.5 text-sm leading-relaxed text-[#8fa3bf]">{body}</p>
      </div>
    </div>
  );
}

// ─── Stat pill ────────────────────────────────────────────────────────────────
function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="flex flex-col items-center gap-1 px-6">
      <span className="font-display text-3xl font-light text-gradient-blue">{value}</span>
      <span className="text-xs uppercase tracking-wide text-[#4a6080]">{label}</span>
    </div>
  );
}

// ─── How it works step ────────────────────────────────────────────────────────
function HowStep({
  n,
  title,
  body,
}: {
  n: number;
  title: string;
  body: string;
}) {
  return (
    <div className="flex gap-4">
      <StepBadge n={n} />
      <div className="pt-0.5">
        <p className="font-medium text-[#e8edf8]">{title}</p>
        <p className="mt-1 text-sm leading-relaxed text-[#8fa3bf]">{body}</p>
      </div>
    </div>
  );
}

// ─── Floating match preview card ──────────────────────────────────────────────
function PreviewMatchCard({
  initials,
  verdict,
  dims,
  delay,
}: {
  initials: string;
  verdict: string;
  dims: { name: string; color: string }[];
  delay: string;
}) {
  return (
    <div
      className="animate-float-up rounded-2xl border border-line bg-panel/80 glass p-4 w-56 shadow-xl"
      style={{ animationDelay: delay }}
    >
      <div className="flex items-center gap-3 mb-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue/20 text-sm font-semibold text-blue">
          {initials}
        </div>
        <div>
          <p className="text-xs font-medium text-[#e8edf8]">{verdict}</p>
          <p className="text-[10px] text-[#4a6080]">Compatibility match</p>
        </div>
      </div>
      <div className="space-y-1.5">
        {dims.map((d) => (
          <div key={d.name} className="flex items-center gap-2">
            <span className={`h-1.5 w-1.5 rounded-full ${d.color} shrink-0`} />
            <span className="text-[11px] text-[#8fa3bf] capitalize">{d.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export function HomePage() {
  const { session } = useAuth();
  const ctaTo = session ? "/dashboard" : "/signup";
  const ctaLabel = session ? "Go to dashboard" : "Get started — it's free";

  return (
    <div className="flex flex-col">
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        {/* Background glow */}
        <div className="gradient-hero pointer-events-none absolute inset-0" />
        <div className="pointer-events-none absolute -top-32 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-blue/10 blur-3xl" />

        <div className="relative mx-auto max-w-6xl px-5 py-24 lg:py-36">
          <div className="flex flex-col items-center gap-12 lg:flex-row lg:items-center lg:gap-16">
            {/* Left copy */}
            <div className="flex-1 text-center lg:text-left">
              <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-blue/25 bg-blue/8 px-4 py-1.5 text-xs text-blue">
                <span className="h-1.5 w-1.5 rounded-full bg-blue animate-pulse" />
                AI-powered compatibility matching
              </div>

              <h1 className="font-display text-5xl font-light leading-tight lg:text-6xl xl:text-7xl">
                <span className="text-gradient">Find people who</span>
                <br />
                <span className="text-gradient-blue italic">actually fit</span>
              </h1>

              <p className="mt-6 max-w-lg text-base leading-relaxed text-[#8fa3bf] lg:text-lg">
                Belong uses a short AI conversation to understand who you really are —
                then matches you using hard filters, vector recall, and pairwise LLM reasoning.
                No star ratings. No swipe queues.
              </p>

              <div className="mt-8 flex flex-wrap justify-center gap-3 lg:justify-start">
                <Link
                  to={ctaTo}
                  className="rounded-full bg-blue px-7 py-3 text-sm font-semibold text-white shadow-lg shadow-blue/25 hover:bg-blue-dim transition-all hover:shadow-blue/40 hover:-translate-y-0.5"
                >
                  {ctaLabel}
                </Link>
                {!session && (
                  <Link
                    to="/login"
                    className="rounded-full border border-line px-7 py-3 text-sm text-[#8fa3bf] hover:border-blue/40 hover:text-[#e8edf8] transition-colors"
                  >
                    Sign in
                  </Link>
                )}
              </div>
            </div>

            {/* Right — floating cards */}
            <div className="relative flex-1 flex justify-center lg:justify-end">
              <div className="relative h-72 w-80 lg:h-80 lg:w-96">
                <div className="absolute top-0 right-0">
                  <PreviewMatchCard
                    initials="AK"
                    verdict="Strong alignment"
                    dims={[
                      { name: "emotional needs", color: "bg-[#d4a843]" },
                      { name: "core values", color: "bg-[#d4a843]" },
                      { name: "lifestyle", color: "bg-[#d4a843]" },
                    ]}
                    delay="0s"
                  />
                </div>
                <div className="absolute bottom-4 left-0">
                  <PreviewMatchCard
                    initials="MR"
                    verdict="Partial alignment"
                    dims={[
                      { name: "conflict style", color: "bg-[#fb923c]" },
                      { name: "lifestyle", color: "bg-[#d4a843]" },
                      { name: "core values", color: "bg-[#fb923c]" },
                    ]}
                    delay="0.15s"
                  />
                </div>
                {/* Decorative blur blob */}
                <div className="pointer-events-none absolute inset-0 -z-10 m-auto h-48 w-48 rounded-full bg-violet/20 blur-3xl" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Stats bar ────────────────────────────────────────────────────── */}
      <section className="border-y border-line bg-panel/50">
        <div className="mx-auto max-w-6xl px-5 py-8">
          <div className="flex flex-wrap items-center justify-center divide-x divide-line">
            <Stat value="3-stage" label="Matching pipeline" />
            <Stat value="6 topics" label="Conversation depth" />
            <Stat value="Zero" label="Fake scores" />
            <Stat value="100%" label="Signal-based" />
          </div>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────────── */}
      <section className="mx-auto w-full max-w-6xl px-5 py-20 lg:py-28">
        <div className="flex flex-col gap-16 lg:flex-row lg:gap-20">
          <div className="lg:w-80 shrink-0">
            <p className="text-xs uppercase tracking-widest text-[#4a6080]">How it works</p>
            <h2 className="mt-3 font-display text-3xl font-light text-[#e8edf8] lg:text-4xl">
              Three steps to a real connection
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-[#8fa3bf]">
              No quizzes. No endless swiping. Belong learns who you are through
              natural conversation, then does the heavy lifting.
            </p>
            <Link
              to={ctaTo}
              className="mt-6 inline-flex items-center gap-1.5 text-sm text-blue hover:underline"
            >
              Start now →
            </Link>
          </div>

          <div className="flex-1 space-y-8">
            <HowStep
              n={1}
              title="Set your profile & filters"
              body="Age, location, orientation, and what you're looking for. These become hard filters so you only see people who match on the basics."
            />
            <div className="h-px bg-line" />
            <HowStep
              n={2}
              title="Have a conversation with Belong"
              body="A short, adaptive dialogue — six core topics, no checklists. Your answers are turned into rich compatibility signals by our LLM extraction pipeline."
            />
            <div className="h-px bg-line" />
            <HowStep
              n={3}
              title="Receive reasoned matches"
              body="Our 3-stage pipeline runs hard filters, pgvector semantic recall, and pairwise LLM reasoning. Every match comes with dimension verdicts and a written reasoning summary."
            />
          </div>
        </div>
      </section>

      {/* ── Feature grid ─────────────────────────────────────────────────── */}
      <section className="border-t border-line bg-panel/30">
        <div className="mx-auto max-w-6xl px-5 py-20 lg:py-28">
          <div className="mb-12 text-center">
            <p className="text-xs uppercase tracking-widest text-[#4a6080]">The tech</p>
            <h2 className="mt-3 font-display text-3xl font-light text-[#e8edf8]">
              Built differently
            </h2>
          </div>

          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            <FeatureCard
              icon={<IconChat />}
              title="Conversational onboarding"
              body="LangGraph-powered dialogue that adapts to your answers and surfaces contradiction-free signals."
              accent="bg-blue/10 text-blue"
            />
            <FeatureCard
              icon={<IconFilter />}
              title="Hard filter stage"
              body="SQL-level exclusions ensure non-negotiables like age range, location, and orientation are respected before anything else runs."
              accent="bg-teal/10 text-teal"
            />
            <FeatureCard
              icon={<IconVector />}
              title="Vector recall"
              body="pgvector cosine similarity retrieves semantically compatible candidates from your embedding space."
              accent="bg-violet/10 text-violet"
            />
            <FeatureCard
              icon={<IconBrain />}
              title="Pairwise LLM reasoning"
              body="Each candidate pair is evaluated across dimensions — emotional needs, values, lifestyle, conflict style — with written verdicts."
              accent="bg-blue/10 text-blue"
            />
          </div>
        </div>
      </section>

      {/* ── Verdict legend ────────────────────────────────────────────────── */}
      <section className="mx-auto w-full max-w-6xl px-5 py-20 lg:py-24">
        <div className="rounded-3xl border border-line bg-panel p-8 lg:p-12">
          <div className="mb-8 flex items-center gap-3">
            <IconStar />
            <h2 className="font-display text-2xl font-light text-[#e8edf8]">
              What the verdicts mean
            </h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                dot: "bg-[#d4a843]",
                verdict: "Strong alignment",
                desc: "Both people's needs and values are clearly reciprocated.",
              },
              {
                dot: "bg-[#fb923c]",
                verdict: "Partial alignment",
                desc: "Some strong signals, some areas worth exploring together.",
              },
              {
                dot: "bg-rose-400",
                verdict: "Conflict",
                desc: "Signals suggest meaningful incompatibility in this dimension.",
              },
              {
                dot: "bg-zinc-500",
                verdict: "Unclear",
                desc: "Not enough signal to draw a confident conclusion yet.",
              },
            ].map((v) => (
              <div key={v.verdict} className="flex gap-3">
                <span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${v.dot}`} />
                <div>
                  <p className="text-sm font-medium text-[#e8edf8]">{v.verdict}</p>
                  <p className="mt-1 text-xs leading-relaxed text-[#8fa3bf]">{v.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA footer ───────────────────────────────────────────────────── */}
      <section className="border-t border-line">
        <div className="mx-auto max-w-6xl px-5 py-20 text-center lg:py-28">
          <h2 className="font-display text-4xl font-light lg:text-5xl">
            <span className="shimmer-text">Ready to find your people?</span>
          </h2>
          <p className="mx-auto mt-4 max-w-md text-sm leading-relaxed text-[#8fa3bf]">
            Takes about 5 minutes. No subscription required to explore.
          </p>
          <Link
            to={ctaTo}
            className="mt-8 inline-flex items-center gap-2 rounded-full bg-blue px-8 py-3.5 text-sm font-semibold text-white shadow-lg shadow-blue/25 hover:bg-blue-dim hover:shadow-blue/40 transition-all hover:-translate-y-0.5"
          >
            {ctaLabel}
          </Link>
        </div>
      </section>
    </div>
  );
}
