"""Tests for _city.py — extract_city, normalize_city, CITIES."""

import pytest
from chinese_scraper_utils import extract_city, normalize_city, CITIES


class TestExtractCity:
    # ── Normal matches ──

    def test_extract_at_beginning(self):
        assert extract_city("上海浦东新区有漫展") == "上海"

    def test_extract_in_middle(self):
        assert extract_city("活动在上海举办") == "上海"

    def test_extract_at_end(self):
        assert extract_city("今天去广州") == "广州"

    def test_extract_with_suffix(self):
        """'上海市' should still match '上海'."""
        result = extract_city("上海市浦东新区")
        assert result == "上海"

    # ── False positive regression ──

    def test_false_positive_xian_road(self):
        """Regression: '西安路' should NOT match '西安'."""
        assert extract_city("西安路有个活动") == ""

    def test_false_positive_haikou_village(self):
        """Regression: '海口村' should NOT match '海口'."""
        assert extract_city("海口村有漫展") == ""

    def test_false_positive_beijing_road(self):
        assert extract_city("北京路步行街") == ""

    # ── Longest match ──

    def test_longest_match_prioritized(self):
        """'石家庄' should match before '石' (if '石' were a city)."""
        assert extract_city("石家庄有展") == "石家庄"

    # ── Multiple cities ──

    def test_first_match_returned(self):
        assert extract_city("从上海到北京") == "上海"  # 上海先出现

    # ── Empty / no match ──

    def test_no_city(self):
        assert extract_city("今天天气不错") == ""

    def test_empty_text(self):
        assert extract_city("") == ""

    # ── False suffix words ──

    def test_false_positive_university(self):
        """'北京大学' should NOT match '北京'."""
        assert extract_city("北京大学有活动") == ""

    def test_false_positive_hotel(self):
        """'西安大酒店' should NOT match '西安'."""
        assert extract_city("西安大酒店有活动") == ""

    def test_false_positive_airport(self):
        """'厦门机场' should NOT match '厦门'."""
        assert extract_city("厦门机场附近") == ""

    # ── Extra cities ──

    def test_extra_cities(self):
        result = extract_city("日喀则有活动", extra_cities=["日喀则"])
        assert result == "日喀则"

    def test_extra_cities_does_not_break_builtin(self):
        result = extract_city("上海有展", extra_cities=["日喀则"])
        assert result == "上海"

    def test_extra_cities_longest_priority(self):
        """Extra cities also use longest-match priority."""
        result = extract_city("乌鲁木齐有展", extra_cities=["乌鲁"])
        assert result == "乌鲁木齐"


class TestNormalizeCity:
    def test_strip_suffix(self):
        assert normalize_city("上海市") == "上海"

    def test_strip_whitespace(self):
        assert normalize_city("  深圳  ") == "深圳"

    def test_china_aliases(self):
        assert normalize_city("中国") == ""
        assert normalize_city("全国") == ""

    def test_already_normal(self):
        assert normalize_city("北京") == "北京"


class TestCities:
    def test_count(self):
        assert len(CITIES) == 50

    def test_no_duplicates(self):
        assert len(CITIES) == len(set(CITIES))

    def test_major_cities_present(self):
        for city in ["北京", "上海", "广州", "深圳", "成都", "杭州"]:
            assert city in CITIES
