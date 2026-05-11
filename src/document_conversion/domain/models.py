from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class DocumentFormat(str, Enum):
    DOCX = "docx"
    LATEX = "latex"
    MARKDOWN = "markdown"


class InputSourceKind(str, Enum):
    FILE = "file"
    URL = "url"


@dataclass(frozen=True)
class ConversionPath:
    source_format: DocumentFormat
    target_format: DocumentFormat

    @property
    def id(self) -> str:
        return f"{self.source_format.value}_to_{self.target_format.value}"


@dataclass(frozen=True)
class InputSource:
    kind: InputSourceKind
    filename: Optional[str] = None
    url: Optional[str] = None


@dataclass(frozen=True)
class CapabilityCell:
    path_id: str
    engine_id: str
    source_format: DocumentFormat
    target_format: DocumentFormat
    status: str
    description: str = ""


@dataclass(frozen=True)
class ConversionProfile:
    id: str
    label: str
    path_id: str
    engine_id: str
    description: str = ""
    engine_options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConversionRequest:
    path: ConversionPath
    input_source: InputSource
    profile_id: str
    debug: bool = False
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConversionJob:
    task_id: str
    state: str
    err_msg: str = ""
    start_time: float = 0.0
    end_time: Optional[float] = None
    debug: bool = False
    work_dir: str = ""
