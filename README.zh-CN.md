**语言 / Language:** [English](README.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-Hant.md) | [日本語](README.ja.md)

# chinese-scraper-utils

<p align="center">
  <img src="https://img.shields.io/pypi/v/chinese-scraper-utils" alt="PyPI version">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
</p>

中文网络爬虫通用工具库 — 日期解析、城市提取、稳定 ID 生成、UA 轮换、速率限制、网页搜索、热榜抓取、LLM 事件提取及 DeepSeek API 客户端。

从 [ComiRadar](https://github.com/sixtdreanight/ComiRadar) 和 [weekly-hotspot](https://github.com/sixtdreanight/weekly-hotspot) 中抽离。

---

## 安装

```bash
# 核心功能（除 httpx + openai 外无额外依赖）
pip install chinese-scraper-utils

# 包含网页搜索支持
pip install chinese-scraper-utils[search]
```

---

## 快速开始

```python
from chinese_scraper_utils import (
    # 核心工具
    parse_date, extract_date, extract_city, guess_category, stable_id, random_ua,
    # 网页搜索
    search_web,
    # 热榜抓取
    scrape_weibo_hot, scrape_zhihu_hot,
    # LLM 事件提取
    DeepSeekClient, EventExtractor,
)

# 中文日期解析
parse_date("2026/05/20")         # "2026-05-20"
extract_date("5月4日上海有漫展")   # "2026-05-04"

# 城市提取（防误判）
extract_city("活动在上海举办")     # "上海"
extract_city("西安路有个活动")     # ""（不是城市！）

# 热榜抓取
weibo = scrape_weibo_hot()       # list[HotTopic]
zhihu = scrape_zhihu_hot()       # list[HotTopic]

# LLM 驱动事件提取
client = DeepSeekClient(api_key="sk-xxx")
extractor = EventExtractor(
    client=client,
    event_types=["漫展", "同人展", "演唱会"],
    min_confidence=0.5,
)
events = extractor.extract(["五一北京漫展嘉年华在国家会议中心..."])

# 命令行用法
# python -m chinese_scraper_utils search "五一漫展"
# python -m chinese_scraper_utils scrape-weibo
# python -m chinese_scraper_utils extract posts.json -t "漫展,演唱会"
```

---

## API 参考

| 导出项 | 类型 | 说明 |
|--------|------|------|
| `parse_date(s)` | `str → str` | 结构化日期解析 |
| `try_parse_date(s)` | `str → str\|None` | 同上，失败返回 None |
| `extract_date(text)` | `str → str` | 中文文本日期提取 |
| `CITIES` | `list[str]` | 50 个中国主要城市 |
| `extract_city(text, extra_cities=None)` | `str → str` | 城市名称提取（防误判） |
| `normalize_city(city)` | `str → str` | 城市名称标准化 |
| `CATEGORY_ALIASES` | `dict[str,str]` | 分类别名映射 |
| `guess_category(title)` | `str → str` | 活动分类推测（最长匹配） |
| `UA_POOL` | `list[str]` | 21 个现代 User-Agent 字符串 |
| `random_ua()` | `→ str` | 随机 UA 选择 |
| `stable_id(*parts)` | `str → str` | 确定性 SHA256 短 ID |
| `RateLimiter` | class | 异步速率限制器（重试 + 抖动） |
| `DeepSeekClient` | class | DeepSeek API 客户端（同步/异步，重试） |
| **新** `SearchResult` | dataclass | 网页搜索结果（标题/URL/摘要） |
| **新** `search_web(query, n)` | `→ list[SearchResult]` | DuckDuckGo 网页搜索 |
| **新** `HotTopic` | dataclass | 统一热榜条目（标题/摘要/URL/来源） |
| **新** `scrape_weibo_hot()` | `→ list[HotTopic]` | 微博热搜 |
| **新** `scrape_zhihu_hot()` | `→ list[HotTopic]` | 知乎热榜 |
| **新** `scrape_hackernews_top()` | `→ list[HotTopic]` | HN 头条 |
| **新** `ExtractedEvent` | dataclass | 结构化事件（含来源追溯） |
| **新** `EventExtractor` | class | 5 阶段 LLM 提取管道 + 缓存 |
| **新** `extract_events(texts, ...)` | `→ list[ExtractedEvent]` | 便捷提取函数 |
| `ScraperError` / `RateLimitError` / 等 | 异常类 | 类型化错误层次结构 |

完整 API 文档: [API_REFERENCE.md](API_REFERENCE.md)

---

## 命令行

```bash
python -m chinese_scraper_utils search "五一北京漫展" -n 10
python -m chinese_scraper_utils scrape-weibo
python -m chinese_scraper_utils scrape-zhihu
python -m chinese_scraper_utils scrape-hn
python -m chinese_scraper_utils extract posts.json -t "漫展,演唱会" -c 0.5 -v
```

---

## 相关项目

- [ComiRadar](https://github.com/sixtdreanight/ComiRadar) — 动漫活动爬虫，使用了本工具库
- [weekly-hotspot](https://github.com/sixtdreanight/weekly-hotspot) — 每周热点深度分析

## 许可证

[MIT](LICENSE)

---

<div align="center">

**Language / 语言**

[**English**](README.md) | [**简体中文**](README.zh-CN.md)

</div>
