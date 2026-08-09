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
  demo_location: { lat: number; lon: number; label: string };
};

const jsonHeaders = { "Content-Type": "application/json", Accept: "application/json" };

export async function fetchHealth(): Promise<Health> {
  const r = await fetch("/api/health");
  if (!r.ok) throw new Error(`Health ${r.status}`);
  return r.json();
}

export async function fetchTopology(): Promise<Topology> {
  const r = await fetch("/api/topology");
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function planMission(query: string) {
  const r = await fetch("/api/plan", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ query }),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || data.error || "Plan failed");
  return data;
}

export async function sendChat(message: string, sessionId = "demo") {
  const r = await fetch("/api/chat", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || data.error || "Chat failed");
  return data as { reply: string };
}

export async function resetChat(sessionId = "demo") {
  await fetch(`/api/chat/reset?session_id=${encodeURIComponent(sessionId)}`, { method: "POST" });
}

export async function optimize(constraints: string) {
  const r = await fetch("/api/optimize", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ constraints }),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || data.error || "Optimize failed");
  return data as OptimizeResult;
}

export async function fetchAlerts(): Promise<{ status: string; message: string; timestamp: string }[]> {
  const r = await fetch("/api/alerts");
  if (!r.ok) return [];
  return r.json();
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
  const url =
    `/api/simulate/stream?src_lat=${lat}&src_lon=${lon}` +
    `&dest_city=${encodeURIComponent(destCity)}`;
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
    handlers.onError("Stream failed — is the API running on :5001?");
  };
  return es;
}
