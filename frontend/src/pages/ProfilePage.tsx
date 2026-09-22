import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ErrorText, Field, inputClass } from "../components/ui";
import { profileApi, type Profile, type ProfileWrite } from "../lib/api";
import { useAuth } from "../lib/auth";

const emptyForm: ProfileWrite = {
  age: 25,
  gender: "woman",
  orientation: "heterosexual",
  relationship_goal: "long-term",
  preferred_age_min: 22,
  preferred_age_max: 35,
  max_distance_km: 25,
  preferred_genders: ["man"],
};

// ─── Chip toggle (preferred genders) ─────────────────────────────────────────
const GENDER_OPTIONS = ["man", "woman", "nonbinary"];

function GenderChips({
  value,
  onChange,
}: {
  value: string[];
  onChange: (v: string[]) => void;
}) {
  function toggle(g: string) {
    onChange(
      value.includes(g) ? value.filter((x) => x !== g) : [...value, g],
    );
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
            className={`rounded-full border px-4 py-1.5 text-sm transition-colors ${
              active
                ? "border-gold bg-gold/15 text-gold"
                : "border-line text-zinc-500 hover:border-zinc-500 hover:text-zinc-300"
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
    <div className="flex items-center gap-2">
      <button
        type="button"
        disabled={busy || loading}
        onClick={locate}
        className="flex items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-xs text-zinc-400 hover:border-gold/40 hover:text-gold disabled:opacity-50"
      >
        <svg
          className={loading ? "animate-spin" : ""}
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
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
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <p className="mb-3 text-xs uppercase tracking-widest text-zinc-600">
        {title}
      </p>
      <div className="rounded-2xl border border-line bg-panel p-5">
        {children}
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
      <div className="flex h-40 items-center justify-center text-zinc-600 text-sm">
        Loading profile…
      </div>
    );
  }

  const hasSignals =
    existing?.profile && Object.keys(existing.profile).length > 0;

  return (
    <section className="mx-auto max-w-2xl space-y-8">
      {/* Header */}
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl">Your profile</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Hard filters used for retrieval. Your personality comes from the conversation.
          </p>
        </div>
        {existing && !hasSignals && (
          <button
            type="button"
            onClick={() => navigate("/onboarding")}
            className="shrink-0 rounded-full border border-gold/40 px-4 py-1.5 text-sm text-gold hover:bg-gold/10"
          >
            Start onboarding →
          </button>
        )}
      </div>

      <form onSubmit={onSubmit} className="space-y-6">
        {/* About you */}
        <Section title="About you">
          <div className="grid gap-4 sm:grid-cols-2">
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
        <Section title="Location">
          <div className="space-y-3">
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
                    set(
                      "latitude",
                      e.target.value === "" ? undefined : Number(e.target.value),
                    )
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
                    set(
                      "longitude",
                      e.target.value === "" ? undefined : Number(e.target.value),
                    )
                  }
                  placeholder="-122.4194"
                />
              </Field>
            </div>
            <Field label="Max distance (km)">
              <div className="flex items-center gap-3">
                <input
                  className={inputClass}
                  type="range"
                  min={5}
                  max={200}
                  step={5}
                  value={form.max_distance_km ?? 25}
                  onChange={(e) => set("max_distance_km", Number(e.target.value))}
                  style={{ accentColor: "var(--color-gold)" }}
                />
                <span className="w-16 shrink-0 text-right text-sm text-zinc-300">
                  {form.max_distance_km ?? 25} km
                </span>
              </div>
            </Field>
          </div>
        </Section>

        {/* Who you're looking for */}
        <Section title="Who you're looking for">
          <div className="space-y-4">
            <Field label="Preferred genders">
              <div className="mt-1">
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
                    set(
                      "preferred_age_min",
                      e.target.value === "" ? undefined : Number(e.target.value),
                    )
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
                    set(
                      "preferred_age_max",
                      e.target.value === "" ? undefined : Number(e.target.value),
                    )
                  }
                />
              </Field>
            </div>
          </div>
        </Section>

        {/* Actions */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={busy}
            className="rounded-full bg-gold px-6 py-2.5 text-sm font-medium text-ink hover:bg-[#e0b88a] disabled:opacity-50"
          >
            {busy ? "Saving…" : existing ? "Update profile" : "Create profile"}
          </button>
          {existing && (
            <button
              type="button"
              onClick={() => {
                void navigator.clipboard.writeText(userId);
                setNotice("User ID copied.");
              }}
              className="rounded-full border border-line px-4 py-2 text-sm text-zinc-400 hover:border-gold/40 hover:text-gold"
            >
              Copy user ID
            </button>
          )}
          <div className="flex-1 space-y-1">
            <ErrorText message={error} />
            {notice && <p className="text-sm text-emerald-400">{notice}</p>}
          </div>
        </div>
      </form>

      {/* Extracted signals */}
      {hasSignals && (
        <Section title="Extracted signals">
          <p className="mb-3 text-xs text-zinc-500">
            Built from your onboarding conversation.
          </p>
          <pre className="overflow-auto rounded-lg bg-ink p-4 text-xs leading-relaxed text-zinc-400">
            {JSON.stringify(existing!.profile, null, 2)}
          </pre>
        </Section>
      )}
    </section>
  );
}
