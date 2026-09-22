export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseBody(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "error" in body) {
    const err = (body as { error: unknown }).error;
    if (typeof err === "string") return err;
  }
  if (body && typeof body === "object" && "message" in body) {
    const msg = (body as { message: unknown }).message;
    if (typeof msg === "string") return msg;
  }
  if (typeof body === "string" && body) return body;
  return fallback;
}

export async function api<T>(
  path: string,
  init: RequestInit = {},
  opts: { auth?: boolean } = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = document.cookie
    .split("; ")
    .find((row) => row.startsWith("belong_token="))
    ?.split("=")[1];
  const decoded = token ? decodeURIComponent(token) : null;
  if (opts.auth !== false && decoded) {
    headers.set("Authorization", `Bearer ${decoded}`);
  }

  const res = await fetch(path, { ...init, headers });
  const body = await parseBody(res);

  if (!res.ok) {
    throw new ApiError(res.status, errorMessage(body, res.statusText));
  }
  return body as T;
}

export type AuthResponse = {
  token: string;
  username: string;
  email: string;
};

export type Profile = {
  user_id: string;
  age: number;
  gender: string;
  orientation: string;
  latitude?: number;
  longitude?: number;
  relationship_goal: string;
  preferred_age_min?: number;
  preferred_age_max?: number;
  max_distance_km?: number;
  preferred_genders?: string[];
  profile?: Record<string, unknown>;
  extraction_version?: string;
  created_at?: string;
  updated_at?: string;
};

export type ProfileWrite = {
  user_id?: string;
  age: number;
  gender: string;
  orientation: string;
  latitude?: number;
  longitude?: number;
  relationship_goal: string;
  preferred_age_min?: number;
  preferred_age_max?: number;
  max_distance_km?: number;
  preferred_genders?: string[];
};

export type OnboardingSession = {
  conversation_id: string;
  question_id?: string;
  message: string;
};

export type ChatMessage = {
  role: string;
  content: string;
  question_id?: string | null;
  created_at?: string;
};

export type OnboardingState = {
  conversation_id: string;
  user_id: string;
  status: string;
  messages: ChatMessage[];
};

export type OnboardingReply = {
  conversation_id: string;
  status: "in_progress" | "completed";
  question_id?: string | null;
  message?: string;
};

export type DimensionResult = {
  verdict?: string;
  evidence_a?: string;
  evidence_b?: string;
};

export type MatchResultItem = {
  candidate_id: string;
  dimension_results?: Record<string, DimensionResult>;
  strong_alignments?: string[];
  potential_conflicts?: string[];
  dealbreaker_violations?: string[];
  uncertainties?: string[];
};

export type MatchJob = {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed" | string;
  matches?: MatchResultItem[];
};

export const authApi = {
  signup: (body: { username: string; email: string; password: string }) =>
    api<{ message: string }>("/auth/signup", { method: "POST", body: JSON.stringify(body) }, { auth: false }),
  login: (body: { email: string; password: string }) =>
    api<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify(body) }, { auth: false }),
};

export const profileApi = {
  get: async (userId: string): Promise<Profile | null> => {
    try {
      return await api<Profile>(`/profiles/${userId}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  },
  create: (body: ProfileWrite & { user_id: string }) =>
    api<Profile>("/profiles", { method: "POST", body: JSON.stringify(body) }),
  update: (userId: string, body: Partial<ProfileWrite>) =>
    api<Profile>(`/profiles/${userId}`, { method: "PATCH", body: JSON.stringify(body) }),
  triggerEmbedding: (userId: string) =>
    api<{ job_id: string; status: string }>(`/profiles/${userId}/embeddings`, { method: "POST" }),
};

export const onboardingApi = {
  start: (userId: string) =>
    api<OnboardingSession>("/onboarding/session", {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),
  send: (conversationId: string, message: string) =>
    api<OnboardingReply>("/onboarding/message", {
      method: "POST",
      body: JSON.stringify({ conversation_id: conversationId, message }),
    }),
  state: (conversationId: string) => api<OnboardingState>(`/onboarding/${conversationId}`),
};

export const matchApi = {
  createJob: (userId: string, limit = 5) =>
    api<{ job_id: string; status: string }>("/matches", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, limit }),
    }),
  job: (jobId: string) => api<MatchJob>(`/matches/jobs/${jobId}`),
  latest: (userId: string) =>
    api<{ user_id: string; matches: MatchResultItem[] }>(`/matches/${userId}`),
};
