"""Template configuration loading and detection utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

DOCUMENTCLASS_RE = re.compile(r"\\documentclass(?:\[[^\]]*])?{([^}]+)}")
USEPACKAGE_RE = re.compile(r"\\usepackage(?:\[[^\]]*])?{([^}]+)}")


class TemplateConfigError(RuntimeError):
    """Raised when a template configuration is invalid."""


def _merge_values(base: Any, new: Any) -> Any:
    if isinstance(base, dict) and isinstance(new, dict):
        merged = dict(base)
        for key, value in new.items():
            if key in merged:
                merged[key] = _merge_values(merged[key], value)
            else:
                merged[key] = value
        return merged
    if isinstance(base, list) and isinstance(new, list):
        merged_list: list[Any] = []
        seen: set[Any] = set()
        for item in base + new:
            marker = item if isinstance(item, (str, int, float)) else id(item)
            if marker in seen:
                continue
            seen.add(marker)
            merged_list.append(item)
        return merged_list
    return new


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TemplateConfigError(f"Failed to parse template '{path}': {exc}") from exc
    if not isinstance(data, dict):
        raise TemplateConfigError(f"Template '{path}' must be a mapping.")
    return data


@dataclass(frozen=True)
class TemplateConfig:
    name: str
    data: dict[str, Any]

    def preprocessors(self) -> list[dict[str, Any]]:
        return _ordered_entries(self.data.get("preprocessors"))

    def filters(self) -> list[dict[str, Any]]:
        return _ordered_entries(self.data.get("filters"))

    def pandoc_spec(self) -> dict[str, Any]:
        return dict(self.data.get("pandoc", {}))

    def detect_block(self) -> dict[str, Any]:
        return dict(self.data.get("detect", {}))

    def citations(self) -> dict[str, Any]:
        return dict(self.data.get("citations", {}))


class TemplateRegistry:
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self._cache: dict[str, TemplateConfig] = {}

    def available_templates(self) -> list[str]:
        return sorted(path.stem for path in self.templates_dir.glob("*.yaml"))

    def load(self, name: str) -> TemplateConfig:
        if name in self._cache:
            return self._cache[name]
        path = self.templates_dir / f"{name}.yaml"
        if not path.exists():
            raise TemplateConfigError(f"Template '{name}' not found at {path}")
        raw = _load_yaml(path)
        inherits = raw.pop("inherits", None)
        merged = _merge_values(self.load(inherits).data, raw) if inherits else raw
        config = TemplateConfig(name=name, data=merged)
        self._cache[name] = config
        return config


class TemplateDetector:
    def __init__(self, registry: TemplateRegistry, fallback: str = "base"):
        self.registry = registry
        self.fallback = fallback

    def guess(self, tex_path: Path, preferred: str | None = None) -> TemplateConfig:
        if preferred:
            return self.registry.load(preferred)
        text = tex_path.read_text(encoding="utf-8", errors="ignore")
        docclass = self._extract_document_class(text)
        packages = list(self._extract_packages(text))
        candidates: list[tuple[TemplateConfig, int]] = []
        for name in self.registry.available_templates():
            if name == self.fallback:
                continue
            config = self.registry.load(name)
            score = _score_config(config.detect_block(), docclass, packages, text)
            threshold = int(config.detect_block().get("threshold", 1))
            if score >= threshold and score > 0:
                candidates.append((config, score))
        if not candidates:
            return self.registry.load(self.fallback)
        candidates.sort(key=lambda item: item[1], reverse=True)
        top_score = candidates[0][1]
        tied = [config for config, score in candidates if score == top_score]
        if len(tied) == 1:
            return tied[0]
        for config in tied:
            if docclass and docclass in config.detect_block().get("classes", []):
                return config
        return tied[0]

    @staticmethod
    def _extract_document_class(text: str) -> str | None:
        match = DOCUMENTCLASS_RE.search(text)
        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_packages(text: str) -> list[str]:
        packages: list[str] = []
        for found in USEPACKAGE_RE.findall(text):
            for token in found.split(","):
                item = token.strip()
                if item:
                    packages.append(item)
        return packages


def _score_config(
    detect_block: dict[str, Any],
    docclass: str | None,
    packages: list[str],
    text: str,
) -> int:
    score = 0
    if docclass and docclass in detect_block.get("classes", []):
        score += 5
    package_set = set(packages)
    for pkg, weight in detect_block.get("packages", {}).items():
        if pkg in package_set:
            score += int(weight)
    for feature, weight in detect_block.get("features", {}).items():
        if feature in text:
            score += int(weight)
    return score


def _ordered_entries(raw_value: Any) -> list[dict[str, Any]]:
    if not raw_value:
        return []
    ordered: dict[str, dict[str, Any]] = {}
    for item in raw_value:
        if isinstance(item, str):
            entry = {"name": item, "order": 0}
        elif isinstance(item, dict):
            name = item.get("name")
            if not name:
                raise TemplateConfigError("Pipeline entry missing 'name' field.")
            entry = dict(item)
            order_value = entry.get("order", 0)
            if not isinstance(order_value, (str, int, float)):
                order_value = 0
            entry["order"] = int(order_value)
        else:
            raise TemplateConfigError(f"Unsupported pipeline entry type: {item!r}")
        ordered[cast(str, entry["name"])] = entry
    return sorted(ordered.values(), key=lambda entry: (entry.get("order", 0), entry["name"]))
