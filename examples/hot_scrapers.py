"""Hot topic scraping examples — Weibo, Zhihu, Hacker News."""

from chinese_scraper_utils import (
    scrape_weibo_hot,
    scrape_zhihu_hot,
    scrape_hackernews_top,
    list_scrapers,
    scrape_all,
    HotTopic,
)


def print_topics(source: str, topics: list[HotTopic], n: int = 5) -> None:
    print(f"\n=== {source} (top {min(n, len(topics))}) ===")
    for topic in topics[:n]:
        print(f"  {topic.title}")
        print(f"    {topic.summary}")
        print(f"    {topic.url}")
        print()


def main():
    # Show registered scrapers
    print("Registered scrapers:", list_scrapers())

    # Individual scraping
    print_topics("Weibo Hot Search", scrape_weibo_hot())
    print_topics("Zhihu Hot List", scrape_zhihu_hot())
    print_topics("Hacker News", scrape_hackernews_top())

    # Bulk scrape all — useful for scheduled jobs
    # all_results = scrape_all()
    # for name, topics in all_results.items():
    #     print(f"{name}: {len(topics)} topics")


if __name__ == "__main__":
    main()
