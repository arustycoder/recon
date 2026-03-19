from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from darkfactory.config import load_env, provider_settings_from_env
from darkfactory.models import Project, ProviderSettings, Session
from darkfactory.services import AssistantService


def run_provider(settings: ProviderSettings, user_message: str) -> dict[str, object]:
    service = AssistantService(settings)
    project = Project(
        id=1,
        name="对比测试",
        plant="示例电厂",
        unit="1#机",
        expert_type="热力专家",
        created_at="2026-03-19 00:00:00",
    )
    session = Session(
        id=1,
        project_id=1,
        name="Provider Compare",
        summary="",
        updated_at="2026-03-19 00:00:00",
    )

    started = perf_counter()
    first_chunk_ms = 0
    chunks: list[str] = []
    for chunk in service.stream_reply(
        project=project,
        session=session,
        recent_messages=[],
        user_message=user_message,
        settings=settings,
    ):
        if chunk and first_chunk_ms == 0:
            first_chunk_ms = int((perf_counter() - started) * 1000)
        chunks.append(chunk)
    total_ms = int((perf_counter() - started) * 1000)
    metrics = service.last_response_metrics()
    return {
        "provider": service.provider_name(settings),
        "target": service.target_label(settings),
        "first_chunk_ms": first_chunk_ms,
        "total_ms": total_ms,
        "stream_mode": metrics.stream_mode,
        "prompt_tokens": metrics.prompt_tokens,
        "completion_tokens": metrics.completion_tokens,
        "total_tokens": metrics.total_tokens,
        "reply_preview": "".join(chunks)[:240],
    }


def main() -> int:
    load_env()
    prompt = "请简单分析当前蒸汽不足的可能原因，并给出两条建议。"

    results: list[dict[str, object]] = []
    results.append(run_provider(ProviderSettings(provider="mock"), prompt))

    env_settings = provider_settings_from_env()
    compatible_provider = AssistantService(env_settings).provider_name(env_settings)
    if compatible_provider in {"openai_compatible", "ollama"}:
        results.append(run_provider(env_settings, prompt))

    for result in results:
        print("provider=", result["provider"])
        print("target=", result["target"])
        print("first_chunk_ms=", result["first_chunk_ms"])
        print("total_ms=", result["total_ms"])
        print("stream_mode=", result["stream_mode"])
        print("prompt_tokens=", result["prompt_tokens"])
        print("completion_tokens=", result["completion_tokens"])
        print("total_tokens=", result["total_tokens"])
        print("reply_preview=", result["reply_preview"])
        print("---")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
