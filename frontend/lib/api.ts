import type {
  DeleteJobResponse,
  DashboardResponse,
  EvaluationDetail,
  JobListResponse,
  JobSetupResponse,
  QuestionAnswer,
  ScreeningProfileDraft
} from "./types";

const API_BASE_URL_OVERRIDE_STORAGE_KEY = "resume-screening.api-base-url";
const DEFAULT_API_BASE_URL = normalizeApiBaseUrl(
  process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_DEFAULT_API_BASE_URL ?? null
);

function normalizeApiBaseUrl(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  if (!trimmed) {
    return null;
  }
  return trimmed.replace(/\/+$/, "");
}

export function getApiBaseUrlOverride(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return normalizeApiBaseUrl(window.localStorage.getItem(API_BASE_URL_OVERRIDE_STORAGE_KEY));
}

export function setApiBaseUrlOverride(value: string): string | null {
  if (typeof window === "undefined") {
    return normalizeApiBaseUrl(value);
  }
  const normalized = normalizeApiBaseUrl(value);
  if (!normalized) {
    window.localStorage.removeItem(API_BASE_URL_OVERRIDE_STORAGE_KEY);
    return null;
  }
  window.localStorage.setItem(API_BASE_URL_OVERRIDE_STORAGE_KEY, normalized);
  return normalized;
}

export function clearApiBaseUrlOverride(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(API_BASE_URL_OVERRIDE_STORAGE_KEY);
}

export function getApiBaseUrl(): string {
  return (
    getApiBaseUrlOverride() ??
    DEFAULT_API_BASE_URL ??
    (typeof window === "undefined" ? "http://localhost:8000" : window.location.origin)
  );
}

export function isStaticPagesHost(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return window.location.hostname.endsWith("github.io");
}

export function hasConfiguredApiBaseUrl(): boolean {
  return Boolean(getApiBaseUrlOverride() ?? DEFAULT_API_BASE_URL);
}

function makeSignal(timeoutMs = 120000): AbortSignal {
  return AbortSignal.timeout(timeoutMs);
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        detail = body.detail;
      }
    } catch {}
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, { cache: "no-store" });
  return parseJson<T>(response);
}

export async function listJobs(): Promise<JobListResponse> {
  return apiGet<JobListResponse>("/jobs");
}

export async function getJob(jobId: string): Promise<JobSetupResponse> {
  return apiGet<JobSetupResponse>(`/jobs/${jobId}`);
}

export async function deleteJob(jobId: string): Promise<DeleteJobResponse> {
  const response = await fetch(`${getApiBaseUrl()}/jobs/${jobId}`, {
    method: "DELETE"
  });
  return parseJson<DeleteJobResponse>(response);
}

export async function importJob(params: { jdText?: string; file?: File | null }): Promise<JobSetupResponse> {
  const formData = new FormData();
  if (params.jdText) {
    formData.append("jd_text", params.jdText);
  }
  if (params.file) {
    formData.append("file", params.file);
  }
  const response = await fetch(`${getApiBaseUrl()}/jobs/import-jd`, {
    method: "POST",
    body: formData,
    signal: makeSignal(120000),
  });
  const rawResult = await parseJson<Record<string, unknown>>(response);

  // Handle async background mode: {"status": "importing", "job_id": "..."}
  if (rawResult.status === "importing" && rawResult.job_id) {
    const jobId = rawResult.job_id as string;
    const maxAttempts = 60;
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise((resolve) => setTimeout(resolve, 3000));
      const pollResponse = await fetch(`${getApiBaseUrl()}/jobs/${jobId}/import-status`, {
        cache: "no-store",
        signal: makeSignal(10000),
      });
      const result = await parseJson<{ status: string; job_id?: string }>(pollResponse);
      if (result.status === "done" && result.job_id) {
        return getJob(result.job_id);
      }
      if (result.status === "failed") {
        throw new Error("岗位导入失败，请重试");
      }
    }
    throw new Error("岗位导入超时，请重试");
  }

  // Handle sync mode (legacy): {"job": {...}}
  return rawResult as unknown as JobSetupResponse;
}

export async function answerInterview(jobId: string, answers: QuestionAnswer[]): Promise<ScreeningProfileDraft> {
  const submitResponse = await fetch(`${getApiBaseUrl()}/jobs/${jobId}/interview/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers }),
    signal: makeSignal(120000),
  });
  const rawResult = await parseJson<Record<string, unknown>>(submitResponse);

  // Handle async background mode: {"status": "compiling", "job_id": "..."}
  if (rawResult.status === "compiling" && rawResult.job_id) {
    const maxAttempts = 60;
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise((resolve) => setTimeout(resolve, 3000));
      const pollResponse = await fetch(`${getApiBaseUrl()}/jobs/${jobId}/compile-status`, {
        cache: "no-store",
        signal: makeSignal(10000),
      });
      const result = await parseJson<{ status: string; draft?: ScreeningProfileDraft }>(pollResponse);
      if (result.status === "done" && result.draft) {
        return result.draft as ScreeningProfileDraft;
      }
      if (result.status !== "compiling") {
        throw new Error("岗位画像生成失败，请重试");
      }
    }
    throw new Error("岗位画像生成超时，请重试");
  }

  // Handle sync mode (legacy): direct ScreeningProfileDraft response
  return rawResult as unknown as ScreeningProfileDraft;
}

export async function freezeProfile(jobId: string, profile: ScreeningProfileDraft): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/jobs/${jobId}/freeze-profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile }),
    signal: makeSignal(120000),
  });
  await parseJson(response);
}

export async function uploadResumes(jobId: string, files: File[]): Promise<void> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const response = await fetch(`${getApiBaseUrl()}/jobs/${jobId}/resumes`, {
    method: "POST",
    body: formData,
    signal: makeSignal(120000),
  });
  await parseJson(response);
}

export async function getDashboard(jobId: string): Promise<DashboardResponse> {
  return apiGet<DashboardResponse>(`/jobs/${jobId}/dashboard`);
}

export async function getEvaluation(evaluationId: string): Promise<EvaluationDetail> {
  return apiGet<EvaluationDetail>(`/evaluations/${evaluationId}`);
}

export async function submitDecision(
  evaluationId: string,
  payload: { decision: string; reviewer_name?: string; comment?: string }
): Promise<EvaluationDetail> {
  const response = await fetch(`${getApiBaseUrl()}/evaluations/${evaluationId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return parseJson<EvaluationDetail>(response);
}
