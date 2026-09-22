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

const COOKIE_NAME = "belong_token";

function setCookie(value: string, days = 30) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${COOKIE_NAME}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Strict`;
}

function getCookie(): string | null {
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${COOKIE_NAME}=`));
  if (!match) return null;
  return decodeURIComponent(match.split("=")[1]);
}

function deleteCookie() {
  document.cookie = `${COOKIE_NAME}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; SameSite=Strict`;
}

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
  const token = getCookie();
  if (!token) return null;
  try {
    const session = sessionFromToken(token);
    if (session.userId) return session;
  } catch {
    deleteCookie();
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
        setCookie(token);
        setSession(next);
      },
      logout: () => {
        deleteCookie();
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
