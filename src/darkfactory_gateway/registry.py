from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Iterable

from darkfactory.config import provider_settings_from_env
from darkfactory.models import ProviderSettings

from .models import GatewayProviderInfo


@dataclass(slots=True)
class ProviderRecord:
    id: str
    kind: str
    label: str
    settings: ProviderSettings
    enabled: bool = True
    default: bool = False
    priority: int = 100
    tags: list[str] | None = None
    default_skill_ids: list[str] | None = None
    cooldown_seconds: int = 30
    max_consecutive_failures: int = 3

    def normalized_tags(self) -> list[str]:
        return list(self.tags or [])

    def normalized_default_skill_ids(self) -> list[str]:
        return list(self.default_skill_ids or [])


class ProviderRegistry:
    def __init__(self, records: list[ProviderRecord] | None = None) -> None:
        loaded_records = records or self._load_records()
        self._records = sorted(
            loaded_records,
            key=lambda item: (0 if item.default else 1, item.priority, item.id),
        )

    def _load_records(self) -> list[ProviderRecord]:
        records = [
            ProviderRecord(
                id="mock",
                kind="mock",
                label="Mock Provider",
                settings=ProviderSettings(provider="mock"),
                default=True,
                priority=999,
                tags=["local", "fallback"],
            )
        ]

        raw_json = os.getenv("DARKFACTORY_GATEWAY_PROVIDERS_JSON", "").strip()
        if raw_json:
            loaded = json.loads(raw_json)
            if isinstance(loaded, list):
                records = []
                for index, item in enumerate(loaded):
                    if not isinstance(item, dict):
                        continue
                    provider_id = str(item.get("id") or f"provider_{index}")
                    kind = str(item.get("kind") or "mock")
                    label = str(item.get("label") or provider_id)
                    enabled = bool(item.get("enabled", True))
                    default = bool(item.get("default", False))
                    priority = int(item.get("priority", 100))
                    tags = [
                        str(tag).strip()
                        for tag in item.get("tags", [])
                        if str(tag).strip()
                    ]
                    default_skill_ids = [
                        str(skill_id).strip()
                        for skill_id in item.get("default_skill_ids", [])
                        if str(skill_id).strip()
                    ]
                    settings = ProviderSettings(
                        provider=kind,
                        ollama_url=str(item.get("ollama_url") or "http://127.0.0.1:11434/v1"),
                        ollama_model=str(item.get("ollama_model") or ""),
                        ollama_api_key=str(item.get("ollama_api_key") or "ollama"),
                        openai_base_url=str(item.get("openai_base_url") or ""),
                        openai_api_key=str(item.get("openai_api_key") or ""),
                        openai_model=str(item.get("openai_model") or ""),
                        api_url=str(item.get("api_url") or ""),
                        api_health_url=str(item.get("api_health_url") or ""),
                        api_stream_url=str(item.get("api_stream_url") or ""),
                        api_cancel_url_template=str(item.get("api_cancel_url_template") or ""),
                        api_providers_url=str(item.get("api_providers_url") or ""),
                        request_timeout_seconds=int(item.get("request_timeout_seconds") or 60),
                    )
                    records.append(
                        ProviderRecord(
                            id=provider_id,
                            kind=kind,
                            label=label,
                            settings=settings,
                            enabled=enabled,
                            default=default,
                            priority=priority,
                            tags=tags,
                            default_skill_ids=default_skill_ids,
                            cooldown_seconds=max(0, int(item.get("cooldown_seconds", 30))),
                            max_consecutive_failures=max(
                                1,
                                int(item.get("max_consecutive_failures", 3)),
                            ),
                        )
                    )
            return records

        env_settings = provider_settings_from_env()
        if env_settings.provider or env_settings.openai_model or env_settings.ollama_model:
            kind = env_settings.provider or "openai_compatible"
            records.append(
                ProviderRecord(
                    id="default",
                    kind=kind,
                    label="Default Env Provider",
                    settings=env_settings,
                    default=False,
                    priority=10,
                    tags=["env"],
                    cooldown_seconds=30,
                    max_consecutive_failures=3,
                )
            )
        return records

    def list(self) -> list[ProviderRecord]:
        return list(self._records)

    def enabled(self) -> list[ProviderRecord]:
        return [record for record in self._records if record.enabled]

    def infos(self) -> list[GatewayProviderInfo]:
        return [
            GatewayProviderInfo(
                id=record.id,
                kind=record.kind,
                label=record.label,
                default=record.default,
                enabled=record.enabled,
                priority=record.priority,
                tags=record.normalized_tags(),
                default_skill_ids=record.normalized_default_skill_ids(),
                cooldown_seconds=record.cooldown_seconds,
                max_consecutive_failures=record.max_consecutive_failures,
            )
            for record in self._records
        ]

    def get(self, provider_id: str | None = None) -> ProviderRecord:
        if provider_id:
            for record in self._records:
                if record.id == provider_id:
                    return record
            raise KeyError(provider_id)

        for record in self._records:
            if record.default:
                return record
        return self._records[0]

    def resolve_chain(
        self,
        provider_id: str | None = None,
        strategy: str = "default",
    ) -> list[ProviderRecord]:
        if provider_id:
            selected = self.get(provider_id)
            chain = [selected]
            if strategy == "fallback":
                for record in self.enabled():
                    if record.id != selected.id:
                        chain.append(record)
            return chain

        enabled_records = self.enabled() or self.list()
        if strategy == "fallback":
            return enabled_records

        return [self.get()]

    def default_provider_id(self) -> str:
        return self.get().id

    def validate_skill_targets(self, skill_ids: Iterable[str]) -> list[str]:
        normalized = [skill_id.strip() for skill_id in skill_ids if skill_id.strip()]
        return normalized
