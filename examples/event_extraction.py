"""LLM-powered event extraction example.

Requires: DEEPSEEK_API_KEY environment variable.
"""
import os
import sys

from chinese_scraper_utils import DeepSeekClient, EventExtractor


def main():
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("Set DEEPSEEK_API_KEY environment variable to run this example.", file=sys.stderr)
        sys.exit(1)

    # Progress callback for CLI feedback
    def progress(msg: str, current: int, total: int) -> None:
        print(f"  [{current}/{total}] {msg}")

    client = DeepSeekClient(api_key=api_key, model="deepseek-v4-flash")
    extractor = EventExtractor(
        client=client,
        event_types=["漫展", "同人展", "演唱会", "展览"],
        min_confidence=0.5,
        progress_callback=progress,
    )

    texts = [
        "五一北京国家会议中心有ComiCup同人展，5月1日到3日举办",
        "上海梅赛德斯奔驰文化中心6月15日有初音未来演唱会，门票已开售",
        "广州琶洲展馆7月漫展嘉年华，超过200个摊位",
        "今天天气不错出去玩了一趟",  # will be filtered by prefilter
    ]

    # Preview before API call
    print("=== Dry Run ===")
    preview = extractor.dry_run(texts)
    for item in preview:
        print(f"  [{item['index']}] score={item['score']}: {item['text']}")
    print(f"  → {len(preview)} texts will be sent to LLM\n")

    # Full extraction
    print("=== Extracting ===")
    events = extractor.extract(texts)

    for e in events:
        print(f"  [{e.category}] {e.title}")
        print(f"    {e.date} @ {e.city or '?'} — {e.venue or '?'}")
        print(f"    confidence: {e.confidence:.0%}")
        print()
        if e.source_text:
            print(f'    source: "{e.source_text[:100]}..."')
            print()


if __name__ == "__main__":
    main()
