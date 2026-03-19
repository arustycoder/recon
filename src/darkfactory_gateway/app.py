from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from darkfactory.config import load_env

from .models import (
    GatewayCancelResponse,
    GatewayChatRequest,
    GatewayChatResponse,
    GatewayHealthResponse,
    GatewayProviderInfo,
    GatewaySkillInfo,
)
from .service import GatewayService


def create_app(service: GatewayService | None = None) -> FastAPI:
    load_env()
    gateway = service or GatewayService()
    app = FastAPI(title="DarkFactory Gateway", version="0.1.0")

    @app.get("/api/health", response_model=GatewayHealthResponse)
    def health() -> GatewayHealthResponse:
        return GatewayHealthResponse(**gateway.health())

    @app.get("/api/providers", response_model=list[GatewayProviderInfo])
    def providers() -> list[GatewayProviderInfo]:
        return gateway.list_providers()

    @app.get("/api/skills", response_model=list[GatewaySkillInfo])
    def skills() -> list[GatewaySkillInfo]:
        return gateway.list_skills()

    @app.post("/api/chat", response_model=GatewayChatResponse)
    def chat(request: GatewayChatRequest) -> GatewayChatResponse:
        return gateway.chat(request)

    @app.post("/api/chat/stream")
    def stream(request: GatewayChatRequest) -> StreamingResponse:
        return StreamingResponse(
            gateway.stream_chat(request),
            media_type="text/event-stream",
        )

    @app.post("/api/chat/{request_id}/cancel", response_model=GatewayCancelResponse)
    def cancel(request_id: str) -> GatewayCancelResponse:
        return GatewayCancelResponse(
            request_id=request_id,
            status=gateway.cancel(request_id),
        )

    return app


app = create_app()
