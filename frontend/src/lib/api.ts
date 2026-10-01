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
  const raw = document.cookie
    .split("; ")
    .find((row) => row.startsWith("belong_token="));
  const token = raw ? raw.substring("belong_token=".length) : null;
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

// ─── Auth ─────────────────────────────────────────────────────────────────────

export type AuthResponse = {
  token: string;
  username: string;
  email: string;
};

export type SignUpRequest = {
  username: string;
  email: string;
  password: string;
};

export type LoginRequest = {
  email: string;
  password: string;
};

// ─── Profile ──────────────────────────────────────────────────────────────────

export type Profile = {
  user_id: string;
  name?: string;
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
  name?: string;
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

export type EmbeddingStatus = {
  user_id: string;
  has_self_embedding: boolean;
  has_wants_embedding: boolean;
  embedding_source_text?: Record<string, unknown>;
  updated_at?: string;
};

// ─── Onboarding ───────────────────────────────────────────────────────────────

export type OnboardingSession = {
  conversation_id: string;
  question_id?: string;
  // backend returns first_question, message is a frontend alias
  first_question?: string;
  message?: string;
};

export type ChatMessage = {
  role: string;
  content: string;
  question_id?: string | null;
  created_at?: string;
  // DB rows may include these extra fields — ignored by UI
  id?: string;
  conversation_id?: string;
};

export type OnboardingState = {
  conversation_id: string;
  user_id: string;
  status: string;
  messages: ChatMessage[];
};

export type OnboardingReply = {
  conversation_id: string;
  // backend sends "active" | "completed", not "in_progress"
  status: "active" | "in_progress" | "completed";
  question_id?: string | null;
  // backend field is assistant_response
  assistant_response?: string;
  message?: string;
};

// ─── Matching ─────────────────────────────────────────────────────────────────

export type OverallVerdict =
  | "strong_alignment"
  | "partial_alignment"
  | "unclear"
  | "conflict";

export type DimensionResult = {
  verdict?: string;
  reasoning?: string;
  evidence_a?: string;
  evidence_b?: string;
  evidence_a_ids?: string[];
  evidence_b_ids?: string[];
};

// Stage 1 — candidate from retrieval engine
export type CandidateMatch = {
  user_id: string;
  name?: string | null;
  age?: number | null;
  gender?: string | null;
  orientation?: string | null;
  relationship_goal?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  distance_km?: number | null;
  profile?: Record<string, unknown>;
  cosine_distance?: number;
  cosine_similarity?: number;
  reverse_cosine_distance?: number | null;
  reverse_cosine_similarity?: number | null;
  combined_score?: number;
};

export type RetrievalListResponse = {
  user_id: string;
  total_candidates: number;
  candidates: CandidateMatch[];
};

export type RetrievalOptions = {
  candidate_pool_limit?: number;
  pre_rank_limit?: number;
  max_distance_km?: number;
  min_similarity_threshold?: number;
  bidirectional_weight?: number;
  require_mutual_age?: boolean;
  require_mutual_gender?: boolean;
  require_mutual_relationship_goal?: boolean;
};

export type AnalyzeMatchRequest = {
  candidate_user_id: string;
  user_id?: string | null;
};

// Stage 2 — full qualitative analysis result
export type MatchResultItem = {
  id?: string | null;
  match_id?: string | null;
  user_a_id?: string | null;
  user_b_id?: string;
  user_b_name?: string | null;
  // legacy field kept for compat
  candidate_id?: string;
  overall_verdict?: OverallVerdict;
  overall_reasoning?: string;
  dimension_results?: Record<string, DimensionResult>;
  complementary_alignments?: string[];
  shared_alignments?: string[];
  strong_alignments?: string[];
  potential_conflicts?: string[];
  dealbreaker_violations?: string[];
  uncertainties?: string[];
  created_at?: string | null;
  updated_at?: string | null;
};

export type JobAcceptedResponse = {
  job_id: string;
  user_id: string;
  type: string;
  status: string;
  created_at: string;
};

export type JobStatusResponse = {
  job_id: string;
  user_id: string;
  type: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled" | string;
  attempts?: number;
  error?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  result?: unknown;
};

export type MatchJob = {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed" | string;
  matches?: MatchResultItem[];
};

export type MatchesListResponse = {
  user_id: string;
  total_matches?: number;
  matches: MatchResultItem[];
};

// ─── API clients ──────────────────────────────────────────────────────────────

export const authApi = {
  signup: (body: SignUpRequest) =>
    api<{ message: string }>(
      "/auth/signup",
      { method: "POST", body: JSON.stringify(body) },
      { auth: false },
    ),
  login: (body: LoginRequest) =>
    api<AuthResponse>(
      "/auth/login",
      { method: "POST", body: JSON.stringify(body) },
      { auth: false },
    ),
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
    api<Profile>(`/profiles/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  triggerEmbedding: (userId: string) =>
    api<JobAcceptedResponse>(`/profiles/${userId}/embeddings`, {
      method: "POST",
    }),
  getEmbeddingStatus: (userId: string) =>
    api<EmbeddingStatus>(`/profiles/${userId}/embeddings`),
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
  state: (conversationId: string) =>
    api<OnboardingState>(`/onboarding/${conversationId}`),
  // Fetch the latest conversation for a user — used when localStorage ID is missing
  latestForUser: (userId: string) =>
    api<OnboardingState>(`/onboarding/user/${userId}`),
};

export const matchApi = {
  // Stage 1 — fast candidate retrieval (no LLM, ~5-15ms)
  candidates: (userId: string, opts?: RetrievalOptions) => {
    const params = new URLSearchParams();
    if (opts?.candidate_pool_limit) params.set("candidate_pool_limit", String(opts.candidate_pool_limit));
    if (opts?.pre_rank_limit) params.set("pre_rank_limit", String(opts.pre_rank_limit));
    if (opts?.max_distance_km) params.set("max_distance_km", String(opts.max_distance_km));
    const qs = params.toString();
    return api<RetrievalListResponse>(`/matches/candidates/${userId}${qs ? `?${qs}` : ""}`);
  },

  // Stage 2 — on-demand LLM pairwise reasoning for a single candidate
  analyze: (candidateUserId: string, userId?: string) =>
    api<MatchResultItem>("/matches/analyze", {
      method: "POST",
      body: JSON.stringify({ candidate_user_id: candidateUserId, user_id: userId ?? null }),
    }),

  // Fetch existing analysis for a candidate pair (avoids re-running LLM)
  pairDetail: (candidateUserId: string) =>
    api<MatchResultItem>(`/matches/details/pair/${candidateUserId}`),

  // Get all persisted analyses for a user
  latest: (userId: string) => api<MatchesListResponse>(`/matches/${userId}`),

  // Get full detail by result ID
  detail: (resultId: string) => api<MatchResultItem>(`/matches/details/${resultId}`),

  // Legacy batch job endpoints (kept for compat)
  createJob: (userId: string, limit = 5) =>
    api<JobAcceptedResponse>("/matches", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, limit }),
    }),
  job: (jobId: string) => api<MatchJob>(`/matches/jobs/${jobId}`),
  jobResults: (jobId: string) => api<MatchesListResponse>(`/matches/jobs/${jobId}/results`),
};
