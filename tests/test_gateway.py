from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from darkfactory_gateway.app import create_app
from darkfactory_gateway.service import GatewayService


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
        self.assertTrue(any(item["id"] == "mock" for item in providers.json()))
        self.assertTrue(any(item["id"] == "structured_output" for item in skills.json()))

    def test_chat_returns_mock_reply(self) -> None:
        response = self.client.post("/api/chat", json=sample_request())
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["provider_id"], "mock")
        self.assertIn("【结论】", body["reply"])

    def test_stream_returns_sse_events(self) -> None:
        with self.client.stream("POST", "/api/chat/stream", json=sample_request()) as response:
            content = "".join(response.iter_text())

        self.assertEqual(response.status_code, 200)
        self.assertIn('"type": "request"', content)
        self.assertIn('"type": "delta"', content)
        self.assertIn('"type": "done"', content)

    def test_cancel_endpoint_marks_request(self) -> None:
        request_id = self.service.request_tracker.create()

        response = self.client.post(f"/api/chat/{request_id}/cancel")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "cancel_requested")


if __name__ == "__main__":
    unittest.main()
