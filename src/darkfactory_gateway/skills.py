from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from string import Formatter

from .models import GatewayChatRequest, GatewaySkillInfo


@dataclass(slots=True)
class SkillRecord:
    id: str
    label: str
    description: str
    template: str
    phase: str = "prompt_shaping"
    enabled_by_default: bool = False
    parameters: dict[str, str] = field(default_factory=dict)

    def parameter_keys(self) -> list[str]:
        keys = set(self.parameters)
        for _, field_name, _, _ in Formatter().parse(self.template):
            if field_name:
                keys.add(field_name)
        return sorted(keys)


@dataclass(slots=True)
class RenderedSkill:
    id: str
    label: str
    phase: str
    content: str


class SafeFormatDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class SkillRegistry:
    def __init__(self, records: list[SkillRecord] | None = None) -> None:
        self._records = records or self._load_records()

    def _load_records(self) -> list[SkillRecord]:
        records = [
            SkillRecord(
                id="project_context",
                label="Project Context",
                description="Inject explicit project and session context into the request.",
                phase="pre_context",
                enabled_by_default=True,
                template=(
                    "当前项目为“{project_name}”，电厂“{plant}”，机组“{unit}”，"
                    "专家角色“{expert_type}”，当前会话“{session_name}”。"
                    "引用项目上下文时先确认是否缺少关键数据。"
                ),
            ),
            SkillRecord(
                id="structured_output",
                label="Structured Output",
                description="Force structured operational output blocks.",
                phase="prompt_shaping",
                enabled_by_default=True,
                parameters={
                    "output_sections": "【结论】【原因分析】【优化建议】【影响评估】",
                },
                template=(
                    "输出优先使用以下结构：{output_sections}。"
                    "如果信息不足，单独列出“待确认项”。"
                ),
            ),
            SkillRecord(
                id="ops_guardrails",
                label="Ops Guardrails",
                description="Keep the answer grounded in operations analysis and uncertainty.",
                phase="prompt_shaping",
                enabled_by_default=True,
                parameters={"safety_mode": "conservative"},
                template=(
                    "分析风格采用 {safety_mode} 模式。"
                    "避免凭空编造现场数据，不确定时明确标注假设、影响范围和待确认项。"
                ),
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
                    template=str(item.get("template") or item.get("prompt") or ""),
                    phase=str(item.get("phase") or "prompt_shaping"),
                    enabled_by_default=bool(item.get("enabled_by_default", False)),
                    parameters={
                        str(key): str(value)
                        for key, value in (item.get("parameters") or {}).items()
                    },
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
                phase=record.phase,
                enabled_by_default=record.enabled_by_default,
                parameter_keys=record.parameter_keys(),
            )
            for record in self._records
        ]

    def select(
        self,
        *,
        request: GatewayChatRequest,
        default_skill_ids: list[str] | None = None,
    ) -> list[SkillRecord]:
        skill_ids = self._merge_skill_ids(
            request=request,
            default_skill_ids=default_skill_ids or [],
        )
        selected: list[SkillRecord] = []
        for skill_id in skill_ids:
            record = self.get(skill_id)
            if record is not None:
                selected.append(record)
        return selected

    def render_phase(
        self,
        *,
        request: GatewayChatRequest,
        selected_skills: list[SkillRecord],
        phase: str,
        extra_context: dict[str, str] | None = None,
    ) -> list[RenderedSkill]:
        context = self._build_context(request, extra_context=extra_context)
        rendered: list[RenderedSkill] = []
        for record in selected_skills:
            if record.phase != phase or not record.template.strip():
                continue
            values = SafeFormatDict(context)
            values.update(record.parameters)
            values.update(
                {
                    str(key): str(value)
                    for key, value in request.skill_arguments.get(record.id, {}).items()
                }
            )
            content = record.template.format_map(values).strip()
            if content:
                rendered.append(
                    RenderedSkill(
                        id=record.id,
                        label=record.label,
                        phase=record.phase,
                        content=content,
                    )
                )
        return rendered

    def apply_post_processing(
        self,
        *,
        request: GatewayChatRequest,
        selected_skills: list[SkillRecord],
        reply: str,
    ) -> str:
        result = reply
        rendered = self.render_phase(
            request=request,
            selected_skills=selected_skills,
            phase="post_processing",
            extra_context={"reply": result},
        )
        for item in rendered:
            if "{reply}" in (self.get(item.id).template if self.get(item.id) else ""):
                result = item.content
            else:
                result = f"{result}\n\n{item.content}".strip()
        return result

    def resolve(
        self,
        *,
        request: GatewayChatRequest,
        default_skill_ids: list[str] | None = None,
        phase: str = "prompt_shaping",
    ) -> list[RenderedSkill]:
        selected = list(self.select(request=request, default_skill_ids=default_skill_ids))
        return self.render_phase(
            request=request,
            selected_skills=selected,
            phase=phase,
        )

    def get(self, skill_id: str) -> SkillRecord | None:
        for record in self._records:
            if record.id == skill_id:
                return record
        return None

    def _merge_skill_ids(
        self,
        *,
        request: GatewayChatRequest,
        default_skill_ids: list[str],
    ) -> list[str]:
        if request.skill_mode == "request_only":
            return self._unique(request.skill_ids)

        merged = [
            record.id
            for record in self._records
            if record.enabled_by_default
        ]
        merged.extend(default_skill_ids)
        merged.extend(request.skill_ids)
        return self._unique(merged)

    def _build_context(
        self,
        request: GatewayChatRequest,
        extra_context: dict[str, str] | None = None,
    ) -> dict[str, str]:
        context = {
            "project_name": request.project.name,
            "plant": request.project.plant,
            "unit": request.project.unit,
            "expert_type": request.project.expert_type,
            "session_name": request.session.name,
            "session_summary": request.session.summary,
            "message": request.message,
        }
        if extra_context:
            context.update(extra_context)
        return context

    def _unique(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            normalized = value.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(normalized)
        return ordered
