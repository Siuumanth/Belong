import { useEffect, useState, type FormEvent } from "react";
import { Button, ErrorText, Field, GhostButton, inputClass } from "../components/ui";
import { profileApi, type Profile, type ProfileWrite } from "../lib/api";
import { useAuth } from "../lib/auth";

const emptyForm: ProfileWrite = {
  age: 25,
  gender: "woman",
  orientation: "heterosexual",
  relationship_goal: "long-term",
  preferred_age_min: 24,
  preferred_age_max: 35,
  max_distance_km: 25,
  preferred_genders: ["man"],
};

export function ProfilePage() {
  const { session } = useAuth();
  const userId = session!.userId;
  const [existing, setExisting] = useState<Profile | null>(null);
  const [form, setForm] = useState<ProfileWrite>(emptyForm);
  const [preferred, setPreferred] = useState("man");
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
            preferred_genders: profile.preferred_genders,
          });
          setPreferred((profile.preferred_genders ?? []).join(", "));
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load profile");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [userId]);

  function update<K extends keyof ProfileWrite>(key: K, value: ProfileWrite[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    const payload: ProfileWrite = {
      ...form,
      preferred_genders: preferred
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };
    try {
      const saved = existing
        ? await profileApi.update(userId, payload)
        : await profileApi.create({ ...payload, user_id: userId });
      setExisting(saved);
      setNotice(existing ? "Profile updated." : "Profile created.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <p className="text-zinc-500">Loading profile…</p>;
  }

  return (
    <section className="space-y-6">
      <div>
        <h1 className="font-display text-3xl">Your filters</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Hard constraints for retrieval. Conversation extracts the rest.
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="grid gap-4 rounded-2xl border border-line bg-panel p-6 md:grid-cols-2"
      >
        <Field label="Age">
          <input
            className={inputClass}
            type="number"
            min={18}
            value={form.age}
            onChange={(e) => update("age", Number(e.target.value))}
            required
          />
        </Field>
        <Field label="Gender">
          <select className={inputClass} value={form.gender} onChange={(e) => update("gender", e.target.value)}>
            <option value="woman">woman</option>
            <option value="man">man</option>
            <option value="nonbinary">nonbinary</option>
          </select>
        </Field>
        <Field label="Orientation">
          <input className={inputClass} value={form.orientation} onChange={(e) => update("orientation", e.target.value)} />
        </Field>
        <Field label="Relationship goal">
          <select
            className={inputClass}
            value={form.relationship_goal}
            onChange={(e) => update("relationship_goal", e.target.value)}
          >
            <option value="long-term">long-term</option>
            <option value="short-term">short-term</option>
            <option value="unsure">unsure</option>
          </select>
        </Field>
        <Field label="Latitude">
          <input
            className={inputClass}
            type="number"
            step="any"
            value={form.latitude ?? ""}
            onChange={(e) => update("latitude", e.target.value === "" ? undefined : Number(e.target.value))}
          />
        </Field>
        <Field label="Longitude">
          <input
            className={inputClass}
            type="number"
            step="any"
            value={form.longitude ?? ""}
            onChange={(e) => update("longitude", e.target.value === "" ? undefined : Number(e.target.value))}
          />
        </Field>
        <Field label="Preferred age min">
          <input
            className={inputClass}
            type="number"
            value={form.preferred_age_min ?? ""}
            onChange={(e) =>
              update("preferred_age_min", e.target.value === "" ? undefined : Number(e.target.value))
            }
          />
        </Field>
        <Field label="Preferred age max">
          <input
            className={inputClass}
            type="number"
            value={form.preferred_age_max ?? ""}
            onChange={(e) =>
              update("preferred_age_max", e.target.value === "" ? undefined : Number(e.target.value))
            }
          />
        </Field>
        <Field label="Max distance (km)">
          <input
            className={inputClass}
            type="number"
            value={form.max_distance_km ?? ""}
            onChange={(e) =>
              update("max_distance_km", e.target.value === "" ? undefined : Number(e.target.value))
            }
          />
        </Field>
        <Field label="Preferred genders (comma-separated)">
          <input className={inputClass} value={preferred} onChange={(e) => setPreferred(e.target.value)} />
        </Field>
        <div className="md:col-span-2 flex items-center gap-3">
          <Button type="submit" disabled={busy}>
            {busy ? "Saving…" : existing ? "Update profile" : "Create profile"}
          </Button>
          {existing && (
            <GhostButton
              type="button"
              onClick={() => navigator.clipboard.writeText(userId)}
            >
              Copy user id
            </GhostButton>
          )}
        </div>
        <div className="md:col-span-2 space-y-1">
          <ErrorText message={error} />
          {notice && <p className="text-sm text-emerald-400">{notice}</p>}
        </div>
      </form>

      {existing?.profile && Object.keys(existing.profile).length > 0 && (
        <div className="rounded-2xl border border-line bg-panel p-6">
          <h2 className="font-display text-xl text-gold">Extracted signals</h2>
          <pre className="mt-3 overflow-auto text-xs text-zinc-400">
            {JSON.stringify(existing.profile, null, 2)}
          </pre>
        </div>
      )}
    </section>
  );
}
