# Changelog

## v0.1.0 (2026-05-23)

### Initial release — extracted from ComiRadar and weekly-cli.

- **`stable_id`**: Deterministic SHA256 short ID generation
- **`parse_date` / `extract_date`**: Chinese date parsing and text extraction
- **`extract_city` / `normalize_city`**: City extraction and normalization for 52 major Chinese cities
- **`guess_category`**: Event category guessing from Chinese titles
- **`random_ua`**: Random User-Agent selection from a curated pool
- **`RateLimiter`**: Async rate limiter with exponential backoff retry
- **`DeepSeekClient`**: DeepSeek API client with JSON mode and fallback
