from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from darkfactory.models import ProviderSettings
from darkfactory.storage import Storage
from darkfactory_gateway.adapters import (
    GatewayAdapterFactory,
    GatewayProviderAdapter,
    HttpBackendGatewayAdapter,
    MockGatewayAdapter,
    OllamaGatewayAdapter,
    OpenAICompatibleGatewayAdapter,
)
from darkfactory_gateway.app import create_app
from darkfactory_gateway.models import GatewayChatRequest
from darkfactory_gateway.registry import ProviderRecord, ProviderRegistry
from darkfactory_gateway.service import GatewayService
from darkfactory_gateway.skills import SkillRecord, SkillRegistry


def sample_request() -> dict:
    return {
        "project": {
            "id": 1,
            "name": "测试项目",
            "plant": "示例电厂",
            "unit": "1#机",
            "expert_type": "热力专家",
            "created_at": "2026-03-19 00:00:00",
        },
        "session": {
            "id": 1,
            "project_id": 1,
            "name": "默认对话",
            "summary": "",
            "updated_at": "2026-03-19 00:00:00",
        },
        "recent_messages": [],
        "message": "请分析蒸汽不足",
        "client_request_id": "client-001",
        "provider_id": "mock",
        "skill_ids": ["structured_output"],
    }


@dataclass
class FakeAdapter(GatewayProviderAdapter):
    target: str = "fake-target"
    reply_text: str = "fake-reply"
    health_text: str = "fake-health"

    def __post_init__(self) -> None:
        from darkfactory.models import ResponseMetrics

        self._metrics = ResponseMetrics(
            stream_mode="single",
            latency_ms=25,
            first_token_latency_ms=5,
            prompt_tokens=120,
            completion_tokens=80,
            total_tokens=200,
        )

    def reply(self, **kwargs) -> str:
        return "".join(self.stream_reply(**kwargs))

    def stream_reply(self, **kwargs):
        yield self.reply_text

    def health_check(self) -> str:
        return self.health_text

    def target_label(self) -> str:
        return self.target

    def last_result(self):
        from darkfactory_gateway.adapters import GatewayAdapterResult

        return GatewayAdapterResult(target=self.target, metrics=self._metrics)


class FakeAdapterFactory(GatewayAdapterFactory):
    def __init__(self, adapter: FakeAdapter) -> None:
        self.adapter = adapter

    def create(self, settings: ProviderSettings) -> GatewayProviderAdapter:
        return self.adapter


class MappingAdapterFactory(GatewayAdapterFactory):
    def __init__(self, adapters: dict[str, GatewayProviderAdapter]) -> None:
        self.adapters = adapters

    def create(self, settings: ProviderSettings) -> GatewayProviderAdapter:
        key = settings.provider or "mock"
        return self.adapters[key]


@dataclass
class RaisingAdapter(FakeAdapter):
    error_text: str = "adapter failed"

    def stream_reply(self, **kwargs):
        raise RuntimeError(self.error_text)
        yield ""


@dataclass
class CapturingAdapter(FakeAdapter):
    captured: dict[str, str] | None = None

    def stream_reply(self, **kwargs):
        if self.captured is not None:
            self.captured["user_message"] = kwargs["user_message"]
        yield self.reply_text


@dataclass
class ReplyOnlyAdapter(FakeAdapter):
    def reply(self, **kwargs) -> str:
        return "reply-path-result"

    def stream_reply(self, **kwargs):
        raise RuntimeError("stream path should not be used for sync chat")
        yield ""


class GatewayAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = Storage(db_path=Path(self.temp_dir.name) / "gateway.db")
        self.service = GatewayService(storage=self.storage)
        self.client = TestClient(create_app(self.service))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_health_and_registry_endpoints(self) -> None:
        health = self.client.get("/api/health")
        providers = self.client.get("/api/providers")
        skills = self.client.get("/api/skills")

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")
        self.assertGreaterEqual(health.json()["provider_count"], 1)
        self.assertTrue(any(item["id"] == "mock" for item in providers.json()))
        self.assertTrue(any(item["id"] == "structured_output" for item in skills.json()))

    def test_chat_returns_mock_reply(self) -> None:
        response = self.client.post("/api/chat", json=sample_request())
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["provider_id"], "mock")
        self.assertEqual(body["client_request_id"], "client-001")
        self.assertEqual(body["attempted_provider_ids"], ["mock"])
        self.assertEqual(body["target"], "mock")
        self.assertIn("【结论】", body["reply"])

    def test_chat_returns_structured_502_when_provider_fails(self) -> None:
        registry = ProviderRegistry(
            [
                ProviderRecord(
                    id="broken",
                    kind="openai_compatible",
                    label="Broken",
                    settings=ProviderSettings(
                        provider="openai_compatible",
                        openai_base_url="http://broken.invalid/v1",
                        openai_model="broken-model",
                    ),
                    default=True,
                    priority=1,
                )
            ]
        )
        service = GatewayService(
            provider_registry=registry,
            storage=Storage(db_path=Path(self.temp_dir.name) / "chat-errors.db"),
            adapter_factory=MappingAdapterFactory(
                {"openai_compatible": RaisingAdapter(error_text="sync provider failed")}
            ),
        )
        client = TestClient(create_app(service))

        response = client.post("/api/chat", json=sample_request() | {"provider_id": "broken"})

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "sync provider failed")

    def test_sync_chat_uses_adapter_reply_path(self) -> None:
        registry = ProviderRegistry(
            [
                ProviderRecord(
                    id="reply_only",
                    kind="openai_compatible",
                    label="Reply Only",
                    settings=ProviderSettings(
                        provider="openai_compatible",
                        openai_base_url="http://reply.invalid/v1",
                        openai_model="reply-model",
                    ),
                    default=True,
                    priority=1,
                )
            ]
        )
        service = GatewayService(
            provider_registry=registry,
            storage=Storage(db_path=Path(self.temp_dir.name) / "reply-path.db"),
            adapter_factory=MappingAdapterFactory(
                {"openai_compatible": ReplyOnlyAdapter()}
            ),
        )

        response = service.chat(service_request(provider_id="reply_only"))

        self.assertEqual(response.reply, "reply-path-result")

    def test_chat_returns_429_when_provider_is_rate_limited(self) -> None:
        registry = ProviderRegistry(
            [
                ProviderRecord(
                    id="limited",
                    kind="openai_compatible",
                    label="Limited",
                    settings=ProviderSettings(
                        provider="openai_compatible",
                        openai_base_url="http://limited.invalid/v1",
                        openai_model="limited-model",
                    ),
                    default=True,
                    priority=1,
                    cooldown_seconds=60,
                )
            ]
        )
        service = GatewayService(
            provider_registry=registry,
            storage=Storage(db_path=Path(self.temp_dir.name) / "rate-limit.db"),
            adapter_factory=MappingAdapterFactory(
                {"openai_compatible": RaisingAdapter(error_text="429 Too Many Requests")}
            ),
        )
        client = TestClient(create_app(service))

        response = client.post("/api/chat", json=sample_request() | {"provider_id": "limited"})

        self.assertEqual(response.status_code, 429)
        self.assertIn("429 Too Many Requests", response.json()["detail"])
        health = service.provider_health("limited")
        self.assertEqual(health.status, "rate_limited")
        self.assertIn("rate limited", health.detail)

    def test_stream_returns_sse_events(self) -> None:
        with self.client.stream("POST", "/api/chat/stream", json=sample_request()) as response:
            content = "".join(response.iter_text())

        self.assertEqual(response.status_code, 200)
        self.assertIn('"type": "request"', content)
        self.assertIn('"type": "delta"', content)
        self.assertIn('"type": "done"', content)

    def test_stream_returns_error_and_done_events_on_provider_failure(self) -> None:
        registry = ProviderRegistry(
            [
                ProviderRecord(
                    id="broken",
                    kind="openai_compatible",
                    label="Broken",
                    settings=ProviderSettings(
                        provider="openai_compatible",
                        openai_base_url="http://broken.invalid/v1",
                        openai_model="broken-model",
                    ),
                    default=True,
                    priority=1,
                )
            ]
        )
        service = GatewayService(
            provider_registry=registry,
            storage=Storage(db_path=Path(self.temp_dir.name) / "stream-errors.db"),
            adapter_factory=MappingAdapterFactory(
                {"openai_compatible": RaisingAdapter(error_text="stream provider failed")}
            ),
        )
        client = TestClient(create_app(service))

        with client.stream(
            "POST",
            "/api/chat/stream",
            json=sample_request() | {"provider_id": "broken"},
        ) as response:
            content = "".join(response.iter_text())

        self.assertEqual(response.status_code, 200)
        self.assertIn('"type": "request"', content)
        self.assertIn('"type": "error"', content)
        self.assertIn('"type": "done"', content)
        self.assertIn('"status": "error"', content)
        self.assertIn("stream provider failed", content)

    def test_provider_health_endpoint(self) -> None:
        response = self.client.get("/api/providers/mock/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    def test_provider_reset_endpoint(self) -> None:
        response = self.client.post("/api/providers/mock/reset")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "reset")

    def test_request_endpoints_return_completed_request(self) -> None:
        chat = self.client.post("/api/chat", json=sample_request())
        request_id = chat.json()["request_id"]

        listing = self.client.get("/api/requests")
        detail = self.client.get(f"/api/requests/{request_id}")

        self.assertEqual(listing.status_code, 200)
        self.assertTrue(any(item["request_id"] == request_id for item in listing.json()))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["status"], "completed")
        self.assertEqual(detail.json()["phase"], "completed")
        self.assertEqual(detail.json()["client_request_id"], "client-001")
        self.assertGreaterEqual(detail.json()["latency_ms"], 0)

    def test_request_listing_supports_filters_and_summary(self) -> None:
        self.client.post("/api/chat", json=sample_request())
        second = sample_request()
        second["provider_id"] = "mock"
        second["client_request_id"] = "client-002"
        self.client.post("/api/chat", json=second)

        listing = self.client.get("/api/requests", params={"provider_id": "mock", "status": "completed"})
        summary = self.client.get("/api/requests/summary", params={"provider_id": "mock"})

        self.assertEqual(listing.status_code, 200)
        self.assertGreaterEqual(len(listing.json()), 2)
        self.assertEqual(summary.status_code, 200)
        self.assertGreaterEqual(summary.json()["request_count"], 2)
        self.assertEqual(summary.json()["error_count"], 0)
        self.assertTrue(any(item["key"] == "mock" for item in summary.json()["by_provider"]))

    def test_cancel_endpoint_marks_request(self) -> None:
        request_id = self.service.request_tracker.create()

        response = self.client.post(f"/api/chat/{request_id}/cancel")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "cancel_requested")

    def test_fallback_strategy_uses_second_provider(self) -> None:
        registry = ProviderRegistry(
            [
                ProviderRecord(
                    id="broken",
                    kind="openai_compatible",
                    label="Broken",
                    settings=ProviderSettings(
                        provider="openai_compatible",
                        openai_base_url="http://broken.invalid/v1",
                        openai_model="broken-model",
                    ),
                    default=True,
                    priority=1,
                ),
                ProviderRecord(
                    id="mock",
                    kind="mock",
                    label="Mock",
                    settings=ProviderSettings(provider="mock"),
                    priority=2,
                ),
            ]
        )
        service = GatewayService(
            provider_registry=registry,
            storage=Storage(db_path=Path(self.temp_dir.name) / "fallback.db"),
            adapter_factory=MappingAdapterFactory(
                {
                    "openai_compatible": RaisingAdapter(error_text="broken provider"),
                    "mock": FakeAdapter(reply_text="fallback reply"),
                }
            ),
        )

        response = service.chat(
            service_request(
                provider_id=None,
                provider_strategy="fallback",
            )
        )

        self.assertEqual(response.provider_id, "mock")
        self.assertEqual(response.attempted_provider_ids, ["broken", "mock"])
        self.assertEqual(response.reply, "fallback reply")

    def test_skill_template_injects_arguments(self) -> None:
        registry = SkillRegistry(
            [
                SkillRecord(
                    id="custom",
                    label="Custom",
                    description="Custom skill",
                    template="输出风格为 {style}，项目是 {project_name}。",
                    parameters={"style": "审慎"},
                )
            ]
        )
        captured: dict[str, str] = {}
        service = GatewayService(
            skill_registry=registry,
            storage=Storage(db_path=Path(self.temp_dir.name) / "skills.db"),
            adapter_factory=FakeAdapterFactory(CapturingAdapter(reply_text="ok", captured=captured)),
        )
        service.chat(
            service_request(
                skill_ids=["custom"],
                skill_mode="request_only",
                skill_arguments={"custom": {"style": "激进"}},
            )
        )

        user_message = captured["user_message"]
        self.assertIn("[custom] 输出风格为 激进，项目是 测试项目。", user_message)
        self.assertIn("[User Message]", user_message)

    def test_post_processing_skill_rewrites_reply(self) -> None:
        registry = SkillRegistry(
            [
                SkillRecord(
                    id="final_wrap",
                    label="Final Wrap",
                    description="Wrap final reply",
                    phase="post_processing",
                    template="【最终输出】\n{reply}\n\n【备注】\n已执行后处理。",
                )
            ]
        )
        service = GatewayService(
            skill_registry=registry,
            storage=Storage(db_path=Path(self.temp_dir.name) / "post.db"),
            adapter_factory=FakeAdapterFactory(FakeAdapter(reply_text="原始回复")),
        )

        response = service.chat(
            service_request(
                skill_ids=["final_wrap"],
                skill_mode="request_only",
            )
        )

        self.assertIn("【最终输出】", response.reply)
        self.assertIn("原始回复", response.reply)

    def test_provider_cooldown_blocks_immediate_retry(self) -> None:
        registry = ProviderRegistry(
            [
                ProviderRecord(
                    id="fragile",
                    kind="openai_compatible",
                    label="Fragile",
                    settings=ProviderSettings(
                        provider="openai_compatible",
                        openai_base_url="http://broken.invalid/v1",
                        openai_model="broken-model",
                    ),
                    default=True,
                    priority=1,
                    cooldown_seconds=60,
                    max_consecutive_failures=1,
                )
            ]
        )
        service = GatewayService(
            provider_registry=registry,
            storage=Storage(db_path=Path(self.temp_dir.name) / "cooldown.db"),
            adapter_factory=MappingAdapterFactory(
                {"openai_compatible": RaisingAdapter(error_text="provider failed")}
            ),
        )

        with self.assertRaises(RuntimeError):
            service.chat(service_request(provider_id="fragile", provider_strategy="default"))

        with self.assertRaises(RuntimeError) as second_error:
            service.chat(service_request(provider_id="fragile", provider_strategy="default"))

        self.assertIn("cooling down", str(second_error.exception))
        health = service.provider_health("fragile")
        self.assertEqual(health.status, "cooldown")
        self.assertIn("cooling down", health.detail)

    def test_provider_reset_endpoint_clears_cooldown(self) -> None:
        registry = ProviderRegistry(
            [
                ProviderRecord(
                    id="fragile",
                    kind="mock",
                    label="Fragile",
                    settings=ProviderSettings(provider="mock"),
                    default=True,
                    cooldown_seconds=60,
                    max_consecutive_failures=1,
                )
            ]
        )
        service = GatewayService(
            provider_registry=registry,
            storage=Storage(db_path=Path(self.temp_dir.name) / "reset.db"),
        )
        service._record_provider_failure("fragile", registry.get("fragile"))

        before = service.provider_health("fragile")
        reset = service.reset_provider("fragile")
        after = service.provider_health("fragile")

        self.assertEqual(before.status, "cooldown")
        self.assertEqual(reset.status, "reset")
        self.assertEqual(after.status, "healthy")

    def test_rate_limited_provider_enters_immediate_cooldown_without_fallback(self) -> None:
        registry = ProviderRegistry(
            [
                ProviderRecord(
                    id="limited",
                    kind="openai_compatible",
                    label="Limited",
                    settings=ProviderSettings(
                        provider="openai_compatible",
                        openai_base_url="http://limited.invalid/v1",
                        openai_model="limited-model",
                    ),
                    default=True,
                    priority=1,
                    cooldown_seconds=60,
                    max_consecutive_failures=3,
                ),
                ProviderRecord(
                    id="mock",
                    kind="mock",
                    label="Mock",
                    settings=ProviderSettings(provider="mock"),
                    priority=2,
                ),
            ]
        )
        service = GatewayService(
            provider_registry=registry,
            storage=Storage(db_path=Path(self.temp_dir.name) / "rate-limit-cooldown.db"),
            adapter_factory=MappingAdapterFactory(
                {
                    "openai_compatible": RaisingAdapter(error_text="429 Too Many Requests"),
                    "mock": FakeAdapter(reply_text="should not run"),
                }
            ),
        )

        with self.assertRaises(RuntimeError) as error:
            service.chat(service_request(provider_id="limited", provider_strategy="default"))

        self.assertIn("429 Too Many Requests", str(error.exception))
        health = service.provider_health("limited")
        self.assertEqual(health.status, "rate_limited")
        self.assertIn("rate limited", health.detail)

    def test_stream_disconnect_enters_short_cooldown(self) -> None:
        registry = ProviderRegistry(
            [
                ProviderRecord(
                    id="unstable",
                    kind="openai_compatible",
                    label="Unstable",
                    settings=ProviderSettings(
                        provider="openai_compatible",
                        openai_base_url="http://unstable.invalid/v1",
                        openai_model="unstable-model",
                    ),
                    default=True,
                    cooldown_seconds=60,
                    max_consecutive_failures=3,
                )
            ]
        )
        service = GatewayService(
            provider_registry=registry,
            storage=Storage(db_path=Path(self.temp_dir.name) / "unstable.db"),
            adapter_factory=MappingAdapterFactory(
                {"openai_compatible": RaisingAdapter(error_text="Provider streaming connection closed before the response completed.")}
            ),
        )

        with self.assertRaises(RuntimeError):
            service.chat(service_request(provider_id="unstable", provider_strategy="default"))

        health = service.provider_health("unstable")
        self.assertEqual(health.status, "cooldown")
        self.assertIn("stream was interrupted", health.detail)
        self.assertGreater(health.cooldown_remaining_seconds, 0)

    def test_provider_health_reports_misconfigured(self) -> None:
        registry = ProviderRegistry(
            [
                ProviderRecord(
                    id="badcfg",
                    kind="openai_compatible",
                    label="Bad Config",
                    settings=ProviderSettings(provider="openai_compatible"),
                    default=True,
                )
            ]
        )
        service = GatewayService(
            provider_registry=registry,
            storage=Storage(db_path=Path(self.temp_dir.name) / "health.db"),
        )

        health = service.provider_health("badcfg")

        self.assertEqual(health.status, "misconfigured")

    def test_service_supports_custom_adapter_factory(self) -> None:
        adapter = FakeAdapter(reply_text="adapter-reply", target="adapter-target")
        registry = ProviderRegistry(
            [
                ProviderRecord(
                    id="mock",
                    kind="mock",
                    label="Mock",
                    settings=ProviderSettings(provider="mock"),
                    default=True,
                    prompt_cost_per_1k=0.001,
                    completion_cost_per_1k=0.002,
                )
            ]
        )
        service = GatewayService(
            provider_registry=registry,
            storage=Storage(db_path=Path(self.temp_dir.name) / "adapter.db"),
            adapter_factory=FakeAdapterFactory(adapter),
        )

        response = service.chat(service_request())
        request_info = service.get_request(response.request_id)

        self.assertEqual(response.reply, "adapter-reply")
        self.assertEqual(response.target, "adapter-target")
        self.assertEqual(response.total_tokens, 200)
        self.assertAlmostEqual(response.estimated_cost_usd, 0.00028)
        self.assertEqual(request_info.target, "adapter-target")
        self.assertEqual(request_info.total_tokens, 200)

    def test_adapter_factory_returns_provider_specific_adapters(self) -> None:
        factory = GatewayAdapterFactory()

        self.assertIsInstance(
            factory.create(ProviderSettings(provider="mock")),
            MockGatewayAdapter,
        )
        self.assertIsInstance(
            factory.create(
                ProviderSettings(
                    provider="ollama",
                    ollama_model="qwen2.5:latest",
                )
            ),
            OllamaGatewayAdapter,
        )
        self.assertIsInstance(
            factory.create(
                ProviderSettings(
                    provider="openai_compatible",
                    openai_base_url="http://localhost:8000/v1",
                    openai_model="demo",
                )
            ),
            OpenAICompatibleGatewayAdapter,
        )
        self.assertIsInstance(
            factory.create(
                ProviderSettings(
                    provider="http_backend",
                    api_url="http://localhost:8000/api/chat",
                )
            ),
            HttpBackendGatewayAdapter,
        )


def service_request(**updates):
    payload = sample_request()
    payload.update(updates)
    return GatewayChatRequest(**payload)


if __name__ == "__main__":
    unittest.main()
