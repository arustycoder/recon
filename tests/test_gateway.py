from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from darkfactory.models import ProviderSettings
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


class GatewayAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = GatewayService()
        self.client = TestClient(create_app(self.service))

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
        self.assertIn("【结论】", body["reply"])

    def test_stream_returns_sse_events(self) -> None:
        with self.client.stream("POST", "/api/chat/stream", json=sample_request()) as response:
            content = "".join(response.iter_text())

        self.assertEqual(response.status_code, 200)
        self.assertIn('"type": "request"', content)
        self.assertIn('"type": "delta"', content)
        self.assertIn('"type": "done"', content)

    def test_provider_health_endpoint(self) -> None:
        response = self.client.get("/api/providers/mock/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_request_endpoints_return_completed_request(self) -> None:
        chat = self.client.post("/api/chat", json=sample_request())
        request_id = chat.json()["request_id"]

        listing = self.client.get("/api/requests")
        detail = self.client.get(f"/api/requests/{request_id}")

        self.assertEqual(listing.status_code, 200)
        self.assertTrue(any(item["request_id"] == request_id for item in listing.json()))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["status"], "completed")
        self.assertEqual(detail.json()["client_request_id"], "client-001")

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
        service = GatewayService(provider_registry=registry)

        def fake_stream_reply(self, **kwargs):
            settings = kwargs["settings"]
            if settings.provider == "openai_compatible":
                raise RuntimeError("broken provider")
            yield "fallback reply"

        with patch("darkfactory_gateway.service.AssistantService.stream_reply", fake_stream_reply):
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
        service = GatewayService(skill_registry=registry)
        captured: dict[str, str] = {}

        def fake_stream_reply(self, **kwargs):
            captured["user_message"] = kwargs["user_message"]
            yield "ok"

        with patch("darkfactory_gateway.service.AssistantService.stream_reply", fake_stream_reply):
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


def service_request(**updates):
    payload = sample_request()
    payload.update(updates)
    return GatewayChatRequest(**payload)


if __name__ == "__main__":
    unittest.main()
