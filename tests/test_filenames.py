from __future__ import annotations

from app.core.filenames import sanitize_filename


def test_ascii_safe_name_unchanged(report_results):
    original = "clean-file_123.docx"
    result = sanitize_filename(original)
    report_results.append(("ASCII unchanged", original, result))
    assert result == original


def test_chinese_name_translated(report_results):
    original = "安全报告.docx"
    result = sanitize_filename(original)
    report_results.append(("Chinese translation", original, result))
    assert "inform" in result.lower() or "safe" in result.lower()
    assert result.endswith(".docx")


def test_mixed_symbols_and_spaces(report_results):
    original = "新设计稿 v2.0 (草案)/final?.docx"
    result = sanitize_filename(original)
    report_results.append(("Mixed symbols", original, result))
    assert "/" not in result and "?" not in result
    assert result.endswith(".docx")


def test_long_name_truncation(report_results):
    original = "一种非常长的中文文件名用于测试自动翻译-之后将要非常长的很多很多文字.docx"
    result = sanitize_filename(original)
    report_results.append(("Long truncation", original, result))
    assert len(result) <= 40 + len(".docx")
    assert result.endswith(".docx")


def test_empty_name_fallback(report_results):
    original = ""
    result = sanitize_filename(original, default="fallback")
    report_results.append(("Empty fallback", original, result))
    assert result == "fallback"
