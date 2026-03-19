from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .models import Message, Project, Session


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
                """
            )

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
