"""Tests for _category.py — guess_category, CATEGORY_ALIASES."""

import pytest
from chinese_scraper_utils import guess_category, CATEGORY_ALIASES


class TestGuessCategory:
    # ── Direct matches ──

    def test_manzhan(self):
        assert guess_category("五一漫展嘉年华") == "漫展"

    def test_concert(self):
        assert guess_category("初音未来演唱会") == "演唱会"

    def test_exhibition(self):
        assert guess_category("清明上河图展览") == "展览"

    def test_tongren(self):
        assert guess_category("ONLY同人展") == "同人展"

    def test_music(self):
        assert guess_category("新年音乐会") == "音乐会"

    # ── Longest match priority ──

    def test_longest_match_erciyuan(self):
        """'二次元' should map to '漫展', not get confused by partial matches."""
        assert guess_category("二次元漫展") == "漫展"

    def test_longest_match_cosplay(self):
        assert guess_category("cosplay活动") == "漫展"

    # ── Alias matching ──

    def test_alias_live(self):
        assert guess_category("地下偶像live演出") == "演唱会"

    def test_alias_cafe(self):
        assert guess_category("cafe主题店") == "展览"

    def test_alias_only(self):
        assert guess_category("ONLY展") == "同人展"

    # ── No match ──

    def test_no_match(self):
        assert guess_category("今天天气不错") == "其他"

    def test_empty_title(self):
        assert guess_category("") == "其他"

    # ── Case insensitivity ──

    def test_case_insensitive(self):
        assert guess_category("LIVE现场") == "演唱会"
