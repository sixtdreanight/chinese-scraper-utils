**言語 / Language:** [English](README.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-Hant.md) | [日本語](README.ja.md)

# chinese-scraper-utils

<p align="center">
  <img src="https://img.shields.io/pypi/v/chinese-scraper-utils" alt="PyPI version">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
</p>

中国語 Web スクレイピング用汎用ツールライブラリ — 日付解析、都市抽出、安定 ID 生成、UA ローテーション、レート制限、Web 検索、ホットランキング取得、LLM イベント抽出、DeepSeek API クライアント。

[ComiRadar](https://github.com/sixtdreanight/ComiRadar) および [weekly-hotspot](https://github.com/sixtdreanight/weekly-hotspot) から抽出されました。

---

## インストール

```bash
# コア機能（httpx + openai 以外に追加依存関係なし）
pip install chinese-scraper-utils

# Web 検索サポートを含む
pip install chinese-scraper-utils[search]
```

---

## クイックスタート

```python
from chinese_scraper_utils import (
    # コアツール
    parse_date, extract_date, extract_city, guess_category, stable_id, random_ua,
    # Web 検索
    search_web,
    # ホットランキング取得
    scrape_weibo_hot, scrape_zhihu_hot,
    # LLM イベント抽出
    DeepSeekClient, EventExtractor,
)

# 中国語日付解析
parse_date("2026/05/20")         # "2026-05-20"
extract_date("5月4日上海有漫展")   # "2026-05-04"

# 都市抽出（誤判定防止）
extract_city("活動在上海舉辦")     # "上海"
extract_city("西安路有個活動")     # ""（都市ではありません！）

# ホットランキング取得
weibo = scrape_weibo_hot()       # list[HotTopic]
zhihu = scrape_zhihu_hot()       # list[HotTopic]

# LLM 駆動イベント抽出
client = DeepSeekClient(api_key="sk-xxx")
extractor = EventExtractor(
    client=client,
    event_types=["漫展", "同人展", "演唱會"],
    min_confidence=0.5,
)
events = extractor.extract(["五一北京漫展嘉年華在國家會議中心..."])

# コマンドラインでの使用例
# python -m chinese_scraper_utils search "五一漫展"
# python -m chinese_scraper_utils scrape-weibo
# python -m chinese_scraper_utils extract posts.json -t "漫展,演唱會"
```

---

## API リファレンス

| エクスポート | 型 | 説明 |
|--------|------|------|
| `parse_date(s)` | `str → str` | 構造化日付解析 |
| `try_parse_date(s)` | `str → str\|None` | 同上、失敗時は None を返す |
| `extract_date(text)` | `str → str` | 中国語テキストからの日付抽出 |
| `CITIES` | `list[str]` | 中国の主要 50 都市 |
| `extract_city(text, extra_cities=None)` | `str → str` | 都市名抽出（誤判定防止） |
| `normalize_city(city)` | `str → str` | 都市名の正規化 |
| `CATEGORY_ALIASES` | `dict[str,str]` | カテゴリ別名マッピング |
| `guess_category(title)` | `str → str` | アクティビティカテゴリ推測（最長一致） |
| `UA_POOL` | `list[str]` | 21 個の最新 User-Agent 文字列 |
| `random_ua()` | `→ str` | ランダム UA 選択 |
| `stable_id(*parts)` | `str → str` | 決定論的 SHA256 短 ID |
| `RateLimiter` | class | 非同期レート制限器（リトライ + ジッター） |
| `DeepSeekClient` | class | DeepSeek API クライアント（同期/非同期、リトライ） |
| **新** `SearchResult` | dataclass | Web 検索結果（タイトル/URL/概要） |
| **新** `search_web(query, n)` | `→ list[SearchResult]` | DuckDuckGo Web 検索 |
| **新** `HotTopic` | dataclass | 統一ホットランキングエントリ（タイトル/概要/URL/ソース） |
| **新** `scrape_weibo_hot()` | `→ list[HotTopic]` | Weibo ホット検索 |
| **新** `scrape_zhihu_hot()` | `→ list[HotTopic]` | 知乎ホットランキング |
| **新** `scrape_hackernews_top()` | `→ list[HotTopic]` | HN トップ記事 |
| **新** `ExtractedEvent` | dataclass | 構造化イベント（ソーストレース付き） |
| **新** `EventExtractor` | class | 5 段階 LLM 抽出パイプライン + キャッシュ |
| **新** `extract_events(texts, ...)` | `→ list[ExtractedEvent]` | 簡便抽出関数 |
| `ScraperError` / `RateLimitError` / など | 例外クラス | 型付けされたエラー階層 |

完全な API ドキュメント: [API_REFERENCE.md](API_REFERENCE.md)

---

## コマンドライン

```bash
python -m chinese_scraper_utils search "五一北京漫展" -n 10
python -m chinese_scraper_utils scrape-weibo
python -m chinese_scraper_utils scrape-zhihu
python -m chinese_scraper_utils scrape-hn
python -m chinese_scraper_utils extract posts.json -t "漫展,演唱會" -c 0.5 -v
```

---

## 関連プロジェクト

- [ComiRadar](https://github.com/sixtdreanight/ComiRadar) — アニメイベントクローラー、本ライブラリを使用
- [weekly-hotspot](https://github.com/sixtdreanight/weekly-hotspot) — 週間ホットトピックの詳細分析

## ライセンス

[MIT](LICENSE)

---

<div align="center">

**Language / 语言 / 言語**

[**English**](README.md) | [**简体中文**](README.zh-CN.md) | [**繁體中文**](README.zh-Hant.md) | [**日本語**](README.ja.md)

</div>
