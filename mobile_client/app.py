from flask import Flask, render_template_string, jsonify, request
import sys
import os
import simpy

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from constellasim.engine import ConstellationSimulator
from constellasim.node import GroundStation, Satellite
from constellasim.utils import Geocoder
from constellasim.llm import NetworkAI

app = Flask(__name__)
ai_analyst = NetworkAI()

@app.route('/')
def home():
    """Renders the Mobile Configurator UI."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/simulate', methods=['POST'])
def run_sim():
    """Run a quick LEO simulation based on user coordinates."""
    data = request.json
    
    # 1. Get Source (GPS) and Destination (Text)
    src_lat = float(data.get('src_lat'))
    src_lon = float(data.get('src_lon'))
    dest_city = data.get('dest_city', 'New York')
    
    # Resolve Destination
    geo = Geocoder()
    dest_lat, dest_lon = geo.resolve_location(dest_city)
    
    if not dest_lat:
        return jsonify({"error": f"Could not find city: {dest_city}"}), 400

    # 2. Setup Simulation
    env = simpy.Environment()
    sim = ConstellationSimulator(env)
    
    # Create simple constellation
    sats = ["SAT1", "SAT2", "SAT3"]
    for s in sats:
        sim.add_node(Satellite(env, s, 1))
    
    # Link Satellites (Mesh)
    sim.add_link("SAT1", "SAT2", weight=5.0) 
    sim.add_link("SAT2", "SAT3", weight=5.0)
    
    # Create Ground Stations
    gs_src = GroundStation(env, "Mobile-User", src_lat, src_lon)
    gs_dest = GroundStation(env, f"Gateway-{dest_city}", dest_lat, dest_lon)
    sim.add_node(gs_src)
    sim.add_node(gs_dest)
    
    sim.add_link(gs_src.node_id, "SAT1", weight=2.0)
    sim.add_link(gs_dest.node_id, "SAT3", weight=2.0)
    
    # 3. Run Traffic
    packet_id = 1
    env.process(sim.send_packet(gs_src.node_id, gs_dest.node_id, packet_id))
    env.run(until=50)
    
    # 4. Generate AI Analysis
    report = sim.generate_report()
    try:
        ai_analysis = ai_analyst.analyze_report(report)
    except Exception as e:
        ai_analysis = f"AI Analyst Offline: {e}"
    
    if sim.stats["latencies"]:
        latency = sim.stats["latencies"][0]
        return jsonify({
            "status": "Success",
            "source": f"{src_lat:.2f}, {src_lon:.2f}",
            "destination": f"{dest_city} ({dest_lat:.2f}, {dest_lon:.2f})",
            "latency_ms": f"{latency:.2f}",
            "ai_analysis": ai_analysis,
            "report": report
        })
    else:
        return jsonify({"status": "Failed", "error": "Packet dropped", "ai_analysis": ai_analysis}), 500

# --- Mobile HTML/JS Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ConstellaSim AI</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #111827; color: #f3f4f6; text-align: center; padding: 20px; }
        .card { background: #1f2937; border-radius: 12px; padding: 20px; margin: 15px auto; max-width: 400px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        h1 { font-size: 1.5rem; margin-bottom: 20px; color: #a78bfa; }
        input { width: 90%; padding: 12px; margin: 10px 0; border-radius: 8px; border: 1px solid #374151; background: #374151; color: white; font-size: 1rem; }
        button { background: #8b5cf6; color: white; border: none; padding: 15px 30px; font-size: 1.1rem; border-radius: 50px; cursor: pointer; width: 100%; margin-top: 10px; transition: background 0.2s; }
        button:active { background: #7c3aed; transform: scale(0.98); }
        .ai-box { background: #4c1d95; border-left: 4px solid #a78bfa; padding: 15px; text-align: left; font-size: 0.9rem; margin-top: 20px; border-radius: 4px; }
        .data-row { display: flex; justify-content: space-between; margin: 8px 0; }
        .label { color: #9ca3af; }
        .value { font-weight: bold; color: #34d399; }
    </style>
</head>
<body>
    <h1>🌐 ConstellaSim AI</h1>
    <p>Intelligent Network Optimization</p>
    
    <div class="card">
        <input type="text" id="destination" placeholder="Destination City (e.g. London)" value="London">
        <button onclick="runSimulation()">🚀 Run AI Diagnostic</button>
        <div id="status" style="margin-top:15px; color:#fbbf24;"></div>
    </div>

    <div id="results" class="card" style="display:none;">
        <h3>Simulation Stats</h3>
        <div class="data-row"><span class="label">Target</span><span class="value" id="res_dest">-</span></div>
        <div class="data-row"><span class="label">Latency</span><span class="value" id="res_lat">-</span></div>
        
        <h3>🤖 AI Topology Analysis</h3>
        <div id="ai_analysis" class="ai-box">Analyzing topology...</div>
    </div>

    <script>
        function runSimulation() {
            const dest = document.getElementById('destination').value;
            const status = document.getElementById('status');
            
            if (!navigator.geolocation) {
                status.textContent = "Geolocation needed.";
                return;
            }

            status.textContent = "Acquiring GPS...";
            navigator.geolocation.getCurrentPosition((pos) => {
                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                status.textContent = "Running AI Analysis...";
                
                fetch('/api/simulate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({src_lat: lat, src_lon: lon, dest_city: dest})
                })
                .then(res => res.json())
                .then(data => {
                    status.textContent = "Analysis Complete ✅";
                    document.getElementById('results').style.display = 'block';
                    document.getElementById('res_dest').textContent = data.destination;
                    document.getElementById('res_lat').textContent = (data.latency_ms || "Dropped") + " ms";
                    document.getElementById('ai_analysis').textContent = data.ai_analysis;
                })
                .catch(err => {
                    status.textContent = "Analysis Failed ❌";
                });
            }, (err) => {
                status.textContent = "GPS Denied ❌";
            });
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
