"""chinese-scraper-utils — 中文信息抓取共享工具集。

提供中文日期解析、城市提取、SHA256 稳定 ID、UA 池、
速率限制、DeepSeek API 客户端等。
"""

from chinese_scraper_utils._hash import stable_id
from chinese_scraper_utils._date import parse_date, extract_date
from chinese_scraper_utils._city import CITIES, extract_city, normalize_city

from chinese_scraper_utils._ua import UA_POOL, random_ua
from chinese_scraper_utils._rate_limit import RateLimiter
from chinese_scraper_utils._ai import DeepSeekClient

__all__ = [
    "stable_id",
    "parse_date",
    "extract_date",
    "CITIES",
    "extract_city",
    "normalize_city",
    "UA_POOL",
    "random_ua",
    "RateLimiter",
    "DeepSeekClient",
]
