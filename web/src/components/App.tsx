import { useEffect, useRef, useState } from "react";
import {
  fetchAlerts,
  fetchHealth,
  optimize,
  planMission,
  resetChat,
  sendChat,
  streamSimulation,
  type Health,
  type OptimizeResult,
  type SimResult,
  type Topology,
} from "../api/client";
import { useGeolocation } from "../hooks/useGeolocation";
import { TopologyMap } from "./TopologyMap";

export function App() {
  const geo = useGeolocation();
  const [health, setHealth] = useState<Health | null>(null);
  const [dest, setDest] = useState("Tokyo");
  const [status, setStatus] = useState("Standing by");
  const [result, setResult] = useState<SimResult | null>(null);
  const [topology, setTopology] = useState<Topology | null>(null);
  const [aiText, setAiText] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [nl, setNl] = useState('Simulate a packet from Tarzana to Singapore');
  const [nlOut, setNlOut] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [chat, setChat] = useState<{ role: "user" | "ai"; text: string }[]>([]);
  const [constraints, setConstraints] = useState("minimize latency");
  const [opt, setOpt] = useState<OptimizeResult | null>(null);
  const [alerts, setAlerts] = useState<{ status: string; message: string }[]>([]);
  const [showAlerts, setShowAlerts] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setStatus("API offline — start `python -m api.main`"));
    const t = setInterval(() => {
      fetchAlerts().then(setAlerts).catch(() => undefined);
    }, 10000);
    fetchAlerts().then(setAlerts).catch(() => undefined);
    return () => {
      clearInterval(t);
      esRef.current?.close();
    };
  }, []);

  function coordsForRun(demo: boolean) {
    if (demo && health) {
      return { lat: health.demo_location.lat, lon: health.demo_location.lon, label: health.demo_location.label };
    }
    if (geo.status === "ready") {
      return { lat: geo.lat, lon: geo.lon, label: "Device GPS" };
    }
    if (health) {
      return { lat: health.demo_location.lat, lon: health.demo_location.lon, label: `${health.demo_location.label} (fallback)` };
    }
    return { lat: 34.1675, lon: -118.5504, label: "Tarzana, CA" };
  }

  function runDiagnostic(demo = false) {
    const c = coordsForRun(demo);
    setStatus(`Uplink from ${c.label} → ${dest}…`);
    setAiText("");
    setStreaming(true);
    setOpt(null);
    esRef.current?.close();
    esRef.current = streamSimulation(c.lat, c.lon, dest, {
      onResult: (r) => {
        setResult(r);
        if (r.topology) setTopology(r.topology);
      },
      onToken: (t) => setAiText((prev) => prev + t),
      onDone: () => {
        setStreaming(false);
        setStatus("Analysis complete");
      },
      onError: (msg) => {
        setStreaming(false);
        setStatus(msg);
      },
    });
  }

  async function onPlan() {
    setNlOut("Parsing…");
    try {
      const data = await planMission(nl);
      setNlOut(JSON.stringify(data, null, 2));
      if (data.topology) setTopology(data.topology);
      if (data.destination) {
        setResult({
          status: data.status,
          source: data.source,
          destination: data.destination,
          latency_ms: data.latency_ms,
          topology: data.topology,
        });
      }
    } catch (e) {
      setNlOut(e instanceof Error ? e.message : "Plan failed");
    }
  }

  async function onChat() {
    const msg = chatInput.trim();
    if (!msg) return;
    setChatInput("");
    setChat((c) => [...c, { role: "user", text: msg }]);
    try {
      const { reply } = await sendChat(msg);
      setChat((c) => [...c, { role: "ai", text: reply }]);
    } catch (e) {
      setChat((c) => [...c, { role: "ai", text: e instanceof Error ? e.message : "Chat failed" }]);
    }
  }

  async function onOptimize() {
    try {
      setOpt(await optimize(constraints));
    } catch (e) {
      setOpt({
        recommendations: [],
        rationale: e instanceof Error ? e.message : "Optimize failed",
        health_score: null,
      });
    }
  }

  return (
    <div className="app-shell">
      <div className="starfield" aria-hidden>
        <div className="orbit-ring r1" />
        <div className="orbit-ring r2" />
        <div className="orbit-ring r3" />
      </div>

      <button
        type="button"
        className={`alert-pill${alerts.length ? " show" : ""}`}
        onClick={() => setShowAlerts((v) => !v)}
      >
        <span>{alerts.length}</span> alert{alerts.length === 1 ? "" : "s"}
      </button>

      <div className="content">
        <header className="hero">
          <h1 className="brand">ConstellaSim</h1>
          <p className="headline">Packet-level LEO mesh, live on your phone.</p>
          <p className="lede">
            Discrete-event routing across a satellite constellation, streamed with an AI network
            architect — built as a hiring demo you can run in minutes.
          </p>
          <div className="cta-row">
            <a className="btn btn-primary" href="#console">
              Open mission console
            </a>
            <button type="button" className="btn btn-ghost" onClick={() => runDiagnostic(true)}>
              Run demo diagnostic
            </button>
          </div>
        </header>

        <section className="section" id="console">
          <div className="section-head">
            <div>
              <h2>Mission console</h2>
              <p>
                GPS source → Dijkstra ISL path → SimPy hop delays → SSE AI critique. AI mode:{" "}
                <strong>{health?.ai_mode ?? "…"}</strong>
                {health ? ` · v${health.version}` : ""}
              </p>
            </div>
          </div>

          {showAlerts && alerts.length > 0 && (
            <div className="panel" style={{ marginBottom: 16 }}>
              <h3>Anomaly feed</h3>
              {alerts.slice(0, 5).map((a, i) => (
                <div key={i} className="rec HIGH">
                  <strong>{a.status}</strong> — {a.message}
                </div>
              ))}
            </div>
          )}

          <div className="console">
            <div className="panel">
              <h3>Uplink</h3>
              <div className="field">
                <label htmlFor="dest">Destination city</label>
                <input
                  id="dest"
                  value={dest}
                  onChange={(e) => setDest(e.target.value)}
                  placeholder="Tokyo, London, Singapore…"
                />
              </div>
              <div className="actions">
                <button type="button" className="btn btn-primary" onClick={() => runDiagnostic(false)}>
                  Run AI diagnostic
                </button>
                <button type="button" className="btn btn-ghost" onClick={() => runDiagnostic(true)}>
                  Demo mode
                </button>
                <a className="btn btn-ghost" href="/api/briefing" style={{ textDecoration: "none" }}>
                  Briefing
                </a>
              </div>
              <div className="status-line">{status}</div>
              {result && (
                <div className="metrics">
                  <div className="metric">
                    <span className="k">Target</span>
                    <span className="v">{result.destination}</span>
                  </div>
                  <div className="metric">
                    <span className="k">Latency</span>
                    <span className="v">{result.latency_ms ?? "—"} ms</span>
                  </div>
                  <div className="metric">
                    <span className="k">Status</span>
                    <span className="v">{result.status}</span>
                  </div>
                </div>
              )}

              <div style={{ marginTop: 16 }}>
                <h3>Live packet route</h3>
                <TopologyMap topology={topology} />
              </div>
            </div>

            <div className="panel">
              <h3>AI topology analysis</h3>
              <div className="ai-box">
                {aiText || "Awaiting stream…"}
                {streaming && <span className="cursor" />}
              </div>

              <div style={{ marginTop: 18 }}>
                <h3>Ask in plain English</h3>
                <div className="field">
                  <label htmlFor="nl">NL planner</label>
                  <input id="nl" value={nl} onChange={(e) => setNl(e.target.value)} />
                </div>
                <button type="button" className="btn btn-ghost" onClick={onPlan}>
                  Ask AI
                </button>
                {nlOut && (
                  <pre style={{ marginTop: 10, whiteSpace: "pre-wrap", color: "#8b9bb4", fontSize: "0.82rem" }}>
                    {nlOut}
                  </pre>
                )}
              </div>
            </div>

            <div className="panel">
              <h3>Follow-up chat</h3>
              <div className="chat-log">
                {chat.map((m, i) => (
                  <div key={i} className={`bubble ${m.role === "user" ? "user" : "ai"}`}>
                    {m.text}
                  </div>
                ))}
              </div>
              <div className="chat-row">
                <input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && onChat()}
                  placeholder="Why did SAT2 dominate delay?"
                />
                <button type="button" className="btn btn-primary" onClick={onChat}>
                  Send
                </button>
              </div>
              <button
                type="button"
                className="btn btn-ghost"
                style={{ marginTop: 10 }}
                onClick={() => {
                  resetChat();
                  setChat([]);
                }}
              >
                New chat
              </button>
            </div>

            <div className="panel">
              <h3>Topology optimizer</h3>
              <div className="field">
                <label htmlFor="opt">Goal</label>
                <input id="opt" value={constraints} onChange={(e) => setConstraints(e.target.value)} />
              </div>
              <button type="button" className="btn btn-ghost" onClick={onOptimize}>
                Optimize mesh
              </button>
              {opt && (
                <div style={{ marginTop: 12 }}>
                  {opt.health_score != null && (
                    <span className="health">Health {opt.health_score}/100</span>
                  )}
                  <p style={{ color: "#c5d0e0", fontSize: "0.92rem" }}>{opt.rationale}</p>
                  {opt.recommendations.map((r, i) => (
                    <div key={i} className={`rec ${r.priority || "MEDIUM"}`}>
                      <strong>[{r.priority}] {r.change}</strong>
                      <div style={{ color: "#8b9bb4", marginTop: 4 }}>→ {r.expected_impact}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>

        <footer className="footer">
          <strong>Stack for this demo</strong>
          <div className="stack-tags">
            <span className="tag">FastAPI</span>
            <span className="tag">SimPy DES</span>
            <span className="tag">NetworkX Dijkstra</span>
            <span className="tag">SSE streaming</span>
            <span className="tag">RAG / multi-cloud AI</span>
            <span className="tag">React 19 + Vite</span>
            <span className="tag">Capacitor iOS/Android</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
