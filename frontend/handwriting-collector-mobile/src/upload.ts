import { Capacitor, CapacitorHttp } from "@capacitor/core";

export const UPLOAD_URL =
  (import.meta.env.VITE_UPLOAD_URL as string | undefined)?.trim() ||
  "http://82.157.132.139:8082/api/handwriting-sessions";

const UPLOAD_TOKEN = (import.meta.env.VITE_UPLOAD_TOKEN as string | undefined)?.trim() || "";

export type UploadResult =
  | { ok: true; storedAs: string | null }
  | { ok: false; message: string };

function readStoredAs(data: unknown): string | null {
  if (typeof data === "string") {
    try {
      const parsed = JSON.parse(data) as { storedAs?: unknown };
      return typeof parsed.storedAs === "string" ? parsed.storedAs : null;
    } catch {
      return null;
    }
  }
  if (data && typeof data === "object" && "storedAs" in data) {
    const value = (data as { storedAs?: unknown }).storedAs;
    return typeof value === "string" ? value : null;
  }
  return null;
}

/**
 * Upload one completed session JSON to the collection server.
 * The caller keeps the local copy regardless of the result.
 */
export async function uploadSession(filename: string, json: string): Promise<UploadResult> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json; charset=utf-8",
    "X-Filename": encodeURIComponent(filename),
  };
  if (UPLOAD_TOKEN) {
    headers["X-Upload-Token"] = UPLOAD_TOKEN;
  }

  try {
    if (Capacitor.isNativePlatform()) {
      const response = await CapacitorHttp.post({
        url: UPLOAD_URL,
        headers,
        data: json,
        connectTimeout: 12_000,
        readTimeout: 12_000,
      });
      if (response.status >= 200 && response.status < 300) {
        return { ok: true, storedAs: readStoredAs(response.data) };
      }
      return { ok: false, message: `HTTP ${response.status}` };
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 12_000);
    try {
      const response = await fetch(UPLOAD_URL, {
        method: "POST",
        headers,
        body: json,
        signal: controller.signal,
      });
      if (!response.ok) {
        return { ok: false, message: `HTTP ${response.status}` };
      }
      const data = await response.json().catch(() => null);
      return { ok: true, storedAs: readStoredAs(data) };
    } finally {
      window.clearTimeout(timeout);
    }
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return { ok: false, message: "请求超时" };
    }
    return { ok: false, message: "无法连接服务器" };
  }
}
