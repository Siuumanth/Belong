import type { ButtonHTMLAttributes, ReactNode } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

const links = [
  { to: "/profile", label: "Profile" },
  { to: "/onboarding", label: "Onboarding" },
  { to: "/matches", label: "Matches" },
];

export function Layout() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-ink text-[#f4efe8]">
      <header className="border-b border-line bg-panel/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-5 py-4">
          <div>
            <p className="font-display text-xl tracking-tight text-gold">Belong</p>
            <p className="text-xs text-zinc-500">Compatibility, not similarity</p>
          </div>
          <nav className="flex items-center gap-1">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `rounded-full px-3 py-1.5 text-sm ${
                    isActive ? "bg-gold/15 text-gold" : "text-zinc-400 hover:text-zinc-200"
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3 text-sm">
            <span className="hidden text-zinc-500 sm:inline">
              {session?.username || session?.email}
            </span>
            <button
              type="button"
              className="rounded-full border border-line px-3 py-1 text-zinc-400 hover:border-gold/40 hover:text-gold"
              onClick={() => {
                logout();
                navigate("/login");
              }}
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

export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs uppercase tracking-wide text-zinc-500">{label}</span>
      {children}
    </label>
  );
}

export const inputClass =
  "w-full rounded-lg border border-line bg-ink px-3 py-2 text-sm text-zinc-100 outline-none placeholder:text-zinc-600 focus:border-gold/50";

export function Button({
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`rounded-full bg-gold px-4 py-2 text-sm font-medium text-ink hover:bg-[#e0b88a] disabled:opacity-50 ${props.className ?? ""}`}
    >
      {children}
    </button>
  );
}

export function GhostButton({
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`rounded-full border border-line px-4 py-2 text-sm text-zinc-300 hover:border-gold/40 hover:text-gold disabled:opacity-50 ${props.className ?? ""}`}
    >
      {children}
    </button>
  );
}

export function ErrorText({ message }: { message: string | null }) {
  if (!message) return null;
  return <p className="text-sm text-rose-400">{message}</p>;
}
