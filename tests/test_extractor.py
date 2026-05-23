"""Tests for _extractor.py — EventExtractor pipeline stages (with mocks)."""

import pytest
from unittest.mock import patch, MagicMock
from chinese_scraper_utils import ExtractedEvent, EventExtractor, DeepSeekClient
from chinese_scraper_utils._extractor import (
    _score_text,
    _prefilter,
    _looks_like_title,
    _check_date,
    _validate_and_score,
    _make_fingerprint,
    _dedup,
    _normalize_title,
    _is_same_event,
    _merge_fields,
)


@pytest.fixture
def client():
    return DeepSeekClient(api_key="sk-test", model="deepseek-chat", max_retries=1)


@pytest.fixture
def extractor(client):
    return EventExtractor(
        client=client,
        event_types=["漫展", "同人展", "演唱会", "音乐会", "展览"],
        min_confidence=0.5,
    )


class TestScoreText:
    def test_high_score_for_event_text(self):
        score = _score_text("5月3日北京国家会议中心举办漫展嘉年华")
        assert score >= 3  # date + city + venue + event keyword

    def test_low_score_for_chat(self):
        score = _score_text("今天天气不错出去玩了")
        assert score <= 1

    def test_date_city_only(self):
        score = _score_text("5月4日上海")
        assert score >= 2  # date + city


class TestPrefilter:
    def test_filters_noise(self):
        texts = [
            "五一漫展来啦！5月3日北京国家会议中心有ComiCup",
            "返图自拍好开心玩得开心超话面基集邮",
        ]
        result = _prefilter(texts, min_score=3)
        # 噪音文本应该被过滤
        result_texts = [t for _, t in result]
        assert len(result) == 1
        assert "ComiCup" in result_texts[0]

    def test_min_score_threshold(self):
        texts = ["5月3日上海", "今天天气不错"]
        result = _prefilter(texts, min_score=3)
        assert len(result) == 0  # neither reaches 3

    def test_deduplicates_similar_texts(self):
        texts = [
            "五一漫展上海有展，在国家会展中心举办欢迎参加",
            "五一漫展上海有展，在国家会展中心举办欢迎参加",  # duplicate
        ]
        result = _prefilter(texts, min_score=2)
        assert len(result) == 1


class TestLooksLikeTitle:
    def test_valid_title(self):
        assert _looks_like_title("北京ComiCup同人展")
        assert _looks_like_title("初音未来演唱会")

    def test_invalid_title(self):
        assert not _looks_like_title("")
        assert not _looks_like_title("嗯")
        assert not _looks_like_title("1234567890")


class TestCheckDate:
    def test_future_date_valid(self):
        assert _check_date("2027-12-31")

    def test_past_date_invalid(self):
        assert not _check_date("2020-01-01")

    def test_empty_invalid(self):
        assert not _check_date("")

    def test_garbage_invalid(self):
        assert not _check_date("not a date")


class TestValidateAndScore:
    def test_high_confidence_event(self):
        raw = [{
            "title": "北京五一漫展",
            "date": "2027-05-01",
            "city": "北京",
            "venue": "国家会议中心",
            "category": "漫展",
            "source_index": 0,
        }]
        text_map = {0: "五一北京漫展在国家会议中心"}
        events = _validate_and_score(raw, ["漫展"], None, text_map)
        assert len(events) == 1
        # 全部有效 → confidence ≈ 1.0
        assert events[0].confidence >= 0.8
        assert events[0].source_text == "五一北京漫展在国家会议中心"

    def test_low_confidence_event(self):
        raw = [{"title": "某活动", "date": "", "city": "", "venue": "", "category": "", "source_index": 0}]
        text_map = {0: "据说有个活动"}
        events = _validate_and_score(raw, ["漫展"], None, text_map)
        assert len(events) == 1
        # 全部无效 → confidence ≈ 0
        assert events[0].confidence <= 0.2

    def test_domain_filter_rejects(self):
        """Category not in event_types should be rejected."""
        raw = [{"title": "军事演习", "category": "军事", "date": "2027-05-01", "city": "北京", "source_index": 0}]
        text_map = {0: "军事演习"}
        events = _validate_and_score(raw, ["漫展", "演唱会"], None, text_map)
        assert len(events) == 0


class TestDedup:
    def _make(self, title, city, date, confidence=0.5):
        return ExtractedEvent(
            title=title, date=date, city=city,
            category="漫展", confidence=confidence,
            source_text="", source_index=0,
        )

    def test_exact_fingerprint_dedup(self):
        a = self._make("北京漫展", "北京", "2026-05-04", 0.5)
        b = self._make("北京漫展", "北京", "2026-05-04", 0.8)
        result = _dedup([a, b])
        assert len(result) == 1
        assert result[0].confidence == 0.8  # higher confidence kept

    def test_fuzzy_merge_same_city_month(self):
        a = self._make("北京ComiCup漫展", "北京", "2026-05-04", 0.5)
        b = self._make("ComiCup漫展 in 北京", "北京", "2026-05-05", 0.7)
        result = _dedup([a, b])
        assert len(result) == 1
        assert result[0].confidence == 0.7

    def test_different_cities_not_deduped(self):
        a = self._make("漫展", "北京", "2026-05-04")
        b = self._make("漫展", "上海", "2026-05-04")
        result = _dedup([a, b])
        assert len(result) == 2


class TestMergeFields:
    def _make(self, title, city, date, venue="", end_date=None):
        return ExtractedEvent(title=title, city=city, date=date, venue=venue, end_date=end_date,
                             category="漫展", confidence=0.5, source_text="", source_index=0)

    def test_merge_fills_missing_venue(self):
        a = self._make("漫展", "北京", "2026-05-04", venue="")
        b = self._make("漫展", "北京", "2026-05-04", venue="国家会议中心")
        _merge_fields(a, b)
        assert a.venue == "国家会议中心"

    def test_merge_does_not_overwrite(self):
        a = self._make("漫展", "北京", "2026-05-04", venue="会展中心")
        b = self._make("漫展", "北京", "2026-05-04", venue="国家会议中心")
        _merge_fields(a, b)
        assert a.venue == "会展中心"  # existing value preserved
