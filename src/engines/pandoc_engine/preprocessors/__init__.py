"""Plugin registry for LaTeX preprocessor steps."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

PreprocessorFunc = Callable[["PreprocessorState"], None]


@dataclass
class Preprocessor:
    name: str
    func: PreprocessorFunc
    depends_on: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""


@dataclass
class PreprocessorState:
    text: str
    metadata: dict[str, object]

    def replace_text(self, new_text: str) -> None:
        self.text = new_text

    def path_value(self, key: str) -> Path | None:
        value = self.metadata.get(key)
        return value if isinstance(value, Path) else None


class PreprocessorRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, Preprocessor] = {}

    def register(
        self,
        name: str,
        *,
        depends_on: list[str] | tuple[str, ...] | None = None,
        description: str = "",
    ) -> Callable[[PreprocessorFunc], PreprocessorFunc]:
        def decorator(func: PreprocessorFunc) -> PreprocessorFunc:
            self._registry[name] = Preprocessor(
                name=name,
                func=func,
                depends_on=tuple(depends_on or ()),
                description=description,
            )
            return func

        return decorator

    def get(self, name: str) -> Preprocessor:
        if name not in self._registry:
            raise KeyError(f"Preprocessor '{name}' is not registered.")
        return self._registry[name]

    def resolve(self, names: list[str] | tuple[str, ...]) -> list[Preprocessor]:
        requested = [self.get(name) for name in names]
        ordered: list[Preprocessor] = []
        visited: set[str] = set()
        temp_mark: set[str] = set()

        def visit(preprocessor: Preprocessor) -> None:
            if preprocessor.name in visited:
                return
            if preprocessor.name in temp_mark:
                raise RuntimeError(f"Circular dependency detected at '{preprocessor.name}'")
            temp_mark.add(preprocessor.name)
            for dep in preprocessor.depends_on:
                visit(self.get(dep))
            temp_mark.remove(preprocessor.name)
            visited.add(preprocessor.name)
            ordered.append(preprocessor)

        for item in requested:
            visit(item)

        deduped: list[Preprocessor] = []
        seen: set[str] = set()
        for item in ordered:
            if item.name in seen:
                continue
            seen.add(item.name)
            deduped.append(item)
        return deduped


registry = PreprocessorRegistry()


def run_preprocessors(
    names: list[str] | tuple[str, ...],
    initial_text: str,
    metadata: dict[str, object] | None = None,
) -> tuple[str, list[str], dict[str, object]]:
    state = PreprocessorState(text=initial_text, metadata=dict(metadata or {}))
    ordered = registry.resolve(names)
    executed: list[str] = []
    for processor in ordered:
        processor.func(state)
        executed.append(processor.name)
    return state.text, executed, state.metadata


from . import bicaption, captions, graphics, math_symbol, normalize_strong, tabularray, tabularx, tsup_citation  # noqa: E402,F401

__all__ = [
    "Preprocessor",
    "PreprocessorRegistry",
    "PreprocessorState",
    "registry",
    "run_preprocessors",
]
