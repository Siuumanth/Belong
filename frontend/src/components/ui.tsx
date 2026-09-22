import type { ButtonHTMLAttributes, ReactNode } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

// ─── Nav links ────────────────────────────────────────────────────────────────
const links = [
  { to: "/profile",    label: "Profile"     },
  { to: "/onboarding", label: "Onboarding"  },
  { to: "/matches",    label: "Matches"     },
];

// ─── Layout ───────────────────────────────────────────────────────────────────
export function Layout() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-ink text-[#e8edf8]">
      <header className="sticky top-0 z-20 border-b border-line bg-panel/90 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-5 py-3">

          {/* Logo — wordmark only */}
          <NavLink to="/profile" className="shrink-0">
            <img
              src="/belong-logo.png"
              alt="Belong"
              className="h-7 object-contain"
            />
          </NavLink>

          {/* Nav */}
          <nav className="flex items-center gap-1">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `rounded-full px-3 py-1.5 text-sm transition-colors ${
                    isActive
                      ? "bg-blue/15 text-blue"
                      : "text-slate-400 hover:text-slate-200"
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>

          {/* User / sign out */}
          <div className="flex items-center gap-3 text-sm shrink-0">
            <span className="hidden max-w-[120px] truncate text-xs text-slate-500 sm:inline">
              {session?.username || session?.email}
            </span>
            <button
              type="button"
              className="rounded-full border border-line px-3 py-1 text-xs text-slate-400 hover:border-blue/40 hover:text-blue transition-colors"
              onClick={() => { logout(); navigate("/login"); }}
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-5 py-8">
        <Outlet />
      </main>
    </div>
  );
}

// ─── Auth shell ───────────────────────────────────────────────────────────────
export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-ink px-4">
      <div className="mb-8 flex flex-col items-center gap-4">
        <img src="/belong-logo.png" alt="Belong" className="h-10 object-contain" />
      </div>
      <div className="w-full max-w-md rounded-2xl border border-line bg-panel p-8 shadow-[0_20px_80px_rgba(0,0,0,0.5)]">
        <h1 className="font-display text-2xl text-white">{title}</h1>
        <p className="mt-1.5 text-sm text-slate-400">{subtitle}</p>
        <div className="mt-7">{children}</div>
      </div>
    </div>
  );
}

// ─── Primitives ───────────────────────────────────────────────────────────────
export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs uppercase tracking-wide text-slate-500">{label}</span>
      {children}
    </label>
  );
}

export const inputClass =
  "w-full rounded-lg border border-line bg-ink px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-blue/50 transition-colors";

export function Button({ children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`w-full rounded-full bg-blue px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-dim disabled:opacity-50 transition-colors ${props.className ?? ""}`}
    >
      {children}
    </button>
  );
}

export function GhostButton({ children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`rounded-full border border-line px-4 py-2 text-sm text-slate-300 hover:border-blue/40 hover:text-blue disabled:opacity-50 transition-colors ${props.className ?? ""}`}
    >
      {children}
    </button>
  );
}

export function ErrorText({ message }: { message: string | null }) {
  if (!message) return null;
  return <p className="text-sm text-rose-400">{message}</p>;
}
