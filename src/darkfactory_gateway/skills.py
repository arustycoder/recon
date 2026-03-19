from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .models import GatewayChatRequest, GatewaySkillInfo


@dataclass(slots=True)
class SkillRecord:
    id: str
    label: str
    description: str
    prompt: str


class SkillRegistry:
    def __init__(self, records: list[SkillRecord] | None = None) -> None:
        self._records = records or self._load_records()

    def _load_records(self) -> list[SkillRecord]:
        records = [
            SkillRecord(
                id="project_context",
                label="Project Context",
                description="Inject explicit project and session context into the request.",
                prompt="强调当前项目、电厂、机组和会话主题，缺失信息时明确说明。",
            ),
            SkillRecord(
                id="structured_output",
                label="Structured Output",
                description="Force structured operational output blocks.",
                prompt="输出时优先使用【结论】【原因分析】【优化建议】【影响评估】结构。",
            ),
            SkillRecord(
                id="ops_guardrails",
                label="Ops Guardrails",
                description="Keep the answer grounded in operations analysis and uncertainty.",
                prompt="避免凭空编造现场数据；不确定时明确标注假设和待确认项。",
            ),
        ]

        raw_json = os.getenv("DARKFACTORY_GATEWAY_SKILLS_JSON", "").strip()
        if not raw_json:
            return records

        loaded = json.loads(raw_json)
        if not isinstance(loaded, list):
            return records
        for item in loaded:
            if not isinstance(item, dict):
                continue
            records.append(
                SkillRecord(
                    id=str(item.get("id") or "custom"),
                    label=str(item.get("label") or item.get("id") or "Custom Skill"),
                    description=str(item.get("description") or "Custom gateway skill."),
                    prompt=str(item.get("prompt") or ""),
                )
            )
        return records

    def list(self) -> list[SkillRecord]:
        return list(self._records)

    def infos(self) -> list[GatewaySkillInfo]:
        return [
            GatewaySkillInfo(
                id=record.id,
                label=record.label,
                description=record.description,
            )
            for record in self._records
        ]

    def prompt_for(self, skill_ids: list[str], request: GatewayChatRequest) -> str:
        if not skill_ids:
            return ""
        prompts: list[str] = []
        for skill_id in skill_ids:
            for record in self._records:
                if record.id == skill_id and record.prompt:
                    prompts.append(f"[{record.id}] {record.prompt}")
                    break
        if not prompts:
            return ""
        return "\n".join(prompts)
