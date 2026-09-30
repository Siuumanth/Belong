import type { ButtonHTMLAttributes, ReactNode } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

// ─── Nav links ────────────────────────────────────────────────────────────────
const NAV_LINKS = [
  {
    to: "/dashboard",
    label: "Home",
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
    ),
  },
  {
    to: "/profile",
    label: "Profile",
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    ),
  },
  {
    to: "/onboarding",
    label: "Onboarding",
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
  {
    to: "/matches",
    label: "Matches",
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
      </svg>
    ),
  },
];

// ─── Layout ───────────────────────────────────────────────────────────────────
export function Layout() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-ink text-[#e8edf8]">
      {/* Top nav */}
      <header className="sticky top-0 z-20 border-b border-line glass">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3">
          {/* Logo */}
          <NavLink to="/" className="shrink-0">
            <img src="/belong-logo.png" alt="Belong" className="h-7 object-contain" />
          </NavLink>

          {/* Nav */}
          <nav className="flex items-center gap-0.5">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm transition-all ${
                    isActive
                      ? "bg-blue/12 text-blue"
                      : "text-[#8fa3bf] hover:bg-panel hover:text-[#e8edf8]"
                  }`
                }
              >
                <span className="opacity-70">{link.icon}</span>
                <span className="hidden sm:inline">{link.label}</span>
              </NavLink>
            ))}
          </nav>

          {/* User */}
          <div className="flex shrink-0 items-center gap-3 text-sm">
            <div className="hidden sm:flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue/15 text-[11px] font-semibold text-blue">
                {(session?.username || session?.email || "?")[0].toUpperCase()}
              </div>
              <span className="max-w-[100px] truncate text-xs text-[#4a6080]">
                {session?.username || session?.email}
              </span>
            </div>
            <button
              type="button"
              className="rounded-xl border border-line px-3 py-1.5 text-xs text-[#8fa3bf] hover:border-blue/30 hover:text-blue transition-colors"
              onClick={() => { logout(); navigate("/login"); }}
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-8">
        <Outlet />
      </main>
    </div>
  );
}

// ─── Public layout (for home page, no auth required) ─────────────────────────
export function PublicLayout() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-ink text-[#e8edf8]">
      <header className="sticky top-0 z-20 border-b border-line glass">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3.5">
          <NavLink to="/" className="shrink-0">
            <img src="/belong-logo.png" alt="Belong" className="h-7 object-contain" />
          </NavLink>

          <div className="flex items-center gap-2">
            {session ? (
              <>
                <NavLink
                  to="/dashboard"
                  className="rounded-xl bg-blue/10 px-4 py-1.5 text-sm text-blue hover:bg-blue/15 transition-colors"
                >
                  Dashboard
                </NavLink>
                <button
                  type="button"
                  className="rounded-xl border border-line px-3 py-1.5 text-xs text-[#8fa3bf] hover:border-blue/30 hover:text-blue transition-colors"
                  onClick={() => { logout(); navigate("/"); }}
                >
                  Sign out
                </button>
              </>
            ) : (
              <>
                <NavLink
                  to="/login"
                  className="rounded-xl px-4 py-1.5 text-sm text-[#8fa3bf] hover:text-[#e8edf8] transition-colors"
                >
                  Sign in
                </NavLink>
                <NavLink
                  to="/signup"
                  className="rounded-xl bg-blue px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-dim transition-colors"
                >
                  Get started
                </NavLink>
              </>
            )}
          </div>
        </div>
      </header>

      <main>
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
      <div className="mb-8">
        <img src="/belong-logo.png" alt="Belong" className="h-9 object-contain" />
      </div>
      <div className="w-full max-w-md rounded-2xl border border-line bg-panel p-8 shadow-[0_20px_80px_rgba(0,0,0,0.5)]">
        <h1 className="font-display text-2xl text-white">{title}</h1>
        <p className="mt-1.5 text-sm text-[#8fa3bf]">{subtitle}</p>
        <div className="mt-7">{children}</div>
      </div>
    </div>
  );
}

// ─── Primitives ───────────────────────────────────────────────────────────────
export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs uppercase tracking-wide text-[#4a6080]">{label}</span>
      {children}
    </label>
  );
}

export const inputClass =
  "w-full rounded-xl border border-line bg-ink px-3 py-2.5 text-sm text-[#e8edf8] outline-none placeholder:text-[#4a6080] focus:border-blue/50 focus:ring-1 focus:ring-blue/20 transition-all";

export function Button({ children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`w-full rounded-xl bg-blue px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-blue/20 hover:bg-blue-dim disabled:opacity-50 transition-all ${props.className ?? ""}`}
    >
      {children}
    </button>
  );
}

export function GhostButton({ children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`rounded-xl border border-line px-4 py-2 text-sm text-[#8fa3bf] hover:border-blue/40 hover:text-blue disabled:opacity-50 transition-colors ${props.className ?? ""}`}
    >
      {children}
    </button>
  );
}

export function ErrorText({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="flex items-center gap-2 rounded-xl border border-rose-400/20 bg-rose-400/8 px-3 py-2 text-sm text-rose-400">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      {message}
    </div>
  );
}
