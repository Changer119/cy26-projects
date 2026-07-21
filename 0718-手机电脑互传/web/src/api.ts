const tokenStorageKey = "phone2computer-token";

export interface AdminConfig {
  upload_url: string;
  output_directory: string;
}

export type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export async function loadAdminConfig(fetcher: Fetcher = fetch): Promise<AdminConfig> {
  const response = await fetcher("/api/admin/config");
  if (!response.ok) {
    throw new Error(`读取管理配置失败（${response.status}）`);
  }
  const payload: unknown = await response.json();
  if (!isAdminConfig(payload)) {
    throw new Error("管理配置格式无效");
  }
  return payload;
}

function isAdminConfig(value: unknown): value is AdminConfig {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return typeof candidate.upload_url === "string" && typeof candidate.output_directory === "string";
}

export interface TokenStorage {
  getItem: (key: string) => string | null;
  setItem: (key: string, value: string) => unknown;
}

export type ReplaceState = (data: unknown, unused: string, url?: string | URL | null) => void;

export function consumePairingToken(
  url: URL,
  storage: TokenStorage,
  replaceState: ReplaceState,
): string | null {
  const token = url.searchParams.get("token");
  if (!token) {
    return storage.getItem(tokenStorageKey);
  }

  storage.setItem(tokenStorageKey, token);
  url.searchParams.delete("token");
  const query = url.searchParams.toString();
  replaceState(null, "", `${url.pathname}${query ? `?${query}` : ""}${url.hash}`);
  return token;
}
