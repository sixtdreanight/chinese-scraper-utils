"""Web 搜索封装 — DuckDuckGo（免费，无需 API Key）。

依赖: ddgs (optional, pip install chinese-scraper-utils[search])
"""

import dataclasses
import logging

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class SearchResult:
    """网页搜索结果。"""
    title: str
    url: str
    snippet: str


def search_web(query: str, max_results: int = 10) -> list[SearchResult]:
    """用 DuckDuckGo 搜索网页，返回结构化结果列表。

    Args:
        query: 搜索关键词。
        max_results: 最大返回结果数。

    Returns:
        SearchResult 列表。ddgs 未安装或搜索失败时返回空列表。
    """
    if not query.strip():
        return []

    try:
        from ddgs import DDGS
    except ImportError:
        logger.warning(
            "ddgs not installed. Install with: pip install chinese-scraper-utils[search]"
        )
        return []

    results: list[SearchResult] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", r.get("url", "")),
                    snippet=r.get("body", r.get("snippet", "")),
                ))
    except Exception as e:
        logger.warning("Search failed for query=%r: %s", query, e)

    return results
