export type JwtClaims = {
  user_id?: string;
  userId?: string;
  sub?: string;
  id?: string;
  username?: string;
  email?: string;
  exp?: number;
};

export function decodeJwt(token: string): JwtClaims {
  const parts = token.split(".");
  if (parts.length < 2) {
    throw new Error("Invalid token");
  }
  const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
  const padded = payload.padEnd(payload.length + ((4 - (payload.length % 4)) % 4), "=");
  return JSON.parse(atob(padded)) as JwtClaims;
}

export function userIdFromToken(token: string): string {
  const claims = decodeJwt(token);
  const id = claims.user_id ?? claims.userId ?? claims.sub ?? claims.id;
  if (!id) {
    throw new Error("Token does not contain a user id");
  }
  return String(id);
}
