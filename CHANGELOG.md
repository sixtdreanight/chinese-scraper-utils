# Changelog

## v0.2.0 (2026-05-23)

### Breaking Changes
- `parse_date("")` now returns `""` instead of today's date. Callers should handle empty string.
  Use `try_parse_date()` for the new `str | None` return type.

### Bug Fixes
- `parse_date()` no longer returns garbage truncated strings for unrecognized input
- `parse_date()` fixed broken `s[:len(fmt)]` truncation logic
- `extract_city()` added false suffix blacklist to prevent "西安路"→"西安" false positives
- `RateLimiter.wait()` added `asyncio.Lock` to prevent TOCTOU race condition
- `guess_category()` now uses longest-match-first to prevent shorter keywords overriding longer ones

### New Features
- **Web Search**: `search_web()` + `SearchResult` dataclass (DuckDuckGo, optional `[search]` extra)
- **Hot Topic Scrapers**: `scrape_weibo_hot()`, `scrape_zhihu_hot()`, `scrape_hackernews_top()` + `HotTopic` dataclass
- **LLM Extraction Pipeline**: `EventExtractor` class with 5-stage pipeline (Prefilter→Domain Filter→LLM Extract→Validate&Score→Dedup)
- **Async DeepSeek Client**: `achat()`, `achat_json()` methods with built-in 429/503 retry
- **Rate Limiter Decorator**: `@limiter.limit` for cleaner async rate limiting
- **CLI**: `python -m chinese_scraper_utils search/scrape-weibo/scrape-zhihu/scrape-hn/extract`
- **Error Types**: `ScraperError`, `RateLimitError`, `ExtractionError`, `ValidationError`, `NetworkError`
- **Type Hints**: Added `py.typed` marker (PEP 561)
- `try_parse_date()` returns `str | None` for explicit null handling
- `extract_city(extra_cities=...)` supports custom city lists
- `UA_POOL` expanded from 5 to 21 entries (Chrome 134-135, Firefox 137-138, Edge 135, Safari 18, mobile)
- LLM extraction caching (keyed on text hash + model, configurable TTL)

### Improvements
- All modules now use `logging` instead of `print()`
- `RateLimiter` retry backoff now includes jitter
- `DeepSeekClient` has built-in retry on network errors and 429/503
## v0.2.1 (2026-05-24)

### Security Fixes
- **CLI extract**: Fixed `AttributeError` crash — `.read_text()` on file object replaced with `.read()` ([`__main__.py`](src/chinese_scraper_utils/__main__.py))
- **Thread safety**: HN scraper now creates per-thread `httpx.Client` to prevent data races ([`_hotspots.py`](src/chinese_scraper_utils/_hotspots.py))
- **LLM prompt injection**: User text wrapped in `<user_text>` XML boundaries + anti-injection guard in extraction prompt ([`_extractor.py`](src/chinese_scraper_utils/_extractor.py))
- **Retry coverage**: 500/502/504 status codes now retried alongside 429/503 ([`_ai.py`](src/chinese_scraper_utils/_ai.py))
- **JSON parse fallback**: Only fires non-JSON-mode retry on last attempt (halves max API calls) ([`_ai.py`](src/chinese_scraper_utils/_ai.py))
- **`stable_id` delimiter**: Pipe characters in input parts now escaped to prevent hash collisions ([`_hash.py`](src/chinese_scraper_utils/_hash.py))
- **Custom errors wired**: `RateLimitError`/`NetworkError` now raised by `RateLimiter.fetch_with_retry()` ([`_rate_limit.py`](src/chinese_scraper_utils/_rate_limit.py))

### Bug Fixes
- **User-Agent rotation**: UA now selected per-request instead of once at module import ([`_hotspots.py`](src/chinese_scraper_utils/_hotspots.py))
- **Dedup false positives**: Date proximity changed from same-month to ±3 day window; title prefix from 6→4 chars ([`_extractor.py`](src/chinese_scraper_utils/_extractor.py))
- **Cross-year dates**: `extract_date()` infers next year when month-day is >90 days past ([`_date.py`](src/chinese_scraper_utils/_date.py))
- **City false suffixes**: Multi-character suffixes (大酒店, 大学, 大厦 etc.) now blocked ([`_city.py`](src/chinese_scraper_utils/_city.py))
- **City aliases**: Added 渝/蓉/沪/鹏城/羊城/江城/泉城/榕城/鹭岛 mappings ([`_city.py`](src/chinese_scraper_utils/_city.py))
- **Text dedup**: Prefilter dedup key widened from 60→120 chars ([`_extractor.py`](src/chinese_scraper_utils/_extractor.py))
- **Title normalization**: Hyphens preserved (no longer stripped) to differentiate series suffixes ([`_extractor.py`](src/chinese_scraper_utils/_extractor.py))
- **Search rate limiting**: 3s minimum interval between DuckDuckGo searches ([`_search.py`](src/chinese_scraper_utils/_search.py))
- **JSON parsing**: `re.MULTILINE` flag added for code block detection ([`_ai.py`](src/chinese_scraper_utils/_ai.py))
