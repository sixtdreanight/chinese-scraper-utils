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
- `_ai.py` extracted `_parse_json_content()` as reusable utility
