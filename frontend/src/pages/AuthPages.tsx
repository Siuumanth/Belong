import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "../lib/api";
import { useAuth } from "../lib/auth";

// ─── Shared primitives ────────────────────────────────────────────────────────
const inputClass =
  "w-full rounded-xl border border-line bg-ink px-4 py-3 text-sm text-[#e8edf8] outline-none placeholder:text-[#4a6080] focus:border-blue/50 focus:ring-1 focus:ring-blue/20 transition-all";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-2">
      <span className="text-xs font-medium uppercase tracking-widest text-[#4a6080]">{label}</span>
      {children}
    </label>
  );
}

function SubmitButton({ busy, children }: { busy: boolean; children: React.ReactNode }) {
  return (
    <button
      type="submit"
      disabled={busy}
      className="w-full rounded-xl bg-blue px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue/20 hover:bg-blue-dim hover:shadow-blue/30 disabled:opacity-50 transition-all"
    >
      {children}
    </button>
  );
}

// ─── Auth shell ───────────────────────────────────────────────────────────────
function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-ink px-4 py-12">
      {/* Background glow */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-blue/8 blur-3xl" />
        <div className="absolute bottom-0 right-1/4 h-64 w-64 rounded-full bg-violet/8 blur-3xl" />
      </div>

      {/* Logo */}
      <Link to="/" className="relative mb-8 block">
        <img src="/belong-logo.png" alt="Belong" className="h-9 object-contain" />
      </Link>

      <div className="relative w-full max-w-md">
        {/* Card */}
        <div className="rounded-3xl border border-line bg-panel p-8 shadow-[0_24px_80px_rgba(0,0,0,0.5)] lg:p-10">
          <div className="mb-7">
            <h1 className="font-display text-2xl font-light text-[#e8edf8]">{title}</h1>
            <p className="mt-1.5 text-sm text-[#8fa3bf]">{subtitle}</p>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}

// ─── Login ────────────────────────────────────────────────────────────────────
export function LoginPage() {
  const { loginWithToken } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await authApi.login({ email, password });
      loginWithToken(res.token, { username: res.username, email: res.email });
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title="Welcome back" subtitle="Sign in to continue finding your people.">
      <form className="space-y-5" onSubmit={onSubmit}>
        <Field label="Email">
          <input
            className={inputClass}
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </Field>
        <Field label="Password">
          <input
            className={inputClass}
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </Field>

        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-rose-400/20 bg-rose-400/8 px-4 py-3 text-sm text-rose-400">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            {error}
          </div>
        )}

        <SubmitButton busy={busy}>{busy ? "Signing in…" : "Sign in"}</SubmitButton>
      </form>

      <div className="mt-6 flex items-center gap-3">
        <div className="h-px flex-1 bg-line" />
        <span className="text-xs text-[#4a6080]">or</span>
        <div className="h-px flex-1 bg-line" />
      </div>

      <p className="mt-5 text-center text-sm text-[#8fa3bf]">
        New here?{" "}
        <Link className="font-medium text-blue hover:underline" to="/signup">
          Create an account
        </Link>
      </p>
    </AuthShell>
  );
}

// ─── Signup ───────────────────────────────────────────────────────────────────
export function SignupPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await authApi.signup({ username, email, password });
      navigate("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title="Join Belong" subtitle="A few details, then we learn who you really are.">
      <form className="space-y-5" onSubmit={onSubmit}>
        <Field label="Username">
          <input
            className={inputClass}
            type="text"
            autoComplete="username"
            placeholder="alex_rivers"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </Field>
        <Field label="Email">
          <input
            className={inputClass}
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </Field>
        <Field label="Password">
          <input
            className={inputClass}
            type="password"
            autoComplete="new-password"
            placeholder="At least 8 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </Field>

        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-rose-400/20 bg-rose-400/8 px-4 py-3 text-sm text-rose-400">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            {error}
          </div>
        )}

        <SubmitButton busy={busy}>{busy ? "Creating account…" : "Create account"}</SubmitButton>
      </form>

      <p className="mt-6 text-center text-sm text-[#8fa3bf]">
        Already have an account?{" "}
        <Link className="font-medium text-blue hover:underline" to="/login">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
