"""Application settings for the ConstellaSim FastAPI backend."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    secret_key: str
    host: str
    port: int
    cors_origins: list[str]
    cors_allow_all: bool
    demo_lat: float
    demo_lon: float
    demo_label: str
    anomaly_monitor: bool
    max_concurrent_sims: int
    require_api_key: bool
    api_key: str | None


def get_settings() -> Settings:
    secret = os.getenv("FLASK_SECRET_KEY") or os.getenv("CONSTELLASIM_SECRET_KEY")
    if not secret:
        # Demo-friendly default so recruiters can boot without ceremony.
        # Override in any shared/production deployment.
        secret = "constellasim-demo-secret-change-me"
    origins = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5001,"
            "http://127.0.0.1:5001,capacitor://localhost,https://localhost,"
            "http://localhost,https://localhost:5173",
        ).split(",")
        if o.strip()
    ]
    api_key = os.getenv("CONSTELLASIM_API_KEY") or None
    return Settings(
        secret_key=secret,
        # 0.0.0.0 enables phone-on-LAN demos; bind 127.0.0.1 for local-only.
        host=os.getenv("FLASK_HOST", os.getenv("HOST", "0.0.0.0")),  # nosec B104
        port=int(os.getenv("PORT", "5001")),
        cors_origins=origins,
        # Opt-in wildcard CORS for throwaway demos only.
        cors_allow_all=os.getenv("CORS_ALLOW_ALL", "false").lower() in {"1", "true", "yes"},
        demo_lat=float(os.getenv("DEMO_LAT", "34.1675")),
        demo_lon=float(os.getenv("DEMO_LON", "-118.5504")),
        demo_label=os.getenv("DEMO_LABEL", "Tarzana, CA"),
        anomaly_monitor=os.getenv("ANOMALY_MONITOR", "true").lower() in {"1", "true", "yes", "on"},
        max_concurrent_sims=int(os.getenv("MAX_CONCURRENT_SIMS", "4")),
        require_api_key=os.getenv("REQUIRE_API_KEY", "false").lower() in {"1", "true", "yes"},
        api_key=api_key,
    )
