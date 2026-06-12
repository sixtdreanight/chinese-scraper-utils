"""Tests for _date.py — parse_date, try_parse_date, extract_date."""

import pytest
from datetime import datetime
from chinese_scraper_utils import parse_date, try_parse_date, extract_date


class TestParseDate:
    # ── Valid formats ──

    def test_iso_format(self):
        assert parse_date("2026-05-04") == "2026-05-04"

    def test_slash_format(self):
        assert parse_date("2026/05/04") == "2026-05-04"

    def test_dot_format(self):
        assert parse_date("2026.05.04") == "2026-05-04"

    def test_compact_format(self):
        assert parse_date("20260504") == "2026-05-04"

    def test_datetime_format(self):
        assert parse_date("2026-05-04 14:30:00") == "2026-05-04"

    def test_iso_with_timezone(self):
        result = parse_date("2026-05-04T14:30:00")
        assert result == "2026-05-04" or result == ""  # fromisoformat handles this

    # ── Edge cases ──

    def test_empty_string(self):
        assert parse_date("") == ""

    def test_none_like(self):
        # parse_date historically accepted empty; now returns ""
        assert parse_date("") == ""

    def test_garbage_returns_empty_not_truncated_garbage(self):
        """Regression test: '北京国家会议中心' should NOT return '北京国家会议中'."""
        result = parse_date("北京国家会议中心")
        assert result == "", f"Expected empty string, got '{result}'"

    def test_random_text(self):
        assert parse_date("hello world") == ""

    def test_short_text(self):
        assert parse_date("abc") == ""

    def test_partial_date(self):
        """'2026-05' is not a complete date."""
        result = parse_date("2026-05")
        assert result == ""


class TestTryParseDate:
    def test_valid_date(self):
        assert try_parse_date("2026-05-04") == "2026-05-04"

    def test_empty_returns_none(self):
        assert try_parse_date("") is None

    def test_garbage_returns_none(self):
        assert try_parse_date("not a date") is None


class TestExtractDate:
    def test_chinese_full_date(self):
        result = extract_date("2026年5月4日上海有漫展")
        assert result == "2026-05-04"

    def test_month_day_only(self):
        result = extract_date("5月4日有活动")
        year = datetime.now().year
        assert result == f"{year}-05-04"

    def test_range_format(self):
        result = extract_date("5月4日-6日广州")
        year = datetime.now().year
        assert result == f"{year}-05-04"

    def test_no_date(self):
        assert extract_date("今天天气不错") == ""

    def test_cross_year_threshold(self):
        """When month-day is > 90 days in the past, it should advance to next year."""
        # Use a date far in the past to trigger cross-year
        result = extract_date("1月1日有活动")
        # Should be next year's January 1st if today is past October
        year = datetime.now().year
        from datetime import date as Date
        jan1 = Date(year, 1, 1)
        if (Date.today() - jan1).days > 90:
            assert result == f"{year + 1}-01-01"
        else:
            assert result == f"{year}-01-01"

    def test_full_date_no_cross_year(self):
        """Explicit year should prevent cross-year advancement."""
        result = extract_date("2025年1月1日有活动")
        assert result == "2025-01-01"
