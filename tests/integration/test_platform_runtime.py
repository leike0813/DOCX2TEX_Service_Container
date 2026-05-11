from __future__ import annotations

from pathlib import Path

from document_conversion.infrastructure.runtime import build_platform_context


def test_build_platform_context_uses_current_environment(isolated_platform_env: Path):
    ctx = build_platform_context()
    assert ctx.cfg.data_root == (isolated_platform_env / "data").resolve()
    assert ctx.cfg.public_root == (isolated_platform_env / "work").resolve()
    payload = ctx.capabilities_payload()
    assert any(
        item["path_id"] == "latex_to_docx"
        and item["engine_id"] == "pandoc"
        and item["status"] == "implemented"
        for item in payload["capabilities"]
    )
