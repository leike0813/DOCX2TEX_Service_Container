"""Post-processing helpers for the Pandoc engine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Postprocessor:
    name: str
    lua_filter: Path | None = None


class PostprocessorRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, Postprocessor] = {}

    def register(self, postprocessor: Postprocessor) -> None:
        self._registry[postprocessor.name] = postprocessor

    def collect_args(self, names: list[str]) -> list[str]:
        args: list[str] = []
        for name in names:
            post = self._registry.get(name)
            if not post:
                raise KeyError(f"Postprocessor '{name}' is not registered.")
            if post.lua_filter:
                args.append(f"--lua-filter={post.lua_filter.as_posix()}")
        return args


registry = PostprocessorRegistry()

from . import catalog as _catalog  # noqa: E402,F401

__all__ = ["Postprocessor", "PostprocessorRegistry", "registry"]
