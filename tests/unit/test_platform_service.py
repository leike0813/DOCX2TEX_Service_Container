from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from document_conversion.application import PlatformService, PlatformTaskSubmission


class _EmptyRegistry:
    def resolve_profile(self, path_id, profile_id):
        raise KeyError(profile_id)


class _Runtime:
    registry = _EmptyRegistry()


def test_platform_service_rejects_unknown_profile():
    service = PlatformService(_Runtime())
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            service.submit_task(
                PlatformTaskSubmission(
                    source_format="docx",
                    target_format="latex",
                    profile_id="docx_to_latex/missing",
                    file=object(),
                )
            )
        )
    assert exc_info.value.status_code == 400
