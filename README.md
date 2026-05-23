# chinese-scraper-utils

<p align="center">
  <img src="https://img.shields.io/pypi/v/chinese-scraper-utils" alt="PyPI version">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
</p>

Shared Python utilities for Chinese-language web scraping — date parsing, city extraction, stable ID generation, UA rotation, rate limiting, web search, hot topic scrapers, LLM-powered event extraction, and a DeepSeek API client.

Extracted from [ComiRadar](https://github.com/sixtdreanight/ComiRadar) and [weekly-hotspot](https://github.com/sixtdreanight/weekly-hotspot).

---

## Installation / 安装

```bash
# Core (zero extra dependencies beyond httpx + openai)
pip install chinese-scraper-utils

# With web search support
pip install chinese-scraper-utils[search]
```

---

## Quick Start / 快速开始

```python
from chinese_scraper_utils import (
    # Core utilities
    parse_date, extract_date, extract_city, guess_category, stable_id, random_ua,
    # Web search
    search_web,
    # Hot topic scrapers
    scrape_weibo_hot, scrape_zhihu_hot,
    # LLM extraction
    DeepSeekClient, EventExtractor,
)

# Parse Chinese dates
parse_date("2026/05/20")         # "2026-05-20"
extract_date("5月4日上海有漫展")   # "2026-05-04"

# Extract cities (false-positive protected)
extract_city("活动在上海举办")     # "上海"
extract_city("西安路有个活动")     # "" (not a city!)

# Scrape hot topics
weibo = scrape_weibo_hot()       # list[HotTopic]
zhihu = scrape_zhihu_hot()       # list[HotTopic]

# LLM-powered event extraction
client = DeepSeekClient(api_key="sk-xxx")
extractor = EventExtractor(
    client=client,
    event_types=["漫展", "同人展", "演唱会"],
    min_confidence=0.5,
)
events = extractor.extract(["五一北京漫展嘉年华在国家会议中心..."])

# CLI usage
# python -m chinese_scraper_utils search "五一漫展"
# python -m chinese_scraper_utils scrape-weibo
# python -m chinese_scraper_utils extract posts.json -t "漫展,演唱会"
```

---

## API Reference / API 参考

| Export / 导出项 | Type | Description |
|-----------------|------|-------------|
| `parse_date(s)` | `str → str` | Structured date parsing |
| `try_parse_date(s)` | `str → str\|None` | Same, returns None on failure |
| `extract_date(text)` | `str → str` | Chinese text date extraction |
| `CITIES` | `list[str]` | 50 major Chinese cities |
| `extract_city(text, extra_cities=None)` | `str → str` | City name extraction (false-positive safe) |
| `normalize_city(city)` | `str → str` | City name normalization |
| `CATEGORY_ALIASES` | `dict[str,str]` | Category alias mapping |
| `guess_category(title)` | `str → str` | Event category guessing (longest-match) |
| `UA_POOL` | `list[str]` | 21 modern User-Agent strings |
| `random_ua()` | `→ str` | Random UA selection |
| `stable_id(*parts)` | `str → str` | Deterministic SHA256 short ID |
| `RateLimiter` | class | Async rate limiter with retry + jitter |
| `DeepSeekClient` | class | DeepSeek API client (sync/async, retry) |
| **NEW** `SearchResult` | dataclass | Web search result (title/url/snippet) |
| **NEW** `search_web(query, n)` | `→ list[SearchResult]` | DuckDuckGo web search |
| **NEW** `HotTopic` | dataclass | Unified hot topic (title/summary/url/source) |
| **NEW** `scrape_weibo_hot()` | `→ list[HotTopic]` | Weibo hot search |
| **NEW** `scrape_zhihu_hot()` | `→ list[HotTopic]` | Zhihu hot list |
| **NEW** `scrape_hackernews_top()` | `→ list[HotTopic]` | HN top stories |
| **NEW** `ExtractedEvent` | dataclass | Structured event (with source tracing) |
| **NEW** `EventExtractor` | class | 5-stage LLM extraction pipeline + cache |
| **NEW** `extract_events(texts, ...)` | `→ list[ExtractedEvent]` | Convenience extractor |
| `ScraperError` / `RateLimitError` / etc. | Exception classes | Typed error hierarchy |

Full API docs: [API_REFERENCE.md](API_REFERENCE.md)

---

## CLI / 命令行

```bash
python -m chinese_scraper_utils search "五一北京漫展" -n 10
python -m chinese_scraper_utils scrape-weibo
python -m chinese_scraper_utils scrape-zhihu
python -m chinese_scraper_utils scrape-hn
python -m chinese_scraper_utils extract posts.json -t "漫展,演唱会" -c 0.5 -v
```

---

## Related / 相关项目

- [ComiRadar](https://github.com/sixtdreanight/ComiRadar) — Anime event scraper using this library
- [weekly-hotspot](https://github.com/sixtdreanight/weekly-hotspot) — Weekly hot topics analysis

## License / 许可证

[MIT](LICENSE)
