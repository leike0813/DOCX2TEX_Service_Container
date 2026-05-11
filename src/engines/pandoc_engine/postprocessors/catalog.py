"""Default postprocessor catalogue."""

from __future__ import annotations

from pathlib import Path

from . import Postprocessor, registry

FILTER_DIR = Path(__file__).resolve().parent.parent / "filters"

registry.register(Postprocessor(name="caption_colon_fix", lua_filter=FILTER_DIR / "caption_colon_to_space.lua"))
registry.register(Postprocessor(name="org_helper", lua_filter=FILTER_DIR / "org_helper.lua"))
