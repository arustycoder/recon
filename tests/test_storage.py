from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from darkfactory.storage import Storage
from darkfactory.models import ProviderSettings


class StorageTests(unittest.TestCase):
    def test_storage_project_session_and_message_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "darkfactory.db"
            storage = Storage(db_path=db_path)

            project_id = storage.create_project("测试项目", plant="测试电厂", unit="2#机")
            session_id = storage.create_session(project_id, "测试对话")
            storage.add_message(session_id, "user", "你好")
            storage.add_message(session_id, "assistant", "已收到")

            projects = storage.list_projects()
            sessions = storage.list_sessions(project_id)
            messages = storage.list_messages(session_id)

            self.assertEqual(len(projects), 1)
            self.assertEqual(projects[0].name, "测试项目")
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].name, "测试对话")
            self.assertEqual([message.role for message in messages], ["user", "assistant"])

    def test_message_attachment_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "darkfactory.db"
            storage = Storage(db_path=db_path)

            project_id = storage.create_project("测试项目")
            session_id = storage.create_session(project_id, "测试对话")
            attachment_id = storage.upsert_attachment(
                path=str(Path(temp_dir) / "report.csv"),
                name="report.csv",
                media_type="csv",
                size_bytes=128,
                excerpt="a,b\n1,2",
            )
            storage.add_message(
                session_id,
                "user",
                "请分析附件",
                attachment_ids=[attachment_id],
            )

            messages = storage.list_messages(session_id)
            self.assertEqual(len(messages), 1)
            self.assertEqual(len(messages[0].attachments), 1)
            self.assertEqual(messages[0].attachments[0].name, "report.csv")

    def test_app_state_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "darkfactory.db"
            storage = Storage(db_path=db_path)

            self.assertIsNone(storage.get_state("last_session_id"))
            storage.set_state("last_session_id", "42")

            self.assertEqual(storage.get_state("last_session_id"), "42")

    def test_provider_settings_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "darkfactory.db"
            storage = Storage(db_path=db_path)

            settings = ProviderSettings(
                provider="openai_compatible",
                openai_base_url="http://localhost:8000/v1",
                openai_api_key="secret",
                openai_model="demo-model",
                request_timeout_seconds=45,
                api_stream_url="http://localhost:8000/api/chat/stream",
                api_cancel_url_template="http://localhost:8000/api/chat/{request_id}/cancel",
            )
            storage.save_provider_settings(settings)
            loaded = storage.get_provider_settings()

            self.assertEqual(loaded.provider, "openai_compatible")
            self.assertEqual(loaded.openai_base_url, "http://localhost:8000/v1")
            self.assertEqual(loaded.openai_model, "demo-model")
            self.assertEqual(loaded.request_timeout_seconds, 45)
            self.assertEqual(loaded.api_stream_url, "http://localhost:8000/api/chat/stream")
            self.assertIn("{request_id}", loaded.api_cancel_url_template)

    def test_request_log_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "darkfactory.db"
            storage = Storage(db_path=db_path)

            project_id = storage.create_project("测试项目")
            session_id = storage.create_session(project_id, "测试对话")
            storage.add_request_log(
                session_id=session_id,
                provider="mock",
                model="mock",
                status="success",
                error_type="",
                stream_mode="stream",
                latency_ms=120,
                first_token_latency_ms=40,
                prompt_tokens=12,
                completion_tokens=24,
                total_tokens=36,
                detail="",
            )

            logs = storage.list_request_logs()
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].session_id, session_id)
            self.assertEqual(logs[0].status, "success")
            self.assertEqual(logs[0].error_type, "")
            self.assertEqual(logs[0].stream_mode, "stream")
            self.assertEqual(logs[0].total_tokens, 36)

    def test_request_log_filters_and_clear(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "darkfactory.db"
            storage = Storage(db_path=db_path)

            project_id = storage.create_project("测试项目")
            session_id = storage.create_session(project_id, "测试对话")
            storage.add_request_log(
                session_id=session_id,
                provider="mock",
                model="mock",
                status="success",
                error_type="",
                latency_ms=10,
            )
            storage.add_request_log(
                session_id=session_id,
                provider="openai_compatible",
                model="demo",
                status="error",
                error_type="rate_limited",
                latency_ms=20,
            )

            self.assertEqual(len(storage.list_request_logs(provider="mock")), 1)
            self.assertEqual(len(storage.list_request_logs(status="error")), 1)
            self.assertEqual(len(storage.list_request_logs(error_type="rate_limited")), 1)

            storage.clear_request_logs(provider="mock")
            logs = storage.list_request_logs()
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].provider, "openai_compatible")
            self.assertEqual(logs[0].error_type, "rate_limited")

            storage.clear_request_logs(error_type="rate_limited")
            self.assertEqual(len(storage.list_request_logs()), 0)

    def test_gateway_request_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "darkfactory.db"
            storage = Storage(db_path=db_path)

            project_id = storage.create_project("测试项目")
            session_id = storage.create_session(project_id, "测试对话")
            storage.save_gateway_request(
                request_id="req_001",
                client_request_id="client-001",
                session_id=session_id,
                status="running",
                phase="model_execution",
                provider_id="mock",
                target="mock",
                stream_mode="stream",
                latency_ms=120,
                first_token_latency_ms=30,
                prompt_tokens=40,
                completion_tokens=50,
                total_tokens=90,
                estimated_cost_usd=0.0123,
                attempted_provider_ids=["mock"],
                skill_ids=["structured_output"],
                error_type="",
                error_detail="",
            )
            storage.save_gateway_request(
                request_id="req_001",
                client_request_id="client-001",
                session_id=session_id,
                status="completed",
                phase="completed",
                provider_id="mock",
                target="mock",
                stream_mode="stream",
                latency_ms=120,
                first_token_latency_ms=30,
                prompt_tokens=40,
                completion_tokens=50,
                total_tokens=90,
                estimated_cost_usd=0.0123,
                attempted_provider_ids=["mock"],
                skill_ids=["structured_output"],
                error_type="",
                error_detail="",
            )

            record = storage.get_gateway_request("req_001")
            records = storage.list_gateway_requests()

            self.assertIsNotNone(record)
            self.assertEqual(record.status, "completed")
            self.assertEqual(record.phase, "completed")
            self.assertEqual(record.latency_ms, 120)
            self.assertEqual(record.total_tokens, 90)
            self.assertEqual(record.error_type, "")
            self.assertEqual(len(records), 1)

    def test_gateway_request_filters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "darkfactory.db"
            storage = Storage(db_path=db_path)

            storage.save_gateway_request(
                request_id="req_a",
                client_request_id="client-a",
                status="completed",
                phase="completed",
                provider_id="mock",
                total_tokens=10,
            )
            storage.save_gateway_request(
                request_id="req_b",
                client_request_id="client-b",
                status="error",
                phase="error",
                provider_id="openai",
                error_type="rate_limited",
                total_tokens=20,
            )

            self.assertEqual(len(storage.filter_gateway_requests(provider_id="mock")), 1)
            self.assertEqual(len(storage.filter_gateway_requests(status="error")), 1)
            self.assertEqual(len(storage.filter_gateway_requests(phase="completed")), 1)
            self.assertEqual(storage.get_gateway_request("req_b").error_type, "rate_limited")


if __name__ == "__main__":
    unittest.main()
