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
    demo_lat: float
    demo_lon: float
    demo_label: str
    anomaly_monitor: bool
    max_concurrent_sims: int


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
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5001,capacitor://localhost,https://localhost",
        ).split(",")
        if o.strip()
    ]
    return Settings(
        secret_key=secret,
        host=os.getenv("FLASK_HOST", os.getenv("HOST", "0.0.0.0")),
        port=int(os.getenv("PORT", "5001")),
        cors_origins=origins,
        demo_lat=float(os.getenv("DEMO_LAT", "34.1675")),
        demo_lon=float(os.getenv("DEMO_LON", "-118.5504")),
        demo_label=os.getenv("DEMO_LABEL", "Tarzana, CA"),
        anomaly_monitor=os.getenv("ANOMALY_MONITOR", "").lower() == "true",
        max_concurrent_sims=int(os.getenv("MAX_CONCURRENT_SIMS", "4")),
    )
