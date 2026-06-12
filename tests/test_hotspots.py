"""Tests for _hotspots.py — scrape_weibo_hot, scrape_zhihu_hot, scrape_hackernews_top (mocked httpx)."""

import pytest
from unittest.mock import patch, MagicMock
import json
from chinese_scraper_utils import (
    scrape_weibo_hot,
    scrape_zhihu_hot,
    scrape_hackernews_top,
    HotTopic,
)


class TestScrapeWeiboHot:
    def test_successful_scrape(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "realtime": [
                    {"word": "五一漫展", "rank": 1, "raw_hot": 9999, "scheme": "https://s.weibo.com/weibo?q=五一漫展"},
                    {"word": "#热门话题#", "rank": 2, "raw_hot": 8000},
                    {"word": "实时热搜", "rank": 3, "raw_hot": 0},  # should be filtered
                ]
            }
        }
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_resp

        with patch("chinese_scraper_utils._hotspots.httpx.Client", return_value=mock_client):
            results = scrape_weibo_hot()

        assert len(results) >= 1
        assert results[0].title == "五一漫展"
        assert results[1].title == "热门话题"  # stripped #
        assert results[0].source == "微博热搜"

    def test_http_error_returns_empty(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_resp

        with patch("chinese_scraper_utils._hotspots.httpx.Client", return_value=mock_client):
            results = scrape_weibo_hot()
            assert results == []


class TestScrapeZhihuHot:
    def test_successful_scrape(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {"target": {"title": "如何看待AI发展", "url": "https://zhihu.com/q/123", "excerpt": "AI讨论", "heat": 5000}},
            ]
        }
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_resp

        with patch("chinese_scraper_utils._hotspots.httpx.Client", return_value=mock_client):
            results = scrape_zhihu_hot()

        assert len(results) == 1
        assert results[0].title == "如何看待AI发展"
        assert results[0].source == "知乎热榜"


class TestScrapeHackernewsTop:
    def test_successful_scrape(self):
        # Mock the story list response
        mock_ids_resp = MagicMock()
        mock_ids_resp.status_code = 200
        mock_ids_resp.json.return_value = [42, 43]

        # Mock individual story responses
        mock_story_42 = MagicMock()
        mock_story_42.status_code = 200
        mock_story_42.json.return_value = {"title": "Show HN: Cool Project", "url": "https://example.com", "score": 100, "descendants": 50}
        mock_story_43 = MagicMock()
        mock_story_43.status_code = 200
        mock_story_43.json.return_value = {"title": "", "score": 0}  # empty title → skipped

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        # First call: story IDs, then individual stories
        mock_client.get.side_effect = [mock_ids_resp, mock_story_42, mock_story_43]

        with patch("chinese_scraper_utils._hotspots.httpx.Client", return_value=mock_client):
            results = scrape_hackernews_top()

        assert len(results) == 1
        assert results[0].title == "Show HN: Cool Project"
        assert results[0].source == "Hacker News"
        assert results[0].raw_score == 100

    def test_hn_http_error_returns_empty(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_resp

        with patch("chinese_scraper_utils._hotspots.httpx.Client", return_value=mock_client):
            results = scrape_hackernews_top()
            assert results == []

    def test_hn_fetch_one_exception_returns_none(self):
        """When an individual story fetch raises an exception, it should be skipped."""
        mock_ids_resp = MagicMock()
        mock_ids_resp.status_code = 200
        mock_ids_resp.json.return_value = [42]

        mock_story = MagicMock()
        mock_story.status_code = 200
        mock_story.json.side_effect = Exception("connection error")

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.side_effect = [mock_ids_resp, mock_story]

        with patch("chinese_scraper_utils._hotspots.httpx.Client", return_value=mock_client):
            results = scrape_hackernews_top()
            assert results == []


class TestScraperRegistry:
    def test_register_and_list(self):
        from chinese_scraper_utils import register_scraper, list_scrapers
        @register_scraper("_test_source")
        def _test_scraper():
            return []
        assert "_test_source" in list_scrapers()

    def test_scrape_all(self):
        from chinese_scraper_utils import scrape_all
        results = scrape_all()
        assert "weibo" in results
        assert "zhihu" in results
        assert "hackernews" in results
