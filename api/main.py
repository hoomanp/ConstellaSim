"""ConstellaSim FastAPI application — recruiter demo backend."""

from __future__ import annotations

import json
import logging
import re
import secrets
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from constellasim import __version__
from constellasim.llm import _sanitize

from api.config import get_settings
from api.schemas import (
    ChatRequest,
    HealthResponse,
    OptimizeRequest,
    PlanRequest,
    SimulateRequest,
    SimulateResponse,
)
from api.simulation import (
    extract_city_from_query,
    remember_simulation,
    resolve_city,
    run_simulation,
)
from api.state import state

logger = logging.getLogger("constellasim.api")
WEB_DIST = ROOT / "web" / "dist"
_SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


def _session_id(x_session_id: str | None, fallback: str | None = None) -> str | None:
    raw = (x_session_id or fallback or "").strip()
    if not raw:
        return None
    if not _SESSION_RE.match(raw):
        raise HTTPException(status_code=400, detail="Invalid X-Session-Id")
    return raw


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data:; "
            "connect-src 'self' http: https:; "
            "frame-ancestors 'none'",
        )
        # HSTS only meaningful over HTTPS; harmless on HTTP demos.
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
        )
        return response


class OptionalApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = state.settings
        if settings.require_api_key and request.url.path.startswith("/api/"):
            if request.url.path == "/api/health":
                return await call_next(request)
            provided = request.headers.get("X-API-Key") or request.query_params.get("api_key")
            if not settings.api_key or not provided or not secrets.compare_digest(
                provided, settings.api_key
            ):
                return Response(content='{"detail":"Unauthorized"}', status_code=401, media_type="application/json")
        return await call_next(request)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    state.boot_ai()
    logger.info("ConstellaSim API ready — AI mode=%s", state.ai_mode)
    yield


app = FastAPI(
    title="ConstellaSim",
    description="LEO constellation packet-route simulator with RAG mission assistant",
    version=__version__,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_settings = get_settings()
_cors_origins = list(_settings.cors_origins)
if _settings.cors_allow_all:
    _cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-Session-Id", "X-API-Key"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(OptionalApiKeyMiddleware)


@app.get("/api/health", response_model=HealthResponse)
@limiter.exempt
def health(request: Request):
    return HealthResponse(
        status="ok",
        service="constellasim",
        version=__version__,
        ai=state.ai is not None,
        ai_mode=state.ai_mode,
        anomaly_monitor=state.monitor is not None,
        demo_location={
            "lat": state.settings.demo_lat,
            "lon": state.settings.demo_lon,
            "label": state.settings.demo_label,
        },
    )


@app.post("/api/simulate", response_model=SimulateResponse)
@limiter.limit("30/minute")
def simulate(
    request: Request,
    body: SimulateRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
):
    sid = _session_id(x_session_id)
    dest = _sanitize(body.dest_city)
    result, err = run_simulation(body.src_lat, body.src_lon, dest)
    if err:
        code = 503 if "busy" in err else 400
        raise HTTPException(status_code=code, detail=err)

    remember_simulation(result, session_id=sid)
    try:
        analysis = state.ai.analyze_report(result["report"]) if state.ai else "AI unavailable"
    except Exception:
        logger.exception("AI analysis failed")
        analysis = "AI analysis temporarily unavailable."

    if result["latency"] is None:
        return SimulateResponse(
            status="Failed",
            source=result["src"],
            destination=result["dest"],
            error="Packet dropped",
            ai_analysis=analysis,
            topology=result["topology"],
        )
    return SimulateResponse(
        status="Success",
        source=result["src"],
        destination=result["dest"],
        latency_ms=f"{result['latency']:.2f}",
        ai_analysis=analysis,
        topology=result["topology"],
    )


@app.get("/api/simulate/stream")
@limiter.limit("30/minute")
def simulate_stream(
    request: Request,
    src_lat: float = Query(...),
    src_lon: float = Query(...),
    dest_city: str = Query("New York"),
    session_id: str | None = Query(default=None),
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
):
    sid = _session_id(x_session_id, session_id)
    if not (-90 <= src_lat <= 90) or not (-180 <= src_lon <= 180):
        raise HTTPException(status_code=400, detail="Coordinates out of range")
    dest = _sanitize((dest_city or "").strip()[:100])
    if not dest:
        raise HTTPException(status_code=400, detail="Invalid destination city")

    result, err = run_simulation(src_lat, src_lon, dest)
    if err:
        raise HTTPException(status_code=503 if "busy" in err else 400, detail=err)

    remember_simulation(result, session_id=sid)
    payload = {
        "status": "Success" if result["latency"] else "Failed",
        "source": result["src"],
        "destination": result["dest"],
        "latency_ms": f"{result['latency']:.2f}" if result["latency"] else "Dropped",
        "topology": result["topology"],
    }

    def generate():
        yield f"event: simresult\ndata: {json.dumps(payload)}\n\n"
        if state.ai is None:
            yield f"data: {json.dumps('AI analysis unavailable.')}\n\n"
        else:
            try:
                for chunk in state.ai.analyze_report_stream(result["report"]):
                    yield f"data: {json.dumps(chunk)}\n\n"
            except Exception:
                logger.exception("Streaming AI failed")
                yield f"data: {json.dumps('AI analysis error.')}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/chat")
@limiter.limit("30/minute")
def chat(
    request: Request,
    body: ChatRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
):
    if state.ai is None:
        raise HTTPException(status_code=503, detail="AI not configured")
    msg = _sanitize(body.message.strip()[:1000])
    sid = _session_id(x_session_id, body.session_id) or "default"

    with state.chat_lock:
        history = list(state.chat_sessions.get(sid, []))
        if not history:
            snapshot = state.get_sim(sid)
            history = [{
                "role": "system",
                "content": (
                    "You are a Satellite Network Architect. Answer follow-up questions about the "
                    "current simulation session. Latest snapshot:\n"
                    + json.dumps(snapshot, indent=2)
                ),
            }]
        history.append({"role": "user", "content": msg})

    try:
        reply = state.ai.chat(history)
    except Exception:
        logger.exception("Chat failed")
        raise HTTPException(status_code=503, detail="AI temporarily unavailable.")

    history.append({"role": "assistant", "content": reply})
    max_msgs = 1 + 10 * 2
    if len(history) > max_msgs:
        history = [history[0]] + history[-(max_msgs - 1):]
    with state.chat_lock:
        state.chat_sessions[sid] = history
    return {"reply": reply}


@app.post("/api/chat/reset")
@limiter.limit("30/minute")
def chat_reset(
    request: Request,
    session_id: str = Query("default"),
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
):
    sid = _session_id(x_session_id, session_id) or "default"
    with state.chat_lock:
        state.chat_sessions.pop(sid, None)
    return {"status": "ok"}


@app.post("/api/plan")
@limiter.limit("20/minute")
def plan(
    request: Request,
    body: PlanRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
):
    if state.planner is None:
        raise HTTPException(status_code=503, detail="AI not configured")
    sid = _session_id(x_session_id)
    intent = state.planner.parse(body.query.strip())
    func = intent.get("function")
    params = intent.get("params", {})
    if not func:
        q = body.query.lower()
        if "simulat" in q or "packet" in q or "send" in q:
            city = extract_city_from_query(body.query)
            func = "simulate"
            params = {"dest_city": city or "Tokyo"}
        elif "topolog" in q or "satellite" in q:
            func = "topology_info"
            params = {"sat_count": 3}
        else:
            raise HTTPException(
                status_code=422,
                detail="I didn't understand that. Try: 'Simulate a packet to Berlin'",
            )

    if func == "simulate":
        dest_city = _sanitize(str(params.get("dest_city", ""))[:100].strip())
        if not dest_city:
            raise HTTPException(status_code=400, detail="dest_city is required for simulate")
        src_city = params.get("src_city", "")
        if src_city and isinstance(src_city, str):
            src_lat, src_lon = resolve_city(_sanitize(src_city[:100].strip()))
            if src_lat is None:
                raise HTTPException(status_code=400, detail="Could not resolve source city.")
        else:
            src_lat, src_lon = state.settings.demo_lat, state.settings.demo_lon
        result, err = run_simulation(src_lat, src_lon, dest_city)
        if err:
            raise HTTPException(status_code=503 if "busy" in err else 400, detail=err)
        remember_simulation(result, session_id=sid)
        return {
            "function": "simulate",
            "source": result["src"],
            "destination": result["dest"],
            "latency_ms": f"{result['latency']:.2f}" if result["latency"] else "Dropped",
            "status": "Success" if result["latency"] else "Failed",
            "topology": result["topology"],
        }

    if func == "topology_info":
        try:
            sat_count = int(params.get("sat_count", 3))
        except (TypeError, ValueError):
            sat_count = 3
        sat_count = max(1, min(sat_count, 20))
        return {
            "function": "topology_info",
            "sat_count": sat_count,
            "topology": f"Linear chain of {sat_count} satellite(s) connecting ground stations at both ends.",
            "note": "Run a simulation to see live performance metrics.",
        }

    raise HTTPException(status_code=422, detail="Unknown function")


@app.get("/api/topology")
@limiter.limit("60/minute")
def topology(
    request: Request,
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
):
    sid = _session_id(x_session_id)
    snapshot = state.get_sim(sid)
    topo = snapshot.get("topology")
    if not topo:
        raise HTTPException(status_code=400, detail="No simulation data yet. Run a simulation first.")
    return topo


@app.post("/api/optimize")
@limiter.limit("10/minute")
def optimize(
    request: Request,
    body: OptimizeRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
):
    if state.ai is None:
        raise HTTPException(status_code=503, detail="AI not configured")
    sid = _session_id(x_session_id)
    snapshot = state.get_sim(sid)
    if not snapshot:
        raise HTTPException(status_code=400, detail="No simulation data yet. Run a simulation first.")
    constraints = _sanitize((body.constraints or "").strip()[:300])
    try:
        return state.ai.optimize_topology(snapshot, constraints)
    except Exception:
        logger.exception("Optimize failed")
        raise HTTPException(status_code=503, detail="Optimization temporarily unavailable.")


@app.get("/api/alerts")
@limiter.limit("60/minute")
def alerts(request: Request):
    if state.monitor is None:
        return []
    return state.monitor.get_alerts()


@app.post("/api/alerts/evaluate")
@limiter.limit("20/minute")
def alerts_evaluate(request: Request):
    """Force an immediate anomaly evaluation (mobile / demo UX)."""
    if state.monitor is None:
        return {"alerts": [], "monitor": False}
    alerts_list = state.monitor.evaluate_now()
    return {"alerts": alerts_list, "monitor": True}


@app.get("/api/briefing")
@limiter.limit("5/minute")
def briefing(
    request: Request,
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
):
    if state.ai is None:
        raise HTTPException(status_code=503, detail="AI not configured")
    sid = _session_id(x_session_id)
    snapshot = state.get_sim(sid)
    if not snapshot:
        raise HTTPException(status_code=400, detail="No simulation data yet. Run a simulation first.")
    try:
        report = state.ai.generate_briefing(snapshot)
    except Exception:
        logger.exception("Briefing failed")
        raise HTTPException(status_code=503, detail="Briefing generation failed.")
    return Response(
        content=report,
        media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="network_briefing.md"'},
    )


@app.get("/api/demo-location")
@limiter.exempt
def demo_location(request: Request):
    return {
        "lat": state.settings.demo_lat,
        "lon": state.settings.demo_lon,
        "label": state.settings.demo_label,
    }


def _safe_web_file(full_path: str) -> Path | None:
    """Resolve a path under WEB_DIST or return None if unsafe / missing."""
    if not full_path or full_path.startswith("/") or "\\" in full_path:
        return None
    # Block traversal segments before resolve.
    parts = Path(full_path).parts
    if any(p == ".." or p.startswith("..") for p in parts):
        return None
    candidate = (WEB_DIST / full_path).resolve()
    root = WEB_DIST.resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    return None


# Serve the Vite production build when present (single-port demo mode).
if WEB_DIST.exists():
    assets = WEB_DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/")
    def spa_index():
        return FileResponse(WEB_DIST / "index.html")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        safe = _safe_web_file(full_path)
        if safe is not None:
            return FileResponse(safe)
        return FileResponse(WEB_DIST / "index.html")


def run():
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
