from flask import Flask, render_template_string, jsonify, request, g, session, Response, stream_with_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
import sys
import os
import secrets
import logging
import threading
import json
import simpy

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from constellasim.engine import ConstellationSimulator
from constellasim.node import GroundStation, Satellite
from constellasim.utils import Geocoder
from constellasim.llm import NetworkAI
from constellasim.planner import NetworkPlanner
from constellasim.monitor import AnomalyMonitor

app = Flask(__name__)
# CRITICAL-2/M-6: require an explicit secret key so sessions are cryptographically sound.
_secret = os.getenv("FLASK_SECRET_KEY")
if not _secret:
    raise RuntimeError("FLASK_SECRET_KEY environment variable must be set")
app.secret_key = _secret
# Raise to 8 KB to accommodate chat message history in POST bodies.
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024
# M-1: trust the first X-Forwarded-For hop so flask-limiter sees the real client IP.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "30 per minute"])

# Wrap NetworkAI init to allow graceful degradation when API keys are absent.
try:
    ai_analyst = NetworkAI()
except Exception:
    logging.getLogger(__name__).exception("Failed to initialize NetworkAI — AI analysis will be unavailable")
    ai_analyst = None

# Feature 3: NL planner (shares the existing AI client).
_planner = NetworkPlanner(ai_analyst) if ai_analyst else None

# Optimization: share a single Geocoder instance to reuse its result cache across requests.
_geocoder = Geocoder()
# V-03: global semaphore to cap simultaneous CPU-bound simulations.
_sim_semaphore = threading.Semaphore(4)

# Feature 4: Anomaly monitor (opt-in via ANOMALY_MONITOR=true).
_monitor = None
if os.getenv("ANOMALY_MONITOR", "").lower() == "true" and ai_analyst:
    _monitor = AnomalyMonitor(ai_analyst)

# Feature 5: Last simulation snapshot for the briefing endpoint.
_last_sim: dict = {}
_sim_lock = threading.Lock()

if _monitor:
    _monitor.set_sim_source(_last_sim, _sim_lock)
    _monitor.start()


@app.before_request
def generate_csp_nonce():
    """Generate a per-request nonce for use in CSP and script tags."""
    g.csp_nonce = secrets.token_urlsafe(16)


@app.after_request
def set_security_headers(response):
    """Add browser-level security headers to every response."""
    nonce = getattr(g, 'csp_nonce', '')
    response.headers['Content-Security-Policy'] = (
        f"default-src 'self'; script-src 'self' 'nonce-{nonce}'; style-src 'self' 'nonce-{nonce}'"
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains'
    return response


@app.route('/')
def home():
    """Renders the Mobile Configurator UI."""
    return render_template_string(HTML_TEMPLATE, nonce=g.csp_nonce)


def _run_simulation(src_lat, src_lon, dest_city):
    """Shared helper: run a constellation simulation and return stats dict."""
    dest_lat, dest_lon = _geocoder.resolve_location(dest_city)
    if not dest_lat:
        return None, "Destination could not be resolved"

    env = simpy.Environment()
    sim = ConstellationSimulator(env)

    sats = ["SAT1", "SAT2", "SAT3"]
    for s in sats:
        sim.add_node(Satellite(env, s, 1))
    sim.add_link("SAT1", "SAT2", weight=5.0)
    sim.add_link("SAT2", "SAT3", weight=5.0)

    gs_src = GroundStation(env, "Mobile-User", src_lat, src_lon)
    dest_node_id = f"Gateway-{abs(hash(dest_city)) % 100000}"
    gs_dest = GroundStation(env, dest_node_id, dest_lat, dest_lon)
    sim.add_node(gs_src)
    sim.add_node(gs_dest)
    sim.add_link(gs_src.node_id, "SAT1", weight=2.0)
    sim.add_link(gs_dest.node_id, "SAT3", weight=2.0)

    if not _sim_semaphore.acquire(blocking=False):
        return None, "Server busy, please retry shortly."
    try:
        env.process(sim.send_packet(gs_src.node_id, gs_dest.node_id, 1))
        env.run(until=50)
    finally:
        _sim_semaphore.release()

    report = sim.generate_report()
    latency = sim.stats["latencies"][0] if sim.stats["latencies"] else None
    return {
        "report": report,
        "latency": latency,
        "src": f"{src_lat:.2f}, {src_lon:.2f}",
        "dest": f"{dest_city} ({dest_lat:.2f}, {dest_lon:.2f})",
        "dest_lat": dest_lat,
        "dest_lon": dest_lon,
    }, None


# --- Original blocking simulate endpoint (kept for API compatibility) ---
@app.route('/api/simulate', methods=['POST'])
@limiter.limit("30 per minute")
def run_sim():
    """Run a quick LEO simulation based on user coordinates."""
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400
    try:
        src_lat = float(data['src_lat'])
        src_lon = float(data['src_lon'])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "src_lat and src_lon must be valid numbers"}), 400
    if not (-90 <= src_lat <= 90) or not (-180 <= src_lon <= 180):
        return jsonify({"error": "Coordinates out of range"}), 400

    dest_city = data.get('dest_city', 'New York')
    if not isinstance(dest_city, str) or not dest_city.strip() or len(dest_city) > 100:
        return jsonify({"error": "Invalid destination city"}), 400
    from constellasim.llm import _sanitize
    dest_city = _sanitize(dest_city.strip())

    result, err = _run_simulation(src_lat, src_lon, dest_city)
    if err:
        status_code = 503 if "busy" in err else 400
        return jsonify({"error": err}), status_code

    with _sim_lock:
        _last_sim.update({
            "source": result["src"],
            "destination": result["dest"],
            "latency_ms": f"{result['latency']:.2f}" if result["latency"] else "dropped",
            "status": "Success" if result["latency"] else "Failed",
            "packet_loss_pct": 0 if result["latency"] else 100,
        })

    try:
        if ai_analyst is None:
            raise RuntimeError("AI not configured")
        ai_analysis = ai_analyst.analyze_report(result["report"])
    except Exception:
        app.logger.exception("AI analysis failed")
        ai_analysis = "AI analysis temporarily unavailable."

    if result["latency"] is not None:
        return jsonify({
            "status": "Success",
            "source": result["src"],
            "destination": result["dest"],
            "latency_ms": f"{result['latency']:.2f}",
            "ai_analysis": ai_analysis,
        })
    else:
        return jsonify({"status": "Failed", "error": "Packet dropped", "ai_analysis": ai_analysis}), 500


# --- Feature 1: Streaming SSE endpoint ---
@app.route('/api/simulate/stream')
@limiter.limit("30 per minute")
def run_sim_stream():
    try:
        src_lat = float(request.args.get('src_lat', ''))
        src_lon = float(request.args.get('src_lon', ''))
    except (TypeError, ValueError):
        return jsonify({"error": "src_lat and src_lon query params are required"}), 400
    if not (-90 <= src_lat <= 90) or not (-180 <= src_lon <= 180):
        return jsonify({"error": "Coordinates out of range"}), 400

    dest_city = request.args.get('dest_city', 'New York')
    if not isinstance(dest_city, str) or not dest_city.strip() or len(dest_city) > 100:
        return jsonify({"error": "Invalid destination city"}), 400
    from constellasim.llm import _sanitize
    dest_city = _sanitize(dest_city.strip())

    result, err = _run_simulation(src_lat, src_lon, dest_city)
    if err:
        return jsonify({"error": err}), 503 if "busy" in err else 400

    with _sim_lock:
        _last_sim.update({
            "source": result["src"],
            "destination": result["dest"],
            "latency_ms": f"{result['latency']:.2f}" if result["latency"] else "dropped",
            "status": "Success" if result["latency"] else "Failed",
            "packet_loss_pct": 0 if result["latency"] else 100,
        })

    sim_payload = {
        "status": "Success" if result["latency"] else "Failed",
        "source": result["src"],
        "destination": result["dest"],
        "latency_ms": f"{result['latency']:.2f}" if result["latency"] else "Dropped",
    }

    def generate():
        yield f"event: simresult\ndata: {json.dumps(sim_payload)}\n\n"
        if ai_analyst is None:
            yield f"data: {json.dumps('AI analysis unavailable.')}\n\n"
        else:
            try:
                for chunk in ai_analyst.analyze_report_stream(result["report"]):
                    yield f"data: {json.dumps(chunk)}\n\n"
            except Exception:
                app.logger.exception("Streaming AI analysis failed")
                yield f"data: {json.dumps('AI analysis error.')}\n\n"
        yield "event: done\ndata: {}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


# --- Feature 2: Multi-turn chat ---
_MAX_CHAT_TURNS = 10


@app.route('/api/chat', methods=['POST'])
@limiter.limit("30 per minute")
def chat():
    if ai_analyst is None:
        return jsonify({"error": "AI not configured"}), 503
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400
    user_msg = data.get("message", "")
    if not isinstance(user_msg, str) or not user_msg.strip():
        return jsonify({"error": "message must be a non-empty string"}), 400
    user_msg = user_msg.strip()[:1000]

    from constellasim.llm import _sanitize
    user_msg = _sanitize(user_msg)

    history = session.get("chat_history", [])

    if not history:
        with _sim_lock:
            snapshot = dict(_last_sim)
        system_content = (
            "You are a Satellite Network Architect. Answer follow-up questions about the current "
            "simulation session. Latest simulation snapshot:\n"
            + json.dumps(snapshot, indent=2)
        )
        history = [{"role": "system", "content": system_content}]

    history.append({"role": "user", "content": user_msg})

    try:
        reply = ai_analyst.chat(history)
    except Exception:
        app.logger.exception("Chat AI call failed")
        return jsonify({"error": "AI temporarily unavailable."}), 503

    history.append({"role": "assistant", "content": reply})

    max_msgs = 1 + _MAX_CHAT_TURNS * 2
    if len(history) > max_msgs:
        history = [history[0]] + history[-(max_msgs - 1):]

    session["chat_history"] = history
    return jsonify({"reply": reply})


@app.route('/api/chat/reset', methods=['POST'])
def chat_reset():
    session.pop("chat_history", None)
    return jsonify({"status": "ok"})


# --- Feature 3: NL2Function planner ---
@app.route('/api/plan', methods=['POST'])
@limiter.limit("20 per minute")
def plan():
    if _planner is None:
        return jsonify({"error": "AI not configured"}), 503
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400
    query = data.get("query", "")
    if not isinstance(query, str) or not query.strip():
        return jsonify({"error": "query must be a non-empty string"}), 400

    intent = _planner.parse(query.strip())
    func = intent.get("function")
    params = intent.get("params", {})

    if not func:
        return jsonify({"error": "I didn't understand that. Try: 'Simulate a packet to Berlin' or 'Topology with 6 satellites'"}), 422

    if func == "simulate":
        dest_city = params.get("dest_city", "")
        if not dest_city or not isinstance(dest_city, str):
            return jsonify({"error": "dest_city is required for simulate"}), 400
        from constellasim.llm import _sanitize
        dest_city = _sanitize(str(dest_city)[:100].strip())

        # Use src_city if provided; otherwise return a placeholder asking for GPS
        src_city = params.get("src_city", "")
        if src_city and isinstance(src_city, str):
            src_city = _sanitize(src_city[:100].strip())
            src_lat, src_lon = _geocoder.resolve_location(src_city)
            if src_lat is None:
                return jsonify({"error": "Could not resolve source city."}), 400
        else:
            # Fall back: use London as default source when GPS not available via planner
            src_lat, src_lon = _geocoder.resolve_location("London")
            if src_lat is None:
                src_lat, src_lon = 51.5, -0.12

        result, err = _run_simulation(src_lat, src_lon, dest_city)
        if err:
            return jsonify({"error": err}), 503 if "busy" in err else 400

        return jsonify({
            "function": "simulate",
            "source": result["src"],
            "destination": result["dest"],
            "latency_ms": f"{result['latency']:.2f}" if result["latency"] else "Dropped",
            "status": "Success" if result["latency"] else "Failed",
        })

    if func == "topology_info":
        sat_count = params.get("sat_count", 3)
        try:
            sat_count = int(sat_count)
        except (TypeError, ValueError):
            sat_count = 3
        sat_count = max(1, min(sat_count, 20))
        return jsonify({
            "function": "topology_info",
            "sat_count": sat_count,
            "topology": f"Linear chain of {sat_count} satellite(s) connecting ground stations at both ends.",
            "note": "Run a simulation to see live performance metrics.",
        })

    return jsonify({"error": "Unknown function"}), 422


# --- Feature 4: Alert feed ---
@app.route('/api/alerts')
def alerts():
    if _monitor is None:
        return jsonify([])
    return jsonify(_monitor.get_alerts())


# --- Feature 5: Network briefing download ---
@app.route('/api/briefing')
@limiter.limit("5 per minute")
def briefing():
    if ai_analyst is None:
        return jsonify({"error": "AI not configured"}), 503
    with _sim_lock:
        snapshot = dict(_last_sim)
    if not snapshot:
        return jsonify({"error": "No simulation data yet. Run a simulation first."}), 400
    try:
        report = ai_analyst.generate_briefing(snapshot)
    except Exception:
        app.logger.exception("Briefing generation failed")
        return jsonify({"error": "Briefing generation failed."}), 503

    return Response(
        report,
        mimetype='text/markdown',
        headers={'Content-Disposition': 'attachment; filename="network_briefing.md"'},
    )


# --- Mobile HTML/JS Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ConstellaSim AI</title>
    <style nonce="{{ nonce }}">
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #111827; color: #f3f4f6; text-align: center; padding: 20px; }
        .card { background: #1f2937; border-radius: 12px; padding: 20px; margin: 15px auto; max-width: 400px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        h1 { font-size: 1.5rem; margin-bottom: 20px; color: #a78bfa; }
        h3 { margin: 16px 0 8px; font-size: 1rem; color: #9ca3af; }
        .text-input { width: calc(100% - 24px); padding: 12px; margin: 10px 0; border-radius: 8px; border: 1px solid #374151; background: #374151; color: white; font-size: 1rem; box-sizing: border-box; }
        .btn-primary { background: #8b5cf6; color: white; border: none; padding: 15px 30px; font-size: 1.1rem; border-radius: 50px; cursor: pointer; width: 100%; margin-top: 10px; transition: background 0.2s; }
        .btn-primary:active { background: #7c3aed; transform: scale(0.98); }
        .ai-box { background: #4c1d95; border-left: 4px solid #a78bfa; padding: 15px; text-align: left; font-size: 0.9rem; margin-top: 10px; border-radius: 4px; white-space: pre-wrap; min-height: 40px; }
        .data-row { display: flex; justify-content: space-between; margin: 8px 0; }
        .label { color: #9ca3af; }
        .value { font-weight: bold; color: #34d399; }
        #status { margin-top: 15px; color: #fbbf24; }
        .hidden { display: none; }
        /* Alert badge */
        #alert-badge { position: fixed; top: 12px; right: 12px; background: #ef4444; color: white; border-radius: 50px; padding: 6px 14px; font-size: 0.82rem; cursor: pointer; z-index: 100; display: none; border: none; }
        #alert-badge.show { display: block; }
        .alert-item { padding: 8px; border-radius: 6px; margin: 6px 0; font-size: 0.83rem; text-align: left; }
        .alert-WARNING { background: #431407; }
        .alert-CRITICAL { background: #7f1d1d; }
        /* Chat widget */
        .chat-section { text-align: left; margin-top: 15px; border-top: 1px solid #374151; padding-top: 15px; }
        #chat-messages { max-height: 200px; overflow-y: auto; margin-bottom: 10px; }
        .chat-msg-user { background: #1e3a5f; padding: 8px 12px; border-radius: 8px 8px 2px 8px; margin: 5px 0; font-size: 0.87rem; }
        .chat-msg-ai { background: #14532d; padding: 8px 12px; border-radius: 2px 8px 8px 8px; margin: 5px 0; font-size: 0.87rem; }
        .chat-msg-error { background: #450a0a; padding: 8px 12px; border-radius: 4px; margin: 5px 0; font-size: 0.87rem; }
        .chat-input-row { display: flex; gap: 8px; }
        .chat-input-row input { flex: 1; padding: 10px; border-radius: 8px; border: 1px solid #374151; background: #111827; color: white; font-size: 0.9rem; }
        .chat-input-row button { background: #8b5cf6; color: white; border: none; padding: 10px 16px; border-radius: 8px; cursor: pointer; }
        .btn-secondary { background: transparent; border: 1px solid #4b5563; color: #9ca3af; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 0.8rem; margin-top: 8px; }
        .btn-briefing { background: #064e3b; color: #6ee7b7; border: 1px solid #059669; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 0.9rem; margin-top: 12px; width: 100%; }
        /* Streaming cursor */
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        .cursor { display: inline-block; width: 7px; height: 1em; background: #a78bfa; animation: blink 1s step-end infinite; vertical-align: text-bottom; margin-left: 2px; }
    </style>
</head>
<body>
    <!-- Feature 4: Alert badge -->
    <button id="alert-badge" onclick="toggleAlerts()">&#9888; <span id="alert-count">0</span> Alert(s)</button>

    <h1>&#127760; ConstellaSim AI</h1>
    <p>Intelligent Network Optimization</p>

    <!-- Alert panel -->
    <div id="alert-panel" class="card hidden">
        <h3>Active Alerts</h3>
        <div id="alert-list"></div>
    </div>

    <!-- Feature 3: NL Planner -->
    <div class="card">
        <h3>Ask in Plain English</h3>
        <input type="text" class="text-input" id="nl_query"
               placeholder='e.g. "Simulate packet from Paris to Tokyo"'>
        <button class="btn-primary" style="font-size:0.95rem;padding:10px 20px;"
                onclick="askPlainEnglish()">Ask AI</button>
        <pre id="nl_result" class="hidden"
             style="margin-top:8px;font-size:0.83rem;color:#9ca3af;text-align:left;white-space:pre-wrap;"></pre>
    </div>

    <!-- Main simulation card -->
    <div class="card">
        <input type="text" class="text-input" id="destination"
               placeholder="Destination City (e.g. London)" value="London">
        <button class="btn-primary" onclick="runSimulation()">&#128640; Run AI Diagnostic</button>
        <div id="status"></div>
        <button class="btn-briefing hidden" id="briefing-btn" onclick="downloadBriefing()">
            &#128196; Download Briefing
        </button>
    </div>

    <!-- Results -->
    <div id="results" class="card hidden">
        <h3>Simulation Stats</h3>
        <div class="data-row"><span class="label">Target</span><span class="value" id="res_dest">-</span></div>
        <div class="data-row"><span class="label">Latency</span><span class="value" id="res_lat">-</span></div>

        <h3>&#129302; AI Topology Analysis</h3>
        <div class="ai-box">
            <span id="ai-text"></span><span id="ai-cursor" class="cursor hidden"></span>
        </div>

        <!-- Feature 2: Chat widget -->
        <div class="chat-section hidden" id="chat-widget">
            <h3>&#128172; Ask Follow-up Questions</h3>
            <div id="chat-messages"></div>
            <div class="chat-input-row">
                <input type="text" id="chat-input" placeholder="Ask a follow-up question...">
                <button onclick="sendChat()">Send</button>
            </div>
            <button class="btn-secondary" onclick="resetChat()">New Chat</button>
        </div>
    </div>

    <script nonce="{{ nonce }}">
        var _eventSource = null;

        // Feature 4: Alert polling — DOM methods to avoid innerHTML with user data
        function pollAlerts() {
            fetch('/api/alerts').then(function(r) { return r.json(); }).then(function(alerts) {
                if (!alerts || alerts.length === 0) return;
                document.getElementById('alert-badge').classList.add('show');
                document.getElementById('alert-count').textContent = String(alerts.length);
                var list = document.getElementById('alert-list');
                while (list.firstChild) { list.removeChild(list.firstChild); }
                alerts.slice(0, 5).forEach(function(a) {
                    var item = document.createElement('div');
                    item.className = 'alert-item alert-' + (a.status === 'CRITICAL' ? 'CRITICAL' : 'WARNING');
                    var strong = document.createElement('strong');
                    strong.textContent = a.status || '';
                    item.appendChild(strong);
                    item.appendChild(document.createTextNode(' \u2014 ' + new Date(a.timestamp).toLocaleTimeString()));
                    var small = document.createElement('div');
                    small.style.fontSize = '0.8rem';
                    small.style.marginTop = '3px';
                    small.textContent = a.message || '';
                    item.appendChild(small);
                    list.appendChild(item);
                });
            }).catch(function() {});
        }
        setInterval(pollAlerts, 10000);
        pollAlerts();

        function toggleAlerts() {
            document.getElementById('alert-panel').classList.toggle('hidden');
        }

        // Feature 1: Streaming via EventSource
        function runSimulation() {
            var dest = document.getElementById('destination').value.trim();
            var status = document.getElementById('status');

            if (!navigator.geolocation) { status.textContent = "Geolocation needed."; return; }
            status.textContent = "Acquiring GPS...";

            navigator.geolocation.getCurrentPosition(function(pos) {
                var lat = pos.coords.latitude;
                var lon = pos.coords.longitude;
                status.textContent = "Running AI Analysis...";

                if (_eventSource) { _eventSource.close(); }
                document.getElementById('ai-text').textContent = '';
                document.getElementById('ai-cursor').classList.remove('hidden');

                var url = '/api/simulate/stream?src_lat=' + lat + '&src_lon=' + lon +
                          '&dest_city=' + encodeURIComponent(dest);
                _eventSource = new EventSource(url);

                _eventSource.addEventListener('simresult', function(e) {
                    var d = JSON.parse(e.data);
                    document.getElementById('results').classList.remove('hidden');
                    document.getElementById('res_dest').textContent = d.destination || '-';
                    document.getElementById('res_lat').textContent = (d.latency_ms || 'Dropped') + ' ms';
                });

                _eventSource.onmessage = function(e) {
                    var token = JSON.parse(e.data);
                    document.getElementById('ai-text').textContent += token;
                };

                _eventSource.addEventListener('done', function() {
                    _eventSource.close();
                    document.getElementById('ai-cursor').classList.add('hidden');
                    document.getElementById('briefing-btn').classList.remove('hidden');
                    document.getElementById('chat-widget').classList.remove('hidden');
                    status.textContent = "Analysis Complete";
                });

                _eventSource.onerror = function() {
                    _eventSource.close();
                    document.getElementById('ai-cursor').classList.add('hidden');
                    status.textContent = "Analysis Failed \u2014 please retry";
                };
            }, function() {
                status.textContent = "GPS Denied";
            });
        }

        // Feature 5: Briefing download
        function downloadBriefing() { window.location.href = '/api/briefing'; }

        // Feature 2: Chat — createElement + textContent to avoid XSS
        function appendChatMsg(text, cssClass) {
            var msgList = document.getElementById('chat-messages');
            var div = document.createElement('div');
            div.className = cssClass;
            div.textContent = text;
            msgList.appendChild(div);
            msgList.scrollTop = msgList.scrollHeight;
        }

        function sendChat() {
            var input = document.getElementById('chat-input');
            var msg = input.value.trim();
            if (!msg) return;
            input.value = '';
            appendChatMsg(msg, 'chat-msg-user');

            fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: msg})
            }).then(function(r) { return r.json(); }).then(function(data) {
                appendChatMsg(data.reply || data.error || 'No response', data.reply ? 'chat-msg-ai' : 'chat-msg-error');
            }).catch(function() {
                appendChatMsg('Error \u2014 please retry.', 'chat-msg-error');
            });
        }

        function resetChat() {
            fetch('/api/chat/reset', {method: 'POST'}).then(function() {
                var msgList = document.getElementById('chat-messages');
                while (msgList.firstChild) { msgList.removeChild(msgList.firstChild); }
            });
        }

        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('chat-input').addEventListener('keydown', function(e) {
                if (e.key === 'Enter') sendChat();
            });
            document.getElementById('nl_query').addEventListener('keydown', function(e) {
                if (e.key === 'Enter') askPlainEnglish();
            });
        });

        // Feature 3: NL Planner
        function askPlainEnglish() {
            var query = document.getElementById('nl_query').value.trim();
            var result = document.getElementById('nl_result');
            if (!query) return;
            result.textContent = 'Processing...';
            result.classList.remove('hidden');

            fetch('/api/plan', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query})
            }).then(function(r) { return r.json(); }).then(function(data) {
                result.textContent = data.error ? data.error : JSON.stringify(data, null, 2);
            }).catch(function() { result.textContent = 'Request failed.'; });
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5001))
    app.run(host=host, port=port, debug=debug)
