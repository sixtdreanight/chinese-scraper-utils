"""Basic usage examples for chinese-scraper-utils."""
import asyncio

from chinese_scraper_utils import (
    stable_id,
    parse_date,
    try_parse_date,
    extract_date,
    extract_city,
    normalize_city,
    guess_category,
    random_ua,
    RateLimiter,
)


def demo_dates():
    print("=== Date Parsing ===")
    print(f"parse_date('2026-06-12'):       {parse_date('2026-06-12')}")
    print(f"parse_date('2026/06/12'):       {parse_date('2026/06/12')}")
    print(f"try_parse_date('garbage'):     {try_parse_date('garbage')}")
    print(f"extract_date('6月12日上海漫展'): {extract_date('6月12日上海漫展')}")
    print()


def demo_cities():
    print("=== City Extraction ===")
    print(f"extract_city('今天北京有漫展'):     {extract_city('今天北京有漫展')}")
    print(f"extract_city('西安路有个活动'):     {extract_city('西安路有个活动')!r}")
    # Adding extra cities
    print(f"extract_city('日喀则有活动', extra_cities=['日喀则']): {extract_city('日喀则有活动', extra_cities=['日喀则'])}")
    print(f"normalize_city('上海市'):          {normalize_city('上海市')}")
    print()


def demo_utils():
    print("=== Utilities ===")
    print(f"stable_id('post', '123'):    {stable_id('post', '123')}")
    print(f"guess_category('初音未来演唱会'): {guess_category('初音未来演唱会')}")
    print(f"guess_category('ComiCup同人展'): {guess_category('ComiCup同人展')}")
    print(f"random_ua()[:50]:           {random_ua()[:50]}...")
    print()


async def demo_rate_limit():
    """Async rate limiting example."""
    limiter = RateLimiter(min_interval=0.1)

    @limiter.limit
    async def fetch(item: str) -> str:
        return f"fetched: {item}"

    results = [await fetch(f"item-{i}") for i in range(3)]
    print("Rate-limited fetches:", results)


def main():
    demo_dates()
    demo_cities()
    demo_utils()
    print("=== Rate Limiting ===")
    asyncio.run(demo_rate_limit())


if __name__ == "__main__":
    main()
