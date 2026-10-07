"""Pydantic request/response models."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class SimulateRequest(BaseModel):
    src_lat: float
    src_lon: float
    dest_city: str = "London"

    @field_validator("src_lat")
    @classmethod
    def lat_range(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError("src_lat out of range")
        return v

    @field_validator("src_lon")
    @classmethod
    def lon_range(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError("src_lon out of range")
        return v

    @field_validator("dest_city")
    @classmethod
    def city_ok(cls, v: str) -> str:
        v = (v or "").strip()
        if not v or len(v) > 100:
            raise ValueError("Invalid destination city")
        return v


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: str = Field(default="default", max_length=64)

    @field_validator("message")
    @classmethod
    def message_nonblank(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("message must be a non-empty string")
        return v

    @field_validator("session_id")
    @classmethod
    def session_ok(cls, v: str) -> str:
        v = (v or "default").strip() or "default"
        if len(v) > 64:
            raise ValueError("session_id too long")
        return v


class PlanRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)

    @field_validator("query")
    @classmethod
    def query_nonblank(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("query must be a non-empty string")
        return v


class OptimizeRequest(BaseModel):
    constraints: str = Field(default="", max_length=300)


class TopologyNode(BaseModel):
    id: str
    type: Literal["satellite", "ground"]


class TopologyEdge(BaseModel):
    source: str
    target: str
    weight: float


class TopologyPayload(BaseModel):
    nodes: list[TopologyNode]
    edges: list[TopologyEdge]
    route: list[str]
    dropped: bool


class SimulateResponse(BaseModel):
    status: str
    source: str
    destination: str
    latency_ms: Optional[str] = None
    ai_analysis: Optional[str] = None
    topology: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    ai: bool
    ai_mode: str
    anomaly_monitor: bool
    demo_location: dict[str, Any]
