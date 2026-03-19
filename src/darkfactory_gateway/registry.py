from __future__ import annotations

import json
import os
from dataclasses import dataclass

from darkfactory.config import provider_settings_from_env
from darkfactory.models import ProviderSettings

from .models import GatewayProviderInfo


@dataclass(slots=True)
class ProviderRecord:
    id: str
    kind: str
    label: str
    settings: ProviderSettings
    default: bool = False


class ProviderRegistry:
    def __init__(self, records: list[ProviderRecord] | None = None) -> None:
        self._records = records or self._load_records()

    def _load_records(self) -> list[ProviderRecord]:
        records = [
            ProviderRecord(
                id="mock",
                kind="mock",
                label="Mock Provider",
                settings=ProviderSettings(provider="mock"),
                default=True,
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
                    default = bool(item.get("default", False))
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
                            default=default,
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
                )
            )
        return records

    def list(self) -> list[ProviderRecord]:
        return list(self._records)

    def infos(self) -> list[GatewayProviderInfo]:
        return [
            GatewayProviderInfo(
                id=record.id,
                kind=record.kind,
                label=record.label,
                default=record.default,
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
