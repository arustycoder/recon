from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
import json

from .config import DEFAULT_PROVIDER_KEYS
from .models import (
    GatewayRequestRecord,
    Message,
    Project,
    ProviderSettings,
    RequestLog,
    Session,
)


DEFAULT_DB_PATH = Path.home() / ".darkfactory" / "darkfactory.db"


class Storage:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    plant TEXT NOT NULL DEFAULT '',
                    unit TEXT NOT NULL DEFAULT '',
                    expert_type TEXT NOT NULL DEFAULT '热力专家',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS request_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    error_type TEXT NOT NULL DEFAULT '',
                    stream_mode TEXT NOT NULL DEFAULT '',
                    latency_ms INTEGER NOT NULL DEFAULT 0,
                    first_token_latency_ms INTEGER NOT NULL DEFAULT 0,
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    detail TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS gateway_requests (
                    request_id TEXT PRIMARY KEY,
                    client_request_id TEXT NOT NULL DEFAULT '',
                    session_id INTEGER,
                    status TEXT NOT NULL,
                    phase TEXT NOT NULL DEFAULT '',
                    provider_id TEXT NOT NULL DEFAULT '',
                    target TEXT NOT NULL DEFAULT '',
                    stream_mode TEXT NOT NULL DEFAULT '',
                    latency_ms INTEGER NOT NULL DEFAULT 0,
                    first_token_latency_ms INTEGER NOT NULL DEFAULT 0,
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    estimated_cost_usd REAL NOT NULL DEFAULT 0,
                    attempted_provider_ids TEXT NOT NULL DEFAULT '[]',
                    skill_ids TEXT NOT NULL DEFAULT '[]',
                    error_type TEXT NOT NULL DEFAULT '',
                    error_detail TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE SET NULL
                );
                """
            )
            self._ensure_request_log_columns(connection)
            self._ensure_gateway_request_columns(connection)

    def _ensure_request_log_columns(self, connection: sqlite3.Connection) -> None:
        existing = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(request_logs)").fetchall()
        }
        required_columns = {
            "error_type": "TEXT NOT NULL DEFAULT ''",
            "stream_mode": "TEXT NOT NULL DEFAULT ''",
            "first_token_latency_ms": "INTEGER NOT NULL DEFAULT 0",
            "prompt_tokens": "INTEGER NOT NULL DEFAULT 0",
            "completion_tokens": "INTEGER NOT NULL DEFAULT 0",
            "total_tokens": "INTEGER NOT NULL DEFAULT 0",
        }
        for name, spec in required_columns.items():
            if name in existing:
                continue
            connection.execute(f"ALTER TABLE request_logs ADD COLUMN {name} {spec}")

    def _ensure_gateway_request_columns(self, connection: sqlite3.Connection) -> None:
        existing = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(gateway_requests)").fetchall()
        }
        required_columns = {
            "target": "TEXT NOT NULL DEFAULT ''",
            "stream_mode": "TEXT NOT NULL DEFAULT ''",
            "latency_ms": "INTEGER NOT NULL DEFAULT 0",
            "first_token_latency_ms": "INTEGER NOT NULL DEFAULT 0",
            "prompt_tokens": "INTEGER NOT NULL DEFAULT 0",
            "completion_tokens": "INTEGER NOT NULL DEFAULT 0",
            "total_tokens": "INTEGER NOT NULL DEFAULT 0",
            "estimated_cost_usd": "REAL NOT NULL DEFAULT 0",
            "error_type": "TEXT NOT NULL DEFAULT ''",
        }
        for name, spec in required_columns.items():
            if name in existing:
                continue
            connection.execute(f"ALTER TABLE gateway_requests ADD COLUMN {name} {spec}")

    def bootstrap(self) -> None:
        if self.list_projects():
            return

        project_id = self.create_project(
            name="1#机运行优化",
            plant="示例电厂",
            unit="1#机",
            expert_type="热力专家",
        )
        session_id = self.create_session(project_id, "蒸汽不足分析")
        self.add_message(
            session_id,
            "assistant",
            (
                "【结论】\n欢迎使用 DarkFactory 第一版。\n\n"
                "【原因分析】\n1. 当前为本地示例数据模式\n"
                "2. 尚未接入真实机组数据\n\n"
                "【优化建议】\n1. 先体验左侧项目与会话切换\n"
                "2. 使用下方快捷按钮验证对话流\n\n"
                "【影响评估】\n当前版本已覆盖项目树、会话、持久化与基础对话。"
            ),
        )

    def list_projects(self) -> list[Project]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, name, plant, unit, expert_type, created_at
                FROM projects
                ORDER BY created_at ASC, id ASC
                """
            ).fetchall()
        return [Project(**dict(row)) for row in rows]

    def create_project(
        self,
        name: str,
        plant: str = "",
        unit: str = "",
        expert_type: str = "热力专家",
    ) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO projects (name, plant, unit, expert_type)
                VALUES (?, ?, ?, ?)
                """,
                (name, plant, unit, expert_type),
            )
            return int(cursor.lastrowid)

    def rename_project(self, project_id: int, name: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE projects SET name = ? WHERE id = ?",
                (name, project_id),
            )

    def update_project(
        self,
        project_id: int,
        *,
        name: str,
        plant: str,
        unit: str,
        expert_type: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE projects
                SET name = ?, plant = ?, unit = ?, expert_type = ?
                WHERE id = ?
                """,
                (name, plant, unit, expert_type, project_id),
            )

    def delete_project(self, project_id: int) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    def get_project(self, project_id: int) -> Project | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, name, plant, unit, expert_type, created_at
                FROM projects
                WHERE id = ?
                """,
                (project_id,),
            ).fetchone()
        return Project(**dict(row)) if row else None

    def list_sessions(self, project_id: int) -> list[Session]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, project_id, name, summary, updated_at
                FROM sessions
                WHERE project_id = ?
                ORDER BY updated_at DESC, id DESC
                """,
                (project_id,),
            ).fetchall()
        return [Session(**dict(row)) for row in rows]

    def create_session(self, project_id: int, name: str) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO sessions (project_id, name)
                VALUES (?, ?)
                """,
                (project_id, name),
            )
            return int(cursor.lastrowid)

    def rename_session(self, session_id: int, name: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE sessions
                SET name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (name, session_id),
            )

    def update_session_metadata(
        self,
        session_id: int,
        *,
        name: str | None = None,
        summary: str | None = None,
    ) -> None:
        fields: list[str] = []
        values: list[str | int] = []
        if name is not None:
            fields.append("name = ?")
            values.append(name)
        if summary is not None:
            fields.append("summary = ?")
            values.append(summary)
        if not fields:
            return

        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(session_id)
        with self.connect() as connection:
            connection.execute(
                f"""
                UPDATE sessions
                SET {", ".join(fields)}
                WHERE id = ?
                """,
                tuple(values),
            )

    def delete_session(self, session_id: int) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    def get_session(self, session_id: int) -> Session | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, project_id, name, summary, updated_at
                FROM sessions
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()
        return Session(**dict(row)) if row else None

    def list_messages(self, session_id: int) -> list[Message]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, session_id, role, content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()
        return [Message(**dict(row)) for row in rows]

    def add_message(self, session_id: int, role: str, content: str) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO messages (session_id, role, content)
                VALUES (?, ?, ?)
                """,
                (session_id, role, content),
            )
            connection.execute(
                """
                UPDATE sessions
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (session_id,),
            )
            return int(cursor.lastrowid)

    def get_state(self, key: str) -> str | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM app_state WHERE key = ?",
                (key,),
            ).fetchone()
        return str(row["value"]) if row else None

    def set_state(self, key: str, value: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO app_state (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def get_provider_settings(self, defaults: ProviderSettings | None = None) -> ProviderSettings:
        base = defaults or ProviderSettings()
        values = {key: getattr(base, key) for key in DEFAULT_PROVIDER_KEYS}
        for key in DEFAULT_PROVIDER_KEYS:
            stored = self.get_state(f"provider.{key}")
            if stored is None:
                continue
            if key == "request_timeout_seconds":
                try:
                    values[key] = max(5, min(int(stored), 300))
                except ValueError:
                    values[key] = base.request_timeout_seconds
                continue
            values[key] = stored
        return ProviderSettings(**values)

    def save_provider_settings(self, settings: ProviderSettings) -> None:
        for key in DEFAULT_PROVIDER_KEYS:
            value = getattr(settings, key)
            self.set_state(f"provider.{key}", str(value))

    def add_request_log(
        self,
        *,
        session_id: int | None,
        provider: str,
        model: str,
        status: str,
        error_type: str = "",
        stream_mode: str = "",
        latency_ms: int,
        first_token_latency_ms: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        detail: str = "",
    ) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO request_logs (
                    session_id,
                    provider,
                    model,
                    status,
                    error_type,
                    stream_mode,
                    latency_ms,
                    first_token_latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    detail
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    provider,
                    model,
                    status,
                    error_type,
                    stream_mode,
                    latency_ms,
                    first_token_latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    detail,
                ),
            )
            return int(cursor.lastrowid)

    def list_request_logs(
        self,
        limit: int = 100,
        *,
        provider: str = "",
        status: str = "",
    ) -> list[RequestLog]:
        where_clauses: list[str] = []
        values: list[str | int] = []
        if provider:
            where_clauses.append("provider = ?")
            values.append(provider)
        if status:
            where_clauses.append("status = ?")
            values.append(status)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        values.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    session_id,
                    provider,
                    model,
                    status,
                    error_type,
                    stream_mode,
                    latency_ms,
                    first_token_latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    detail,
                    created_at
                FROM request_logs
                {where_sql}
                ORDER BY id DESC
                LIMIT ?
                """,
                tuple(values),
            ).fetchall()
        return [RequestLog(**dict(row)) for row in rows]

    def clear_request_logs(self, *, provider: str = "", status: str = "") -> None:
        where_clauses: list[str] = []
        values: list[str] = []
        if provider:
            where_clauses.append("provider = ?")
            values.append(provider)
        if status:
            where_clauses.append("status = ?")
            values.append(status)

        sql = "DELETE FROM request_logs"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        with self.connect() as connection:
            connection.execute(sql, tuple(values))

    def save_gateway_request(
        self,
        *,
        request_id: str,
        client_request_id: str = "",
        session_id: int | None = None,
        status: str,
        phase: str = "",
        provider_id: str = "",
        target: str = "",
        stream_mode: str = "",
        latency_ms: int = 0,
        first_token_latency_ms: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
        attempted_provider_ids: list[str] | None = None,
        skill_ids: list[str] | None = None,
        error_type: str = "",
        error_detail: str = "",
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO gateway_requests (
                    request_id,
                    client_request_id,
                    session_id,
                    status,
                    phase,
                    provider_id,
                    target,
                    stream_mode,
                    latency_ms,
                    first_token_latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    estimated_cost_usd,
                    attempted_provider_ids,
                    skill_ids,
                    error_type,
                    error_detail
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(request_id) DO UPDATE SET
                    client_request_id = excluded.client_request_id,
                    session_id = excluded.session_id,
                    status = excluded.status,
                    phase = excluded.phase,
                    provider_id = excluded.provider_id,
                    target = excluded.target,
                    stream_mode = excluded.stream_mode,
                    latency_ms = excluded.latency_ms,
                    first_token_latency_ms = excluded.first_token_latency_ms,
                    prompt_tokens = excluded.prompt_tokens,
                    completion_tokens = excluded.completion_tokens,
                    total_tokens = excluded.total_tokens,
                    estimated_cost_usd = excluded.estimated_cost_usd,
                    attempted_provider_ids = excluded.attempted_provider_ids,
                    skill_ids = excluded.skill_ids,
                    error_type = excluded.error_type,
                    error_detail = excluded.error_detail,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    request_id,
                    client_request_id,
                    session_id,
                    status,
                    phase,
                    provider_id,
                    target,
                    stream_mode,
                    latency_ms,
                    first_token_latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    estimated_cost_usd,
                    json.dumps(attempted_provider_ids or [], ensure_ascii=False),
                    json.dumps(skill_ids or [], ensure_ascii=False),
                    error_type,
                    error_detail,
                ),
            )

    def list_gateway_requests(self, limit: int = 100) -> list[GatewayRequestRecord]:
        return self.filter_gateway_requests(limit=limit)

    def filter_gateway_requests(
        self,
        limit: int = 100,
        *,
        provider_id: str = "",
        status: str = "",
        phase: str = "",
        since_minutes: int = 0,
    ) -> list[GatewayRequestRecord]:
        where_clauses: list[str] = []
        values: list[str | int] = []
        if provider_id:
            where_clauses.append("provider_id = ?")
            values.append(provider_id)
        if status:
            where_clauses.append("status = ?")
            values.append(status)
        if phase:
            where_clauses.append("phase = ?")
            values.append(phase)
        if since_minutes > 0:
            where_clauses.append("updated_at >= datetime('now', ?)")
            values.append(f"-{int(since_minutes)} minutes")

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        values.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    request_id,
                    client_request_id,
                    session_id,
                    status,
                    phase,
                    provider_id,
                    target,
                    stream_mode,
                    latency_ms,
                    first_token_latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    estimated_cost_usd,
                    attempted_provider_ids,
                    skill_ids,
                    error_type,
                    error_detail,
                    created_at,
                    updated_at
                FROM gateway_requests
                {where_sql}
                ORDER BY updated_at DESC, created_at DESC, request_id DESC
                LIMIT ?
                """,
                tuple(values),
            ).fetchall()
        return [GatewayRequestRecord(**dict(row)) for row in rows]

    def get_gateway_request(self, request_id: str) -> GatewayRequestRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    request_id,
                    client_request_id,
                    session_id,
                    status,
                    phase,
                    provider_id,
                    target,
                    stream_mode,
                    latency_ms,
                    first_token_latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    estimated_cost_usd,
                    attempted_provider_ids,
                    skill_ids,
                    error_type,
                    error_detail,
                    created_at,
                    updated_at
                FROM gateway_requests
                WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
        return GatewayRequestRecord(**dict(row)) if row else None
