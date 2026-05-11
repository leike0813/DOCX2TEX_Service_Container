from __future__ import annotations

from document_conversion.domain import (
    CapabilityCell,
    ConversionEngine,
    ConversionProfile,
    DocumentFormat,
    EngineRegistry,
)


class _FakeConverter(ConversionEngine):
    converter_id = "fake"
    engine_id = "fake"

    def capability_cells(self) -> list[CapabilityCell]:
        return [
            CapabilityCell(
                path_id="docx_to_latex",
                engine_id=self.engine_id,
                source_format=DocumentFormat.DOCX,
                target_format=DocumentFormat.LATEX,
                status="implemented",
            )
        ]

    def profiles(self) -> list[ConversionProfile]:
        return [
            ConversionProfile(
                id="docx_to_latex/fake-default",
                label="Fake Default",
                path_id="docx_to_latex",
                engine_id=self.engine_id,
            )
        ]

    async def submit(self, submission, runtime, request, profile) -> dict[str, bool]:
        return {"ok": True}


def test_engine_registry_resolves_profile_within_path():
    registry = EngineRegistry()
    converter = _FakeConverter()
    registry.register(converter)

    assert registry.get("fake") is converter
    profile = registry.resolve_profile("docx_to_latex", "docx_to_latex/fake-default")
    assert profile.engine_id == "fake"
    assert registry.all_cells()[0].path_id == "docx_to_latex"
