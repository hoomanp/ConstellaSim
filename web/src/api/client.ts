/** API client with configurable base URL for Capacitor / LAN demos. */

export type Topology = {
  nodes: { id: string; type: "satellite" | "ground" }[];
  edges: { source: string; target: string; weight: number }[];
  route: string[];
  dropped: boolean;
};

export type SimResult = {
  status: string;
  source: string;
  destination: string;
  latency_ms?: string;
  topology?: Topology;
};

export type OptimizeResult = {
  recommendations: { change: string; expected_impact: string; priority: string }[];
  rationale: string;
  health_score: number | null;
};

export type Health = {
  status: string;
  version: string;
  ai: boolean;
  ai_mode: string;
  anomaly_monitor: boolean;
  demo_location: { lat: number; lon: number; label: string };
};

export type AlertItem = {
  status: string;
  message: string;
  timestamp: string;
};

const STORAGE_KEY = "constellasim.apiBase";
const jsonHeaders = { "Content-Type": "application/json", Accept: "application/json" };

type CapWindow = Window & {
  Capacitor?: {
    isNativePlatform?: () => boolean;
    getPlatform?: () => string;
  };
};

export function isNativeApp(): boolean {
  const cap = (window as CapWindow).Capacitor;
  return Boolean(cap?.isNativePlatform?.());
}

export function defaultApiBase(): string {
  if (!isNativeApp()) return "";
  const platform = (window as CapWindow).Capacitor?.getPlatform?.() || "";
  if (platform === "android") return "http://10.0.2.2:5001";
  return "http://127.0.0.1:5001";
}

export function getApiBase(): string {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved != null && saved !== "") return saved.replace(/\/$/, "");
  } catch {
    /* ignore */
  }
  return defaultApiBase();
}

export function setApiBase(url: string): void {
  const cleaned = url.trim().replace(/\/$/, "");
  localStorage.setItem(STORAGE_KEY, cleaned);
}

function apiUrl(path: string): string {
  const base = getApiBase();
  if (!base) return path;
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

async function parseError(r: Response): Promise<string> {
  try {
    const data = await r.json();
    if (typeof data.detail === "string") return data.detail;
    if (data.error) return String(data.error);
    return JSON.stringify(data);
  } catch {
    return (await r.text()) || `HTTP ${r.status}`;
  }
}

export async function fetchHealth(): Promise<Health> {
  const r = await fetch(apiUrl("/api/health"));
  if (!r.ok) throw new Error(`Health ${r.status}`);
  return r.json();
}

export async function fetchTopology(): Promise<Topology> {
  const r = await fetch(apiUrl("/api/topology"));
  if (!r.ok) throw new Error(await parseError(r));
  return r.json();
}

export async function planMission(query: string) {
  const r = await fetch(apiUrl("/api/plan"), {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ query }),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || data.error || "Plan failed");
  return data;
}

export async function sendChat(message: string, sessionId = "demo") {
  const r = await fetch(apiUrl("/api/chat"), {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || data.error || "Chat failed");
  return data as { reply: string };
}

export async function resetChat(sessionId = "demo") {
  await fetch(apiUrl(`/api/chat/reset?session_id=${encodeURIComponent(sessionId)}`), {
    method: "POST",
  });
}

export async function optimize(constraints: string) {
  const r = await fetch(apiUrl("/api/optimize"), {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ constraints }),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || data.error || "Optimize failed");
  return data as OptimizeResult;
}

export async function fetchAlerts(): Promise<AlertItem[]> {
  const r = await fetch(apiUrl("/api/alerts"));
  if (!r.ok) return [];
  return r.json();
}

export async function evaluateAlerts(): Promise<AlertItem[]> {
  const r = await fetch(apiUrl("/api/alerts/evaluate"), { method: "POST" });
  if (!r.ok) return fetchAlerts();
  const data = await r.json();
  return data.alerts || [];
}

export async function downloadBriefing(): Promise<void> {
  const r = await fetch(apiUrl("/api/briefing"));
  if (!r.ok) throw new Error(await parseError(r));
  const text = await r.text();
  const blob = new Blob([text], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "network_briefing.md";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function streamSimulation(
  lat: number,
  lon: number,
  destCity: string,
  handlers: {
    onResult: (r: SimResult) => void;
    onToken: (t: string) => void;
    onDone: () => void;
    onError: (msg: string) => void;
  },
) {
  const url = apiUrl(
    `/api/simulate/stream?src_lat=${lat}&src_lon=${lon}` +
      `&dest_city=${encodeURIComponent(destCity)}`,
  );
  const es = new EventSource(url);

  es.addEventListener("simresult", (e) => {
    handlers.onResult(JSON.parse((e as MessageEvent).data));
  });
  es.onmessage = (e) => {
    handlers.onToken(JSON.parse(e.data));
  };
  es.addEventListener("done", () => {
    es.close();
    handlers.onDone();
  });
  es.onerror = () => {
    es.close();
    handlers.onError("Stream failed — check backend URL / API on :5001");
  };
  return es;
}
