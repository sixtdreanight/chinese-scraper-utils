"""热点抓取 — 微博热搜 / 知乎热榜 / Hacker News 热门。

三个平台的数据格式差异较大，本模块统一输出 HotTopic dataclass。
所有抓取使用 httpx 同步请求，调用方可自行包装为异步。
"""

import dataclasses
import logging

import httpx

from chinese_scraper_utils._ua import random_ua
from chinese_scraper_utils.errors import ScraperError

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════════════


@dataclasses.dataclass
class HotTopic:
    """统一的热点话题数据结构。"""
    title: str
    summary: str
    url: str
    source: str       # "微博热搜" | "知乎热榜" | "Hacker News"
    raw_score: int    # 平台原始热度数值


# ═══════════════════════════════════════════════════════════════
# 微博热搜
# ═══════════════════════════════════════════════════════════════

_WEIBO_STATIC_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://weibo.com/",
    "X-Requested-With": "XMLHttpRequest",
}


def _weibo_headers():
    return {**_WEIBO_STATIC_HEADERS, "User-Agent": random_ua()}


def _weibo_item_to_topic(item: dict) -> HotTopic | None:
    word = item.get("word") or item.get("note") or item.get("title")
    if not word or word in ("实时热搜", "微博热搜", "热搜榜"):
        return None
    raw_url = item.get("scheme", "") or item.get("url", "") or ""
    url = raw_url if raw_url.startswith("http") else f"https://s.weibo.com/weibo?q={word}"
    return HotTopic(
        title=str(word).strip().lstrip("#").rstrip("#"),
        summary=f"热搜第{item.get('rank', '?')}名 · 热度 {item.get('raw_hot', item.get('hot', '?'))}",
        url=url,
        source="微博热搜",
        raw_score=item.get("raw_hot", item.get("hot", 0)) or 0,
    )


def scrape_weibo_hot() -> list[HotTopic]:
    """抓取微博实时热搜榜。

    Returns:
        HotTopic 列表。抓取失败返回空列表。
    """
    results: list[HotTopic] = []
    try:
        with httpx.Client(verify=True, follow_redirects=True) as client:
            # 先访问首页获取 cookie
            client.get("https://weibo.com/", timeout=15)
            # 再请求热搜 API
            resp = client.get(
                "https://weibo.com/ajax/side/hotSearch",
                headers=_weibo_headers(),
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning("[weibo] HTTP %s", resp.status_code)
                return []
            data = resp.json()
            items = (
                data.get("data", {}).get("realtime", [])
                or data.get("data", {}).get("hotgovs", [])
                or []
            )
            for item in items:
                topic = _weibo_item_to_topic(item)
                if topic:
                    results.append(topic)
            logger.info("[weibo] scraped %d topics", len(results))
    except Exception as e:
        logger.warning("[weibo] error: %s", e)
    return results


# ═══════════════════════════════════════════════════════════════
# 知乎热榜
# ═══════════════════════════════════════════════════════════════

_ZHIHU_STATIC_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.zhihu.com/hot",
    "Origin": "https://www.zhihu.com",
}


def _zhihu_headers():
    return {**_ZHIHU_STATIC_HEADERS, "User-Agent": random_ua()}


def scrape_zhihu_hot() -> list[HotTopic]:
    """抓取知乎热榜。

    Returns:
        HotTopic 列表。抓取失败返回空列表。
    """
    results: list[HotTopic] = []
    try:
        with httpx.Client(verify=True, follow_redirects=True) as client:
            resp = client.get(
                "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
                "?limit=50&desktop=true",
                headers=_zhihu_headers(),
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning("[zhihu] HTTP %s", resp.status_code)
                return []
            data = resp.json()
            items = data.get("data", [])
            for i, item in enumerate(items):
                target = item.get("target", {})
                title = (target.get("title") or "").strip()
                if not title:
                    continue
                url = target.get("url", "")
                if not url:
                    qid = target.get("id", "")
                    url = f"https://www.zhihu.com/question/{qid}" if qid else ""
                if url and not url.startswith("http"):
                    url = f"https://www.zhihu.com{url}"
                results.append(HotTopic(
                    title=title,
                    summary=f"知乎热榜第{i + 1}名 · {target.get('excerpt', '')[:80] or '热度话题'}",
                    url=url,
                    source="知乎热榜",
                    raw_score=target.get("heat", 0) or target.get("follower_count", 0) or 0,
                ))
            logger.info("[zhihu] scraped %d topics", len(results))
    except Exception as e:
        logger.warning("[zhihu] error: %s", e)
    return results


# ═══════════════════════════════════════════════════════════════
# Hacker News
# ═══════════════════════════════════════════════════════════════


def scrape_hackernews_top() -> list[HotTopic]:
    """抓取 Hacker News 首页热门。

    Returns:
        HotTopic 列表。抓取失败返回空列表。
    """
    results: list[HotTopic] = []
    try:
        with httpx.Client(verify=True, follow_redirects=True) as client:
            resp = client.get(
                "https://hacker-news.firebaseio.com/v0/topstories.json",
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning("[hn] HTTP %s", resp.status_code)
                return []
            ids = resp.json()[:30]

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def fetch_one(hid: int) -> HotTopic | None:
            try:
                # Each thread creates its own httpx.Client (httpx.Client is not thread-safe)
                with httpx.Client(verify=True, follow_redirects=True, timeout=httpx.Timeout(10.0)) as c:
                    item = c.get(
                        f"https://hacker-news.firebaseio.com/v0/item/{hid}.json",
                    ).json()
                title = (item.get("title") or "").strip()
                if not title:
                    return None
                url = item.get("url") or f"https://news.ycombinator.com/item?id={hid}"
                score = item.get("score", 0)
                return HotTopic(
                    title=title,
                    summary=f"HN热度 {score} · {item.get('descendants', 0)} 条评论",
                    url=url,
                    source="Hacker News",
                    raw_score=score,
                )
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {pool.submit(fetch_one, hid): hid for hid in ids}
            for future in as_completed(futures):
                item = future.result()
                if item:
                    results.append(item)

        logger.info("[hn] scraped %d topics", len(results))
    except Exception as e:
        logger.warning("[hn] error: %s", e)
    return results
