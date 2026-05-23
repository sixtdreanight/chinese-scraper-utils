# cn-scraper-utils

<p align="center">
  <img src="https://img.shields.io/pypi/v/cn-scraper-utils" alt="PyPI version">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
</p>

Shared Python utilities for Chinese-language web scraping — date parsing, city extraction, stable ID generation, UA rotation, rate limiting, and a DeepSeek API client. Extracted from [ComiRadar](https://github.com/sixtdreanight/ComiRadar) and `weekly-cli`, where these functions had diverged across two codebases.

从 [ComiRadar](https://github.com/sixtdreanight/ComiRadar) 与 `weekly-cli` 中提取的共享 Python 工具集：中文日期解析、城市提取、稳定 ID 生成、UA 池、速率限制、DeepSeek 客户端。

---

## Installation / 安装

```bash
pip install cn-scraper-utils
```

---

## Usage / 使用示例

### Stable ID / 稳定 ID

```python
from cn_scraper_utils import stable_id

uid = stable_id("北京国际动漫展", "北京", "2026-05-04")
# => "3a8f1c9e2d4b6a05"  (SHA256 hex prefix, deterministic across restarts)
```

### Date Parsing / 日期解析

```python
from cn_scraper_utils import parse_date, extract_date

# Structured date parsing / 结构化日期解析
parse_date("2026-05-04")           # => "2026-05-04"
parse_date("2026/05/04 14:30:00")  # => "2026-05-04"

# Chinese text date extraction / 中文文本日期提取
extract_date("5月4日上海有漫展")       # => "2026-05-04"
extract_date("2026年5月4日-6日")      # => "2026-05-04"
```

### City Extraction & Normalization / 城市提取与规范化

```python
from cn_scraper_utils import extract_city, normalize_city, CITIES

extract_city("活动在上海举办")      # => "上海"
extract_city("广州天河区")         # => "广州"

normalize_city("上海市")           # => "上海"
normalize_city("  深圳市  ")       # => "深圳"
```

### Category Guessing / 类别猜测

```python
from cn_scraper_utils import guess_category

guess_category("五一漫展嘉年华")   # => "漫展"
guess_category("初音未来演唱会")   # => "演唱会"
guess_category("清明上河图展览")   # => "展览"
```

### Random User-Agent / 随机 UA

```python
from cn_scraper_utils import random_ua, UA_POOL

random_ua()  # => "Mozilla/5.0 (Windows NT 10.0; ..."
```

### Async Rate Limiter / 异步速率限制

```python
import asyncio
from cn_scraper_utils import RateLimiter

limiter = RateLimiter(min_interval=1.0)

async def fetch():
    async with httpx.AsyncClient() as client:
        resp = await limiter.fetch_with_retry(
            lambda: client.get("https://example.com")
        )
        return resp.text
```

### DeepSeek AI Client / DeepSeek AI 客户端

```python
from cn_scraper_utils import DeepSeekClient

client = DeepSeekClient(api_key="sk-xxx")
result = client.chat_json([
    {"role": "user", "content": "提取活动信息：北京五一漫展"}
])
# => {"name": "...", "date": "...", "city": "..."}
```

---

## API Reference / API 参考

| Export / 导出项          | Type / 类型         | Description / 描述                                           |
|--------------------------|---------------------|---------------------------------------------------------------|
| `stable_id(*parts)`      | `str` → `str`       | Deterministic SHA256 short ID / 确定性 SHA256 短 ID           |
| `parse_date(s)`          | `str` → `str`       | Structured date parsing / 结构化日期解析                      |
| `extract_date(text)`     | `str` → `str`       | Chinese text date extraction / 中文文本日期提取                |
| `CITIES`                 | `list[str]`         | 52 major Chinese cities / 52 个主要中国城市                    |
| `extract_city(text)`     | `str` → `str`       | Chinese city name extraction / 城市名提取                      |
| `normalize_city(city)`   | `str` → `str`       | City name normalization (strip suffix) / 城市名规范化          |
| `CATEGORY_ALIASES`       | `dict[str, str]`    | Category alias mapping / 类别别名映射                          |
| `guess_category(title)`  | `str` → `str`       | Category guessing from title / 根据标题猜测类别                |
| `UA_POOL`                | `list[str]`         | User-Agent pool / User-Agent 池                                |
| `random_ua()`            | ` → `str`           | Random UA selection / 随机返回 UA                              |
| `RateLimiter`            | class               | Async rate limiter with retry / 异步速率限制器                  |
| `DeepSeekClient`         | class               | DeepSeek API wrapper / DeepSeek API 封装客户端                  |

---

## License / 许可证

[MIT](LICENSE)
