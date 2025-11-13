from __future__ import annotations

from typing import List, Tuple

import pytest

filename_results: List[Tuple[str, str, str]] = []


@pytest.fixture(scope="module")
def report_results() -> List[Tuple[str, str, str]]:
    filename_results.clear()
    yield filename_results


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not filename_results:
        return
    terminalreporter.write_sep("-", "filename sanitize results")
    for title, original, sanitized in filename_results:
        terminalreporter.write_line(f"{title}: {original} -> {sanitized}")
