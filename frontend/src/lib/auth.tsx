import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { decodeJwt, userIdFromToken } from "./jwt";

type Session = {
  token: string;
  userId: string;
  username: string;
  email: string;
};

type AuthContextValue = {
  session: Session | null;
  loginWithToken: (token: string, extras?: { username?: string; email?: string }) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function sessionFromToken(token: string, extras?: { username?: string; email?: string }): Session {
  const claims = decodeJwt(token);
  return {
    token,
    userId: userIdFromToken(token),
    username: extras?.username ?? claims.username ?? "",
    email: extras?.email ?? claims.email ?? "",
  };
}

function loadSession(): Session | null {
  const token = localStorage.getItem("belong_token");
  if (!token) return null;
  try {
    const session = sessionFromToken(token);
    if (session.userId) return session;
  } catch {
    localStorage.removeItem("belong_token");
  }
  return null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(loadSession);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      loginWithToken: (token, extras) => {
        const next = sessionFromToken(token, extras);
        localStorage.setItem("belong_token", token);
        setSession(next);
      },
      logout: () => {
        localStorage.removeItem("belong_token");
        setSession(null);
      },
    }),
    [session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
