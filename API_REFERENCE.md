# API Reference — chinese-scraper-utils v0.2.0

## Core Utilities

### `parse_date(s: str) -> str`
解析结构化日期字符串，返回 `YYYY-MM-DD` 格式。无法解析返回 `""`。

| Input | Output |
|-------|--------|
| `"2026-05-04"` | `"2026-05-04"` |
| `"2026/05/04"` | `"2026-05-04"` |
| `"2026.05.04"` | `"2026-05-04"` |
| `"20260504"` | `"2026-05-04"` |
| `"2026-05-04 14:30:00"` | `"2026-05-04"` |
| `"北京国家会议中心"` | `""` |

### `try_parse_date(s: str) -> str | None`
同 `parse_date()`，但无法解析时返回 `None`。

### `extract_date(text: str) -> str`
从中文自由文本提取日期。

```python
extract_date("5月4日上海有漫展")      # "2026-05-04"
extract_date("2026年5月4日-6日")     # "2026-05-04"
```

### `extract_city(text: str, extra_cities=None) -> str`
从文本提取城市名。假后缀（路/街/道/村/区...）后的匹配会被忽略。

```python
extract_city("活动在上海举办")         # "上海"
extract_city("西安路有个活动")         # ""  (假后缀保护)
extract_city("日喀则有活动", extra_cities=["日喀则"])  # "日喀则"
```

### `normalize_city(city: str) -> str`
规范化城市名：去空格、去"市"后缀、"中国"/"全国"→空。

### `CITIES: list[str]`
50 个主要中国城市列表。

### `guess_category(title: str) -> str`
根据标题猜测活动类别。使用最长匹配优先。返回 `"漫展"|"同人展"|"演唱会"|"音乐会"|"舞台剧"|"展览"|"其他"`。

### `stable_id(*parts: str) -> str`
确定性的 SHA256 短 ID（16 hex chars），跨进程重启不变。

### `random_ua() -> str`
随机返回 21 条最新 User-Agent 中的一条。

### `UA_POOL: list[str]`
21 条 User-Agent 池（Chrome/Firefox/Edge/Safari，桌面+移动）。

---

## Web Search

### `SearchResult`
```python
@dataclass
class SearchResult:
    title: str      # 网页标题
    url: str        # 网页链接
    snippet: str    # 内容摘要
```

### `search_web(query: str, max_results: int = 10) -> list[SearchResult]`
DuckDuckGo 搜索。需要 `pip install chinese-scraper-utils[search]`。
ddgs 未安装或搜索失败时返回空列表。

---

## Hot Topic Scrapers

### `HotTopic`
```python
@dataclass
class HotTopic:
    title: str      # 话题标题
    summary: str    # 热度描述
    url: str        # 链接
    source: str     # "微博热搜" | "知乎热榜" | "Hacker News"
    raw_score: int  # 原始热度数值
```

### `scrape_weibo_hot() -> list[HotTopic]`
抓取微博实时热搜榜。

### `scrape_zhihu_hot() -> list[HotTopic]`
抓取知乎热榜。

### `scrape_hackernews_top() -> list[HotTopic]`
抓取 Hacker News 首页热门（30 条，并发获取详情）。

---

## LLM Extraction Pipeline

### `ExtractedEvent`
```python
@dataclass
class ExtractedEvent:
    title: str
    date: str
    end_date: str | None
    city: str
    venue: str
    category: str
    confidence: float       # 0.0-1.0，规则计算
    source_text: str        # 溯源：提取自哪段原文
    source_index: int       # 溯源：对应 texts 索引
```

### `EventExtractor`
```python
class EventExtractor:
    def __init__(
        self,
        client: DeepSeekClient,
        event_types: list[str],          # ["漫展", "同人展", "演唱会", ...]
        min_confidence: float = 0.5,
        temperature: float = 0.1,
        extra_cities: list[str] | None = None,
        cache_path: str | None = None,   # 缓存文件路径
        cache_ttl_days: int = 7,
    )

    def extract(
        self,
        texts: list[str],
        *,
        custom_prompt: str | None = None,
        min_score: int = 3,
    ) -> list[ExtractedEvent]

    def dry_run(
        self,
        texts: list[str],
        *,
        min_score: int = 3,
    ) -> list[dict]  # 不调 API 的预检
```

五阶段管道：
1. **Prefilter** — 噪音过滤 + 关键词打分（日期+2/城市+1/场馆+1/活动词+1）
2. **Domain Filter** — 只提取 event_types 范围内的活动
3. **LLM Extract** — DeepSeek JSON mode + temperature=0.1
4. **Validate & Score** — 规则计算 confidence（date+0.3/city+0.25/venue+0.15/category+0.15/title+0.15）
5. **Dedup** — 指纹哈希 → 模糊匹配 → 高置信覆盖

### `extract_events(texts, client, *, event_types, ...) -> list[ExtractedEvent]`
便捷函数，等价于 `EventExtractor(...).extract(texts)`。

---

## AI Client

### `DeepSeekClient`
```python
class DeepSeekClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        max_retries: int = 3,
    )

    # 同步
    def chat(self, messages, temperature=0.3, max_tokens=8192) -> str
    def chat_json(self, messages, temperature=0.3, max_tokens=8192) -> dict | list

    # 异步
    async def achat(self, messages, temperature=0.3, max_tokens=8192) -> str
    async def achat_json(self, messages, temperature=0.3, max_tokens=8192) -> dict | list
```
内置 429/503 重试（指数退避 + jitter）。`chat_json` 解析失败时自动回退重试（不加 JSON mode）。

---

## Rate Limiter

### `RateLimiter`
```python
class RateLimiter:
    def __init__(self, min_interval: float = 2.0)

    async def wait(self)                      # 等待至可发起请求
    async def fetch_with_retry(self, fetch_fn, max_retries=3)  # 请求包装器

    def limit(self, func)  # 装饰器
```

---

## Error Types

```python
ScraperError          # 基类
├── RateLimitError    # HTTP 429 / 平台限流
├── ExtractionError   # LLM 提取失败
├── ValidationError   # 数据校验失败
└── NetworkError      # 网络超时/DNS/连接错误
```

---

## CLI

```bash
# 搜索
python -m chinese_scraper_utils search "五一北京漫展" -n 5

# 抓取热点
python -m chinese_scraper_utils scrape-weibo
python -m chinese_scraper_utils scrape-zhihu
python -m chinese_scraper_utils scrape-hn

# LLM 提取 （需要 DEEPSEEK_API_KEY）
python -m chinese_scraper_utils extract posts.json -t "漫展,演唱会" -c 0.5 -v
```
