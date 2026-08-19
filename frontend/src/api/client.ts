export interface ApiLogEntry {
  id: number;
  method: string;
  path: string;
  status: number | null;
  ok: boolean;
  requestBody: unknown;
  responseBody: unknown;
  startedAt: string;
  durationMs: number;
}

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly body: unknown;

  constructor(status: number, detail: string, body: unknown) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.body = body;
  }
}

const MAX_LOG_ENTRIES = 200;

let credential: string | null = null;
let nextId = 1;
let entries: ApiLogEntry[] = [];
const listeners = new Set<(entries: ApiLogEntry[]) => void>();

export function setCredential(value: string | null): void {
  credential = value;
}

export function subscribeToLog(listener: (entries: ApiLogEntry[]) => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function readLog(): ApiLogEntry[] {
  return entries;
}

export function clearLog(): void {
  entries = [];
  listeners.forEach((listener) => listener(entries));
}

function record(entry: ApiLogEntry): void {
  entries = [entry, ...entries].slice(0, MAX_LOG_ENTRIES);
  listeners.forEach((listener) => listener(entries));
}

export interface RequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
  query?: Record<string, string | number | string[] | undefined>;
  anonymous?: boolean;
}

function buildPath(path: string, query: RequestOptions["query"]): string {
  if (!query) return path;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined) continue;
    if (Array.isArray(value)) value.forEach((item) => params.append(key, item));
    else params.append(key, String(value));
  }
  const serialized = params.toString();
  return serialized ? `${path}?${serialized}` : path;
}

function detailFrom(status: number, body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            const location = "loc" in item ? (item as { loc: unknown[] }).loc.slice(1).join(".") : "";
            return location ? `${location}: ${(item as { msg: string }).msg}` : (item as { msg: string }).msg;
          }
          return JSON.stringify(item);
        })
        .join("; ");
    }
  }
  return `Request failed with status ${status}.`;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const fullPath = buildPath(`/api/v1${path}`, options.query);
  const headers: Record<string, string> = { Accept: "application/json" };

  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (!options.anonymous && credential) headers.Authorization = `Bearer ${credential}`;

  const startedAt = new Date();
  const startedTicks = performance.now();

  let response: Response;
  try {
    response = await fetch(fullPath, {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch (cause) {
    record({
      id: nextId++,
      method,
      path: fullPath,
      status: null,
      ok: false,
      requestBody: options.body,
      responseBody: String(cause),
      startedAt: startedAt.toISOString(),
      durationMs: Math.round(performance.now() - startedTicks),
    });
    throw new ApiError(0, "The API is not reachable. Is the backend running?", null);
  }

  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  record({
    id: nextId++,
    method,
    path: fullPath,
    status: response.status,
    ok: response.ok,
    requestBody: options.body,
    responseBody: body,
    startedAt: startedAt.toISOString(),
    durationMs: Math.round(performance.now() - startedTicks),
  });

  if (!response.ok) throw new ApiError(response.status, detailFrom(response.status, body), body);
  return body as T;
}
