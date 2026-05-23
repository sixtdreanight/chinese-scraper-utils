"""cn-scraper-utils — 中文信息抓取共享工具集。

提供中文日期解析、城市提取、SHA256 稳定 ID、UA 池、
速率限制、DeepSeek API 客户端等。
"""

from cn_scraper_utils._hash import stable_id
from cn_scraper_utils._date import parse_date, extract_date
from cn_scraper_utils._city import CITIES, extract_city, normalize_city
from cn_scraper_utils._category import CATEGORY_ALIASES, guess_category
from cn_scraper_utils._ua import UA_POOL, random_ua
from cn_scraper_utils._rate_limit import RateLimiter
from cn_scraper_utils._ai import DeepSeekClient

__all__ = [
    "stable_id",
    "parse_date",
    "extract_date",
    "CITIES",
    "extract_city",
    "normalize_city",
    "CATEGORY_ALIASES",
    "guess_category",
    "UA_POOL",
    "random_ua",
    "RateLimiter",
    "DeepSeekClient",
]
