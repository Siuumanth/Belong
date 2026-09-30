import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { profileApi, type Profile, type ProfileWrite } from "../lib/api";
import { useAuth } from "../lib/auth";
import { ErrorText, Field, inputClass } from "../components/ui";

const emptyForm: ProfileWrite = {
  name: "",
  age: 25,
  gender: "woman",
  orientation: "heterosexual",
  relationship_goal: "long-term",
  preferred_age_min: 22,
  preferred_age_max: 35,
  max_distance_km: 25,
  preferred_genders: ["man"],
};

// ─── Gender chips ─────────────────────────────────────────────────────────────
const GENDER_OPTIONS = ["man", "woman", "nonbinary"];

function GenderChips({
  value,
  onChange,
}: {
  value: string[];
  onChange: (v: string[]) => void;
}) {
  function toggle(g: string) {
    onChange(value.includes(g) ? value.filter((x) => x !== g) : [...value, g]);
  }
  return (
    <div className="flex flex-wrap gap-2">
      {GENDER_OPTIONS.map((g) => {
        const active = value.includes(g);
        return (
          <button
            key={g}
            type="button"
            onClick={() => toggle(g)}
            className={`rounded-full border px-4 py-1.5 text-sm capitalize transition-all ${
              active
                ? "border-blue bg-blue/15 text-blue shadow-sm shadow-blue/10"
                : "border-line text-[#8fa3bf] hover:border-blue/30 hover:text-[#e8edf8]"
            }`}
          >
            {g}
          </button>
        );
      })}
    </div>
  );
}

// ─── Geolocation button ───────────────────────────────────────────────────────
function GeoButton({
  onLocate,
  busy,
}: {
  onLocate: (lat: number, lng: number) => void;
  busy: boolean;
}) {
  const [loading, setLoading] = useState(false);
  const [denied, setDenied] = useState(false);

  function locate() {
    if (!navigator.geolocation) return;
    setLoading(true);
    setDenied(false);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLoading(false);
        onLocate(
          parseFloat(pos.coords.latitude.toFixed(5)),
          parseFloat(pos.coords.longitude.toFixed(5)),
        );
      },
      () => {
        setLoading(false);
        setDenied(true);
      },
    );
  }

  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        disabled={busy || loading}
        onClick={locate}
        className="flex items-center gap-2 rounded-xl border border-line px-4 py-2 text-xs text-[#8fa3bf] hover:border-blue/40 hover:text-blue disabled:opacity-50 transition-colors"
      >
        <svg
          className={loading ? "animate-spin" : ""}
          width="13"
          height="13"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4l3 3" />
        </svg>
        {loading ? "Locating…" : "Use my location"}
      </button>
      {denied && (
        <span className="text-xs text-rose-400">Location access denied</span>
      )}
    </div>
  );
}

// ─── Section wrapper ──────────────────────────────────────────────────────────
function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-line bg-panel overflow-hidden">
      <div className="border-b border-line px-6 py-4">
        <p className="text-sm font-semibold text-[#e8edf8]">{title}</p>
        {description && (
          <p className="mt-0.5 text-xs text-[#4a6080]">{description}</p>
        )}
      </div>
      <div className="p-6">{children}</div>
    </div>
  );
}

// ─── Profile completeness banner ──────────────────────────────────────────────
function CompletionBanner({
  hasProfile,
  hasSignals,
}: {
  hasProfile: boolean;
  hasSignals: boolean;
}) {
  const steps = [
    { done: hasProfile, label: "Profile created" },
    { done: hasSignals, label: "Onboarding completed" },
  ];
  const doneCount = steps.filter((s) => s.done).length;
  const pct = (doneCount / steps.length) * 100;

  return (
    <div className="rounded-2xl border border-line bg-panel p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-medium text-[#e8edf8]">Profile completeness</p>
        <span className="text-xs text-[#4a6080]">{doneCount}/{steps.length}</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-line">
        <div
          className="h-full rounded-full bg-blue transition-all duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-4 space-y-2">
        {steps.map((s) => (
          <div key={s.label} className="flex items-center gap-2.5">
            <div
              className={`flex h-5 w-5 items-center justify-center rounded-full border text-[10px] transition-colors ${
                s.done
                  ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-400"
                  : "border-line text-[#4a6080]"
              }`}
            >
              {s.done ? "✓" : "·"}
            </div>
            <span className={`text-xs ${s.done ? "text-[#8fa3bf]" : "text-[#4a6080]"}`}>
              {s.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export function ProfilePage() {
  const { session } = useAuth();
  const userId = session!.userId;
  const navigate = useNavigate();

  const [existing, setExisting] = useState<Profile | null>(null);
  const [form, setForm] = useState<ProfileWrite>(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    profileApi
      .get(userId)
      .then((profile) => {
        if (cancelled) return;
        setExisting(profile);
        if (profile) {
          setForm({
            name: profile.name ?? "",
            age: profile.age,
            gender: profile.gender,
            orientation: profile.orientation,
            latitude: profile.latitude,
            longitude: profile.longitude,
            relationship_goal: profile.relationship_goal,
            preferred_age_min: profile.preferred_age_min,
            preferred_age_max: profile.preferred_age_max,
            max_distance_km: profile.max_distance_km,
            preferred_genders: profile.preferred_genders ?? [],
          });
        }
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Failed to load profile");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [userId]);

  function set<K extends keyof ProfileWrite>(key: K, value: ProfileWrite[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const saved = existing
        ? await profileApi.update(userId, form)
        : await profileApi.create({ ...form, user_id: userId });
      setExisting(saved);
      setNotice(existing ? "Profile updated." : "Profile created.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-60 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-blue" />
          <span className="text-xs text-[#4a6080]">Loading profile…</span>
        </div>
      </div>
    );
  }

  const hasSignals = existing?.profile && Object.keys(existing.profile).length > 0;

  return (
    <div className="mx-auto max-w-2xl space-y-6 py-2">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-light text-[#e8edf8]">
            {existing?.name ? `Hi, ${existing.name}` : "Your profile"}
          </h1>
          <p className="mt-1.5 text-sm text-[#8fa3bf]">
            These filters shape who gets through before the AI takes over.
          </p>
        </div>
        {existing && !hasSignals && (
          <Link
            to="/onboarding"
            className="shrink-0 rounded-xl border border-blue/30 bg-blue/8 px-4 py-2 text-sm font-medium text-blue hover:bg-blue/15 transition-colors"
          >
            Start onboarding →
          </Link>
        )}
      </div>

      {/* Completion banner */}
      {existing && (
        <CompletionBanner hasProfile={!!existing} hasSignals={!!hasSignals} />
      )}

      <form onSubmit={onSubmit} className="space-y-5">
        {/* About you */}
        <Section title="About you" description="Basic identity used for matching filters">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Display name">
              <input
                className={inputClass}
                type="text"
                placeholder="Alice"
                value={form.name ?? ""}
                onChange={(e) => set("name", e.target.value)}
              />
            </Field>
            <Field label="Age">
              <input
                className={inputClass}
                type="number"
                min={18}
                max={99}
                value={form.age}
                onChange={(e) => set("age", Number(e.target.value))}
                required
              />
            </Field>
            <Field label="Gender">
              <select
                className={inputClass}
                value={form.gender}
                onChange={(e) => set("gender", e.target.value)}
              >
                <option value="woman">Woman</option>
                <option value="man">Man</option>
                <option value="nonbinary">Nonbinary</option>
              </select>
            </Field>
            <Field label="Orientation">
              <input
                className={inputClass}
                value={form.orientation}
                onChange={(e) => set("orientation", e.target.value)}
                placeholder="e.g. heterosexual, bisexual…"
              />
            </Field>
            <Field label="Relationship goal">
              <select
                className={inputClass}
                value={form.relationship_goal}
                onChange={(e) => set("relationship_goal", e.target.value)}
              >
                <option value="long-term">Long-term</option>
                <option value="short-term">Short-term</option>
                <option value="unsure">Not sure yet</option>
              </select>
            </Field>
          </div>
        </Section>

        {/* Location */}
        <Section title="Location" description="Used for distance-based hard filtering">
          <div className="space-y-4">
            <GeoButton
              busy={busy}
              onLocate={(lat, lng) => {
                set("latitude", lat);
                set("longitude", lng);
              }}
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Latitude">
                <input
                  className={inputClass}
                  type="number"
                  step="any"
                  value={form.latitude ?? ""}
                  onChange={(e) =>
                    set("latitude", e.target.value === "" ? undefined : Number(e.target.value))
                  }
                  placeholder="37.7749"
                />
              </Field>
              <Field label="Longitude">
                <input
                  className={inputClass}
                  type="number"
                  step="any"
                  value={form.longitude ?? ""}
                  onChange={(e) =>
                    set("longitude", e.target.value === "" ? undefined : Number(e.target.value))
                  }
                  placeholder="-122.4194"
                />
              </Field>
            </div>
            <Field label={`Max distance — ${form.max_distance_km ?? 25} km`}>
              <input
                className="w-full accent-blue cursor-pointer"
                type="range"
                min={5}
                max={200}
                step={5}
                value={form.max_distance_km ?? 25}
                onChange={(e) => set("max_distance_km", Number(e.target.value))}
              />
              <div className="mt-1 flex justify-between text-[10px] text-[#4a6080]">
                <span>5 km</span>
                <span>200 km</span>
              </div>
            </Field>
          </div>
        </Section>

        {/* Who you're looking for */}
        <Section title="Who you're looking for" description="Hard filter applied before any AI stage">
          <div className="space-y-5">
            <Field label="Preferred genders">
              <div className="mt-2">
                <GenderChips
                  value={form.preferred_genders ?? []}
                  onChange={(v) => set("preferred_genders", v)}
                />
              </div>
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Age min">
                <input
                  className={inputClass}
                  type="number"
                  min={18}
                  value={form.preferred_age_min ?? ""}
                  onChange={(e) =>
                    set("preferred_age_min", e.target.value === "" ? undefined : Number(e.target.value))
                  }
                />
              </Field>
              <Field label="Age max">
                <input
                  className={inputClass}
                  type="number"
                  min={18}
                  value={form.preferred_age_max ?? ""}
                  onChange={(e) =>
                    set("preferred_age_max", e.target.value === "" ? undefined : Number(e.target.value))
                  }
                />
              </Field>
            </div>
          </div>
        </Section>

        {/* Actions */}
        <div className="flex flex-wrap items-center gap-3 pt-1">
          <button
            type="submit"
            disabled={busy}
            className="rounded-xl bg-blue px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue/20 hover:bg-blue-dim disabled:opacity-50 transition-all"
          >
            {busy ? "Saving…" : existing ? "Update profile" : "Create profile"}
          </button>
          {existing && (
            <button
              type="button"
              onClick={() => {
                void navigator.clipboard.writeText(userId);
                setNotice("User ID copied to clipboard.");
              }}
              className="rounded-xl border border-line px-4 py-2.5 text-sm text-[#8fa3bf] hover:border-blue/30 hover:text-blue transition-colors"
            >
              Copy user ID
            </button>
          )}
          <div className="flex-1">
            <ErrorText message={error} />
            {notice && <p className="text-sm text-emerald-400">{notice}</p>}
          </div>
        </div>
      </form>

      {/* Extracted signals */}
      {hasSignals && (
        <Section title="Extracted signals" description="Built from your onboarding conversation — read-only">
          <pre className="overflow-auto rounded-xl bg-ink p-4 text-xs leading-relaxed text-[#8fa3bf]">
            {JSON.stringify(existing!.profile, null, 2)}
          </pre>
          <div className="mt-4 flex gap-3">
            <button
              type="button"
              onClick={() => navigate("/onboarding")}
              className="rounded-xl border border-line px-4 py-2 text-xs text-[#8fa3bf] hover:border-blue/30 hover:text-blue transition-colors"
            >
              Redo onboarding
            </button>
            <button
              type="button"
              onClick={() => {
                profileApi.triggerEmbedding(userId).then(() => setNotice("Embedding job enqueued.")).catch(() => setError("Failed to enqueue embedding job."));
              }}
              className="rounded-xl border border-line px-4 py-2 text-xs text-[#8fa3bf] hover:border-blue/30 hover:text-blue transition-colors"
            >
              Regenerate embeddings
            </button>
          </div>
        </Section>
      )}
    </div>
  );
}
