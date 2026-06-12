"""Tests for __main__.py — CLI commands."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestSearchCommand:
    def test_search_with_results(self, capsys):
        from chinese_scraper_utils import SearchResult
        result = SearchResult(title="Test Result", url="https://example.com", snippet="A snippet")
        testargs = ["prog", "search", "test query"]
        with patch("chinese_scraper_utils.search_web", return_value=[result]):
            with patch.object(sys, "argv", testargs):
                from chinese_scraper_utils.__main__ import main
                main()
        captured = capsys.readouterr()
        assert "[1] Test Result" in captured.out

    def test_search_no_results(self, capsys):
        testargs = ["prog", "search", "no-match-query"]
        with patch("chinese_scraper_utils.search_web", return_value=[]):
            with patch.object(sys, "argv", testargs):
                from chinese_scraper_utils.__main__ import main
                main()
        captured = capsys.readouterr()
        assert "无结果" in captured.out

    def test_search_with_max_results(self, capsys):
        testargs = ["prog", "search", "test", "-n", "5"]
        with patch("chinese_scraper_utils.search_web") as mock_fn:
            mock_fn.return_value = []
            with patch.object(sys, "argv", testargs):
                from chinese_scraper_utils.__main__ import main
                main()
            mock_fn.assert_called_once_with("test", max_results=5)


class TestScrapeCommands:
    def test_scrape_weibo(self, capsys):
        from chinese_scraper_utils import HotTopic
        topics = [
            HotTopic(title="Hot Topic 1", summary="desc 1", url="https://a.com", source="weibo", raw_score=100),
        ]
        testargs = ["prog", "scrape-weibo"]
        with patch("chinese_scraper_utils.scrape_weibo_hot", return_value=topics):
            with patch.object(sys, "argv", testargs):
                from chinese_scraper_utils.__main__ import main
                main()
        captured = capsys.readouterr()
        assert "Hot Topic 1" in captured.out

    def test_scrape_weibo_empty(self, capsys):
        testargs = ["prog", "scrape-weibo"]
        with patch("chinese_scraper_utils.scrape_weibo_hot", return_value=[]):
            with patch.object(sys, "argv", testargs):
                from chinese_scraper_utils.__main__ import main
                main()
        captured = capsys.readouterr()
        assert "抓取失败" in captured.out

    def test_scrape_zhihu(self, capsys):
        from chinese_scraper_utils import HotTopic
        topics = [
            HotTopic(title="Zhihu Hot", summary="desc", url="https://z.com", source="zhihu", raw_score=50),
        ]
        testargs = ["prog", "scrape-zhihu"]
        with patch("chinese_scraper_utils.scrape_zhihu_hot", return_value=topics):
            with patch.object(sys, "argv", testargs):
                from chinese_scraper_utils.__main__ import main
                main()
        captured = capsys.readouterr()
        assert "Zhihu Hot" in captured.out

    def test_scrape_hn(self, capsys):
        from chinese_scraper_utils import HotTopic
        topics = [
            HotTopic(title="HN Post", summary="desc", url="https://hn.com", source="hn", raw_score=100),
        ]
        testargs = ["prog", "scrape-hn"]
        with patch("chinese_scraper_utils.scrape_hackernews_top", return_value=topics):
            with patch.object(sys, "argv", testargs):
                from chinese_scraper_utils.__main__ import main
                main()
        captured = capsys.readouterr()
        assert "HN Post" in captured.out


class TestExtractCommand:
    def test_extract_json_input(self, capsys):
        data = ["五一北京漫展在国家会议中心", "今天天气不错"]
        mock_events = [MagicMock(
            title="北京漫展", date="2027-05-01", city="北京", venue="国家会议中心",
            category="漫展", confidence=0.8, source_text="五一北京漫展...",
        )]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f)
            f.flush()
            fname = f.name

        try:
            with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}):
                mock_ext = MagicMock()
                mock_ext.extract.return_value = mock_events
                with patch("chinese_scraper_utils.EventExtractor", return_value=mock_ext):
                    with patch("chinese_scraper_utils.DeepSeekClient"):
                        testargs = ["prog", "extract", fname, "-c", "0.8"]
                        with patch.object(sys, "argv", testargs):
                            from chinese_scraper_utils.__main__ import main
                            main()
        finally:
            Path(fname).unlink()
        captured = capsys.readouterr()
        assert "北京漫展" in captured.out

    def test_extract_missing_api_key(self, capsys, tmp_path):
        tfile = tmp_path / "dummy.json"
        tfile.write_text('["test data"]', encoding="utf-8")
        testargs = ["prog", "extract", str(tfile)]
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(sys, "argv", testargs):
                from chinese_scraper_utils.__main__ import main
                try:
                    main()
                except SystemExit as e:
                    assert e.code == 1
        captured = capsys.readouterr()
        assert "DEEPSEEK_API_KEY" in captured.err

    def test_extract_non_json_file(self, capsys):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Line 1: 北京有漫展\nLine 2: 上海有演唱会\n")
            f.flush()
            fname = f.name

        try:
            with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}):
                mock_ext = MagicMock()
                mock_ext.extract.return_value = []
                with patch("chinese_scraper_utils.EventExtractor", return_value=mock_ext):
                    with patch("chinese_scraper_utils.DeepSeekClient"):
                        testargs = ["prog", "extract", fname]
                        with patch.object(sys, "argv", testargs):
                            from chinese_scraper_utils.__main__ import main
                            main()
        finally:
            Path(fname).unlink()
        captured = capsys.readouterr()
        assert "未提取到" in captured.out

    def test_extract_empty_input(self, capsys):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump([], f)
            f.flush()
            fname = f.name

        try:
            with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}):
                with patch("chinese_scraper_utils.DeepSeekClient"):
                    with patch("chinese_scraper_utils.EventExtractor"):
                        testargs = ["prog", "extract", fname]
                        with patch.object(sys, "argv", testargs):
                            from chinese_scraper_utils.__main__ import main
                            main()
        finally:
            Path(fname).unlink()
        captured = capsys.readouterr()
        assert "输入为空" in captured.out

    def test_extract_with_verbose(self, capsys):
        mock_events = [MagicMock(
            title="北京漫展", date="2027-05-01", city="北京", venue="国家会议中心",
            category="漫展", confidence=0.8, source_text="原文前120字",
        )]
        data = ["test"]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f)
            f.flush()
            fname = f.name

        try:
            with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}):
                mock_ext = MagicMock()
                mock_ext.extract.return_value = mock_events
                with patch("chinese_scraper_utils.EventExtractor", return_value=mock_ext):
                    with patch("chinese_scraper_utils.DeepSeekClient"):
                        testargs = ["prog", "extract", fname, "-v"]
                        with patch.object(sys, "argv", testargs):
                            from chinese_scraper_utils.__main__ import main
                            main()
        finally:
            Path(fname).unlink()
        captured = capsys.readouterr()
        assert "来源" in captured.out


class TestMainNoCommand:
    def test_no_command_prints_help(self, capsys):
        testargs = ["prog"]
        with patch.object(sys, "argv", testargs):
            from chinese_scraper_utils.__main__ import main
            try:
                main()
            except SystemExit as e:
                assert e.code == 1
        captured = capsys.readouterr()
        assert any(w in captured.out for w in ["search", "scrape", "usage", "Chinese", "中文"])
