"""chinese-scraper-utils CLI — python -m chinese_scraper_utils <command>

Commands:
    search <query>           DuckDuckGo 搜索
    scrape-weibo            抓取微博热搜
    scrape-zhihu            抓取知乎热榜
    scrape-hn               抓取 Hacker News 热门
    extract <file>          从 JSON 文本文件提取活动信息
"""

import argparse
import json
import sys


def _cmd_search(args):
    from chinese_scraper_utils import search_web

    results = search_web(args.query, max_results=args.max)
    if not results:
        print("(无结果或搜索失败)")
        return
    for i, r in enumerate(results, 1):
        print(f"[{i}] {r.title}")
        print(f"    {r.url}")
        print(f"    {r.snippet}")
        print()


def _cmd_scrape_weibo(args):
    from chinese_scraper_utils import scrape_weibo_hot

    topics = scrape_weibo_hot()
    if not topics:
        print("(抓取失败或热搜为空)")
        return
    for i, t in enumerate(topics, 1):
        print(f"{i:2d}. {t.title}")
        print(f"    {t.summary}  |  {t.url}")


def _cmd_scrape_zhihu(args):
    from chinese_scraper_utils import scrape_zhihu_hot

    topics = scrape_zhihu_hot()
    if not topics:
        print("(抓取失败或热榜为空)")
        return
    for i, t in enumerate(topics, 1):
        print(f"{i:2d}. {t.title}")
        print(f"    {t.summary}  |  {t.url}")


def _cmd_scrape_hn(args):
    from chinese_scraper_utils import scrape_hackernews_top

    topics = scrape_hackernews_top()
    if not topics:
        print("(抓取失败或热门为空)")
        return
    for i, t in enumerate(topics, 1):
        print(f"{i:2d}. {t.title}")
        print(f"    {t.summary}  |  {t.url}")


def _cmd_extract(args):
    from chinese_scraper_utils import EventExtractor, DeepSeekClient
    import os

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("错误: 请设置 DEEPSEEK_API_KEY 环境变量", file=sys.stderr)
        sys.exit(1)

    input_path = args.input
    try:
        texts = json.loads(input_path.read())
    except FileNotFoundError:
        print(f"错误: 文件不存在 — {args.input}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        # 尝试按纯文本读取（每行一条）
        input_path.seek(0)
        texts = input_path.read().strip().split("\n")
        texts = [t for t in texts if t.strip()]

    if not texts:
        print("(输入为空)")
        return

    event_types = [t.strip() for t in (args.types or "漫展,同人展,演唱会,音乐会,展览").split(",")]

    client = DeepSeekClient(api_key=api_key)
    extractor = EventExtractor(
        client=client,
        event_types=event_types,
        min_confidence=args.min_confidence,
    )
    events = extractor.extract(texts)

    if not events:
        print("(未提取到活动信息)")
        return

    for i, e in enumerate(events, 1):
        print(f"[{i}] {e.title}")
        print(f"    日期: {e.date}  |  城市: {e.city or '未知'}  |  场馆: {e.venue or '未知'}")
        print(f"    类别: {e.category}  |  置信度: {e.confidence:.0%}")
        if args.verbose:
            print(f"    来源: {e.source_text[:120]}")
        print()


def main():
    parser = argparse.ArgumentParser(
        prog="chinese-scraper-utils",
        description="中文信息抓取工具集",
    )
    sub = parser.add_subparsers(dest="command")

    # search
    p = sub.add_parser("search", help="DuckDuckGo 搜索")
    p.add_argument("query", help="搜索关键词")
    p.add_argument("-n", "--max", type=int, default=10, help="最大结果数")
    p.set_defaults(func=_cmd_search)

    # scrape-weibo
    p = sub.add_parser("scrape-weibo", help="抓取微博热搜")
    p.set_defaults(func=_cmd_scrape_weibo)

    # scrape-zhihu
    p = sub.add_parser("scrape-zhihu", help="抓取知乎热榜")
    p.set_defaults(func=_cmd_scrape_zhihu)

    # scrape-hn
    p = sub.add_parser("scrape-hn", help="抓取 Hacker News 热门")
    p.set_defaults(func=_cmd_scrape_hn)

    # extract
    p = sub.add_parser("extract", help="从文本提取活动信息")
    p.add_argument("input", type=argparse.FileType("r", encoding="utf-8"),
                   help="JSON 文本列表文件（或每行一条的文本文件）")
    p.add_argument("-t", "--types", help="活动类型，逗号分隔（默认: 漫展,同人展,演唱会,音乐会,展览）")
    p.add_argument("-c", "--min-confidence", type=float, default=0.5, help="最低置信度（默认: 0.5）")
    p.add_argument("-v", "--verbose", action="store_true", help="显示来源文本")
    p.set_defaults(func=_cmd_extract)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
