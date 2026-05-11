from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any

from .models import CapabilityCell, ConversionProfile


class ConversionEngine(ABC):
    engine_id: str

    @abstractmethod
    def capability_cells(self) -> list[CapabilityCell]:
        raise NotImplementedError

    @abstractmethod
    def profiles(self) -> list[ConversionProfile]:
        raise NotImplementedError

    @abstractmethod
    async def submit(
        self,
        submission: Any,
        runtime: Any,
        request: Any,
        profile: ConversionProfile,
    ) -> dict[str, Any]:
        raise NotImplementedError


class EngineRegistry:
    def __init__(self) -> None:
        self._engines: dict[str, ConversionEngine] = {}
        self._profiles: dict[str, ConversionProfile] = {}

    def register(self, engine: ConversionEngine) -> None:
        self._engines[engine.engine_id] = engine
        for profile in engine.profiles():
            self._profiles[profile.id] = profile

    def get(self, engine_id: str) -> ConversionEngine:
        return self._engines[engine_id]

    def all_engines(self) -> list[ConversionEngine]:
        return list(self._engines.values())

    def all_cells(self) -> list[CapabilityCell]:
        cells: list[CapabilityCell] = []
        for engine in self._engines.values():
            cells.extend(engine.capability_cells())
        return cells

    def all_profiles(self) -> list[ConversionProfile]:
        return list(self._profiles.values())

    def profiles_by_path(self) -> dict[str, list[ConversionProfile]]:
        grouped: dict[str, list[ConversionProfile]] = defaultdict(list)
        for profile in self._profiles.values():
            grouped[profile.path_id].append(profile)
        for items in grouped.values():
            items.sort(key=lambda item: item.id)
        return dict(sorted(grouped.items()))

    def resolve_profile(self, path_id: str, profile_id: str) -> ConversionProfile:
        profile = self._profiles.get(profile_id)
        if profile is None or profile.path_id != path_id:
            raise KeyError(profile_id)
        return profile
