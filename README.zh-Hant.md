**語言 / Language:** [English](README.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-Hant.md) | [日本語](README.ja.md)

# chinese-scraper-utils

<p align="center">
  <img src="https://img.shields.io/pypi/v/chinese-scraper-utils" alt="PyPI version">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
</p>

中文網路爬蟲通用工具庫 — 日期解析、城市提取、穩定 ID 生成、UA 輪換、速率限制、網頁搜尋、熱榜抓取、LLM 事件提取及 DeepSeek API 用戶端。

從 [ComiRadar](https://github.com/sixtdreanight/ComiRadar) 和 [weekly-hotspot](https://github.com/sixtdreanight/weekly-hotspot) 中抽離。

---

## 安裝

```bash
# 核心功能（除 httpx + openai 外無額外依賴）
pip install chinese-scraper-utils

# 包含網頁搜尋支援
pip install chinese-scraper-utils[search]
```

---

## 快速開始

```python
from chinese_scraper_utils import (
    # 核心工具
    parse_date, extract_date, extract_city, guess_category, stable_id, random_ua,
    # 網頁搜尋
    search_web,
    # 熱榜抓取
    scrape_weibo_hot, scrape_zhihu_hot,
    # LLM 事件提取
    DeepSeekClient, EventExtractor,
)

# 中文日期解析
parse_date("2026/05/20")         # "2026-05-20"
extract_date("5月4日上海有漫展")   # "2026-05-04"

# 城市提取（防誤判）
extract_city("活動在上海舉辦")     # "上海"
extract_city("西安路有個活動")     # ""（不是城市！）

# 熱榜抓取
weibo = scrape_weibo_hot()       # list[HotTopic]
zhihu = scrape_zhihu_hot()       # list[HotTopic]

# LLM 驅動事件提取
client = DeepSeekClient(api_key="sk-xxx")
extractor = EventExtractor(
    client=client,
    event_types=["漫展", "同人展", "演唱會"],
    min_confidence=0.5,
)
events = extractor.extract(["五一北京漫展嘉年華在國家會議中心..."])

# 命令列用法
# python -m chinese_scraper_utils search "五一漫展"
# python -m chinese_scraper_utils scrape-weibo
# python -m chinese_scraper_utils extract posts.json -t "漫展,演唱會"
```

---

## API 參考

| 匯出項 | 類型 | 說明 |
|--------|------|------|
| `parse_date(s)` | `str → str` | 結構化日期解析 |
| `try_parse_date(s)` | `str → str\|None` | 同上，失敗返回 None |
| `extract_date(text)` | `str → str` | 中文文字日期提取 |
| `CITIES` | `list[str]` | 50 個中國主要城市 |
| `extract_city(text, extra_cities=None)` | `str → str` | 城市名稱提取（防誤判） |
| `normalize_city(city)` | `str → str` | 城市名稱標準化 |
| `CATEGORY_ALIASES` | `dict[str,str]` | 分類別名映射 |
| `guess_category(title)` | `str → str` | 活動分類推測（最長匹配） |
| `UA_POOL` | `list[str]` | 21 個現代 User-Agent 字串 |
| `random_ua()` | `→ str` | 隨機 UA 選擇 |
| `stable_id(*parts)` | `str → str` | 確定性 SHA256 短 ID |
| `RateLimiter` | class | 非同步速率限制器（重試 + 抖動） |
| `DeepSeekClient` | class | DeepSeek API 用戶端（同步/非同步，重試） |
| **新** `SearchResult` | dataclass | 網頁搜尋結果（標題/URL/摘要） |
| **新** `search_web(query, n)` | `→ list[SearchResult]` | DuckDuckGo 網頁搜尋 |
| **新** `HotTopic` | dataclass | 統一熱榜條目（標題/摘要/URL/來源） |
| **新** `scrape_weibo_hot()` | `→ list[HotTopic]` | 微博熱搜 |
| **新** `scrape_zhihu_hot()` | `→ list[HotTopic]` | 知乎熱榜 |
| **新** `scrape_hackernews_top()` | `→ list[HotTopic]` | HN 頭條 |
| **新** `ExtractedEvent` | dataclass | 結構化事件（含來源追溯） |
| **新** `EventExtractor` | class | 5 階段 LLM 提取管線 + 快取 |
| **新** `extract_events(texts, ...)` | `→ list[ExtractedEvent]` | 便捷提取函數 |
| `ScraperError` / `RateLimitError` / 等 | 例外類別 | 型別化錯誤階層結構 |

完整 API 文件: [API_REFERENCE.md](API_REFERENCE.md)

---

## 命令列

```bash
python -m chinese_scraper_utils search "五一北京漫展" -n 10
python -m chinese_scraper_utils scrape-weibo
python -m chinese_scraper_utils scrape-zhihu
python -m chinese_scraper_utils scrape-hn
python -m chinese_scraper_utils extract posts.json -t "漫展,演唱會" -c 0.5 -v
```

---

## 相關專案

- [ComiRadar](https://github.com/sixtdreanight/ComiRadar) — 動漫活動爬蟲，使用了本工具庫
- [weekly-hotspot](https://github.com/sixtdreanight/weekly-hotspot) — 每週熱點深度分析

## 授權條款

[MIT](LICENSE)

---

<div align="center">

**Language / 语言 / 言語**

[**English**](README.md) | [**简体中文**](README.zh-CN.md) | [**繁體中文**](README.zh-Hant.md) | [**日本語**](README.ja.md)

</div>
