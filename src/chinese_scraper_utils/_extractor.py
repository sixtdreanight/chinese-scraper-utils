"""LLM 驱动的结构化事件提取管道 — 对标 Google LangExtract 五阶段管道。

管道: Prefilter → Domain Filter → LLM Extract → Validate & Score → Dedup
每个阶段独立可测试。EventExtractor 类封装了完整的管道配置。
"""

import dataclasses
import hashlib
import json
import logging
import re
from pathlib import Path

from chinese_scraper_utils._ai import DeepSeekClient
from chinese_scraper_utils._city import CITIES
from chinese_scraper_utils._date import parse_date
from chinese_scraper_utils._category import guess_category

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════════════


@dataclasses.dataclass
class ExtractedEvent:
    """LLM 提取的结构化活动信息。"""
    title: str
    date: str
    end_date: str | None = None
    city: str = ""
    venue: str = ""
    category: str = ""
    confidence: float = 0.0       # 规则计算，非 LLM 随口说
    source_text: str = ""         # 溯源：从原文哪段话提取
    source_index: int = -1        # 溯源：对应 texts 的索引


# ═══════════════════════════════════════════════════════════════
# Stage 1: Prefilter — 噪音过滤 + 关键词打分
# ═══════════════════════════════════════════════════════════════

# 噪音模式：纯闲聊、返图、自拍等不含活动信息的帖子
_NOISE_PATTERNS: list[re.Pattern] = [
    re.compile(p) for p in [
        r"返图", r"自拍", r"面基", r"集邮", r"扩列", r"求扩",
        r"#.*?#", r"超话", r"coser", r"好开心", r"玩得",
    ]
]

# 活动关键词（按权重）
_EVENT_KEYWORDS = [
    "漫展", "同人展", "演唱会", "音乐会", "舞台剧", "展览", "嘉年华",
    "见面会", "ComiCup", "CP展", "ONLY", "萤火虫", "ChinaJoy",
    "IJOY", "BW", "BML", "CCG", "IDO", "Live", "live",
]

# 场馆关键词
_VENUE_KEYWORDS = [
    "会展中心", "展览中心", "国际博览中心", "展览馆", "体育馆", "大剧院",
    "剧院", "艺术中心", "文化中心", "会议中心", "美术馆", "博物馆", "博览馆",
    "livehouse", "LiveHouse", "Live house",
]

# 日期模式
_DATE_RE = re.compile(
    r"(\d{4}[年.\-/]\d{1,2}[月.\-/]\d{1,2}[日号]?)|"
    r"(\d{1,2}[月.\-/]\d{1,2}[日号]?\s*[-至到]\s*\d{1,2}[日号]?)|"
    r"(\d{1,2}月\d{1,2}[日号]?)"
)


def _score_text(text: str) -> int:
    """对一段文本打分，估算它包含活动信息的可能性。"""
    score = 0

    # 日期: +2（最重要的信号）
    if _DATE_RE.search(text):
        score += 2

    # 城市: +1
    for city in CITIES:
        if city in text:
            score += 1
            break

    # 场馆: +1
    for vk in _VENUE_KEYWORDS:
        if vk in text:
            score += 1
            break

    # 活动词: +1
    for ek in _EVENT_KEYWORDS:
        if ek.lower() in text.lower():
            score += 1
            break

    return score


def _prefilter(
    texts: list[str],
    min_score: int = 3,
) -> list[tuple[int, str]]:
    """过滤噪音文本，返回 (index, text) 列表，按得分降序排列。"""
    scored: list[tuple[int, int, str]] = []

    for i, text in enumerate(texts):
        if not text or len(text) < 15:
            continue

        # 检查噪音模式
        noisy = False
        for pat in _NOISE_PATTERNS:
            if pat.search(text):
                noisy = True
                break
        # 有活动信号的即使是噪音也保留
        if noisy and not any(kw in text for kw in ["展", "届", "音乐会", "演唱会", "官宣", "定档"]):
            continue

        s = _score_text(text)
        if s >= min_score:
            scored.append((s, i, text))

    # 去重（相似文本）
    seen: set[str] = set()
    uniq: list[tuple[int, str]] = []
    for s, i, t in sorted(scored, key=lambda x: x[0], reverse=True):
        key = t[:60]
        if key not in seen:
            seen.add(key)
            uniq.append((i, t))

    logger.debug("Prefilter: %d → %d texts", len(texts), len(uniq))
    return uniq


# ═══════════════════════════════════════════════════════════════
# Stage 2: Domain Filter — 领域约束
# ═══════════════════════════════════════════════════════════════

def _domain_prompt(event_types: list[str]) -> str:
    """生成领域约束的提取 prompt 片段。"""
    type_list = "、".join(event_types)
    return (
        f"只提取以下类型的活动：{type_list}。"
        f"不属于这些类型的内容直接忽略，不要返回。"
    )


# ═══════════════════════════════════════════════════════════════
# Stage 3: LLM Extract
# ═══════════════════════════════════════════════════════════════

_EXTRACT_SYSTEM_PROMPT = """从用户提供的文本中提取近期或未来的演出/活动信息。

规则：
1. 只提取有明确活动名称的真实活动（不是闲聊提到的猜测）
2. date 必须是未来日期，过去的不要
3. city/venue 不确定就留空 ""
4. category 使用中文类别名
5. 多条文本指向同一事件时合并为一条
6. 每条提取结果标注 source_index（对应输入文本的序号）

输出纯 JSON 数组：
[{
  "title": "活动名",
  "date": "YYYY-MM-DD",
  "endDate": "YYYY-MM-DD 或空",
  "city": "城市名或空",
  "venue": "场馆名或空",
  "category": "类别",
  "source_index": 0
}]"""


def _build_extract_prompt(
    texts: list[tuple[int, str]],
    event_types: list[str],
) -> str:
    """构建完整的提取 prompt。"""
    domain = _domain_prompt(event_types)
    items = "\n".join(
        f"[{i}] {text[:300]}"  # 截断长文本
        for i, text in texts
    )
    return f"{_EXTRACT_SYSTEM_PROMPT}\n\n{domain}\n\n输入文本：\n{items}"


def _extract_raw(
    client: DeepSeekClient,
    texts: list[tuple[int, str]],
    event_types: list[str],
    temperature: float = 0.1,
) -> list[dict]:
    """调用 LLM 提取原始结构化数据。"""
    prompt = _build_extract_prompt(texts, event_types)
    try:
        result = client.chat_json(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=8192,
        )
        if isinstance(result, dict):
            # 有时候 LLM 返回 {"events": [...]} 而不是直接数组
            result = result.get("events", [])
        if not isinstance(result, list):
            logger.warning("LLM extraction returned non-list: %s", type(result))
            return []
        return result
    except Exception as e:
        logger.warning("LLM extraction call failed: %s", e)
        return []


# ═══════════════════════════════════════════════════════════════
# Stage 4: Validate & Score
# ═══════════════════════════════════════════════════════════════

def _looks_like_title(t: str) -> bool:
    """判断字符串是否像一个真实的活动名称。"""
    if not t or len(t) < 3 or len(t) > 60:
        return False
    # 纯数字/纯符号不是活动名
    if re.match(r"^[\d\s!?！？。，,、·•]+$", t):
        return False
    # 有专有名词特征（中文或英文单词）
    return bool(re.search(r"[一-鿿]{2,}|[A-Z][a-z]{2,}", t))


def _validate_and_score(
    raw_items: list[dict],
    event_types: list[str],
    extra_cities: list[str] | None,
    text_map: dict[int, str],
) -> list[ExtractedEvent]:
    """校验 LLM 提取结果并计算置信度。"""
    all_cities = set(CITIES) | set(extra_cities or [])
    events: list[ExtractedEvent] = []

    for item in raw_items:
        title = (item.get("title") or "").strip()
        if not title:
            continue

        date = (item.get("date") or "").strip()
        end_date = (item.get("endDate") or "").strip() or None
        city = (item.get("city") or "").strip()
        venue = (item.get("venue") or "").strip()
        category = (item.get("category") or "").strip()
        source_index = item.get("source_index", -1)
        source_text = text_map.get(source_index, "")

        # ── 字段验证 ──
        valid_date = _check_date(date)
        valid_city = city in all_cities if city else False
        valid_venue = len(venue) >= 2 if venue else False
        valid_category = category in set(event_types)
        valid_title = _looks_like_title(title)

        # ── Domain Filter ──
        if category and category not in event_types:
            continue

        # ── 规则化置信度 ──
        score = 0.0
        if valid_date:       score += 0.30
        if valid_city:       score += 0.25
        if valid_venue:      score += 0.15
        if valid_category:   score += 0.15
        if valid_title:      score += 0.15

        events.append(ExtractedEvent(
            title=title,
            date=date,
            end_date=end_date,
            city=city,
            venue=venue,
            category=category if valid_category else guess_category(title),
            confidence=min(score, 1.0),
            source_text=source_text,
            source_index=source_index,
        ))

    return events


def _check_date(d: str) -> bool:
    """检查日期是否有效且不为过去。"""
    if not d:
        return False
    parsed = parse_date(d)
    if not parsed:
        return False
    from datetime import date as Date
    today = Date.today().isoformat()
    return parsed >= today


# ═══════════════════════════════════════════════════════════════
# Stage 5: Dedup — 三层去重
# ═══════════════════════════════════════════════════════════════

_TITLE_CLEANUP = re.compile(
    r"[　\s!！?？。，,、·•「」『』【】()（）\[\]{}:：#＃\-\-~～★☆♥♦♣♠✓✔✗✘]+"
)


def _normalize_title(title: str) -> str:
    return _TITLE_CLEANUP.sub("", title.lower().strip())


def _make_fingerprint(event: ExtractedEvent) -> str:
    parts = [
        _normalize_title(event.title),
        event.city.strip().rstrip("市"),
        event.date,
    ]
    raw = "|".join(p for p in parts if p)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _is_same_event(a: ExtractedEvent, b: ExtractedEvent) -> bool:
    """两个事件是否指向同一活动。"""
    if not a.city or not b.city:
        return False
    if a.city != b.city:
        return False
    ta = _normalize_title(a.title)
    tb = _normalize_title(b.title)
    if ta == tb:
        return True
    # 短标题子串判断
    if len(ta) >= 4 and len(tb) >= 4:
        if ta[:6] == tb[:6] or ta in tb or tb in ta:
            return True
    # 同月同日
    if a.date and b.date and a.date[:7] == b.date[:7]:
        return True
    return False


def _dedup(events: list[ExtractedEvent]) -> list[ExtractedEvent]:
    """三层去重：指纹哈希 → 模糊匹配 → 高置信度覆盖。"""
    if len(events) <= 1:
        return events

    # Layer 1: 指纹精确去重
    seen: dict[str, ExtractedEvent] = {}
    for e in events:
        fp = _make_fingerprint(e)
        if fp in seen:
            if e.confidence > seen[fp].confidence:
                seen[fp] = e
        else:
            seen[fp] = e

    # Layer 2: 模糊匹配合并
    result = list(seen.values())
    result.sort(key=lambda x: x.date or "")

    merged: list[ExtractedEvent] = []
    for e in result:
        found = False
        for i, m in enumerate(merged):
            if _is_same_event(e, m):
                if e.confidence > m.confidence:
                    _merge_fields(e, m)
                    merged[i] = e  # 替换为高置信度条目
                else:
                    _merge_fields(m, e)
                found = True
                break
        if not found:
            merged.append(e)

    logger.debug("Dedup: %d → %d events", len(events), len(merged))
    return merged


def _merge_fields(target: ExtractedEvent, source: ExtractedEvent):
    """用 source 的缺失字段补全 target。"""
    for field in ["venue", "end_date"]:
        src_val = getattr(source, field, None)
        tgt_val = getattr(target, field, None)
        if not tgt_val and src_val:
            setattr(target, field, src_val)


# ═══════════════════════════════════════════════════════════════
# LLM 提取缓存（对标 DELM）
# ═══════════════════════════════════════════════════════════════


def _cache_key(texts: list[tuple[int, str]], event_types: list[str], model: str) -> str:
    """生成提取缓存的 key。"""
    content = "|".join(
        f"{i}:{t[:200]}" for i, t in sorted(texts)
    )
    payload = f"{content}||{'|'.join(sorted(event_types))}||{model}"
    return hashlib.sha256(payload.encode()).hexdigest()


class _ExtractionCache:
    """提取结果的磁盘缓存。"""

    def __init__(self, path: str | None, ttl_days: int = 7):
        self._path = Path(path) if path else None
        self._ttl_seconds = ttl_days * 86400
        self._data: dict[str, dict] = {}

    def _load(self):
        if not self._path or not self._path.exists():
            return
        try:
            self._data = json.loads(self._path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def _save(self):
        if not self._path:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False), "utf-8")
        tmp.replace(self._path)

    def get(self, key: str) -> list[dict] | None:
        if not self._path:
            return None
        self._load()
        entry = self._data.get(key)
        if not entry:
            return None
        from datetime import datetime
        age = datetime.now().timestamp() - entry.get("ts", 0)
        if age > self._ttl_seconds:
            del self._data[key]
            self._save()
            return None
        logger.debug("Cache hit for extraction key %s", key[:12])
        return entry.get("events", [])

    def set(self, key: str, events: list[dict]):
        if not self._path:
            return
        from datetime import datetime
        self._data[key] = {
            "ts": datetime.now().timestamp(),
            "events": events,
        }
        self._save()


# ═══════════════════════════════════════════════════════════════
# EventExtractor — 公共 API
# ═══════════════════════════════════════════════════════════════


class EventExtractor:
    """LLM 事件提取器 — 封装五阶段管道。

    Usage:
        client = DeepSeekClient(api_key="sk-xxx")
        extractor = EventExtractor(
            client=client,
            event_types=["漫展", "同人展", "演唱会"],
            min_confidence=0.5,
        )
        events = extractor.extract(["五一北京漫展...", "今天好开心..."])

    Parameters:
        client: DeepSeek API 客户端。
        event_types: 要提取的活动类型列表。
        min_confidence: 最低置信度阈值（0-1），低于此值的丢弃。
        temperature: LLM 采样温度，越低越稳定。
        extra_cities: 额外的城市名列表。
        cache_path: 提取缓存文件路径，None 禁用缓存。
        cache_ttl_days: 缓存有效期（天）。
    """

    def __init__(
        self,
        client: DeepSeekClient,
        event_types: list[str],
        min_confidence: float = 0.5,
        temperature: float = 0.1,
        extra_cities: list[str] | None = None,
        cache_path: str | None = None,
        cache_ttl_days: int = 7,
    ):
        self._client = client
        self._event_types = event_types
        self._min_confidence = min_confidence
        self._temperature = temperature
        self._extra_cities = extra_cities
        self._cache = _ExtractionCache(cache_path, cache_ttl_days)

    def dry_run(
        self,
        texts: list[str],
        *,
        min_score: int = 3,
    ) -> list[dict]:
        """不调用 API 的预检：返回会进入 LLM 提取的候选文本及评分。

        用于在正式提取前预览哪些文本会被送入 AI，以及估算 API 调用量。
        """
        scored = _prefilter(texts, min_score=min_score)
        return [
            {"index": i, "text": t[:200], "score": _score_text(t)}
            for i, t in scored
        ]

    def extract(
        self,
        texts: list[str],
        *,
        custom_prompt: str | None = None,
        min_score: int = 3,
    ) -> list[ExtractedEvent]:
        """从非结构化文本中提取活动信息。

        Args:
            texts: 原始文本列表（每条为一段可能包含活动信息的文本）。
            custom_prompt: 自定义提取指令（覆盖默认 prompt 中的领域约束部分）。
            min_score: Prefilter 最低分阈值。

        Returns:
            通过五阶段管道的 ExtractedEvent 列表。
        """
        if not texts:
            return []

        # Stage 1: Prefilter
        scored = _prefilter(texts, min_score=min_score)
        if not scored:
            return []

        # 构建索引到原文的映射
        text_map: dict[int, str] = {i: texts[i] for _, i in scored if i < len(texts)}

        # 检查缓存
        cache_key = _cache_key(scored, self._event_types, self._client.model)
        cached = self._cache.get(cache_key)
        if cached is not None:
            events = _validate_and_score(
                cached, self._event_types, self._extra_cities, text_map
            )
            return [e for e in events if e.confidence >= self._min_confidence]

        # Stage 2 & 3: LLM Extract
        event_types_for_llm = (
            self._event_types if custom_prompt is None else []
        )
        raw = _extract_raw(
            self._client, scored, event_types_for_llm, self._temperature
        )

        # Cache raw LLM response
        self._cache.set(cache_key, raw)

        # Stage 4: Validate & Score
        events = _validate_and_score(
            raw, self._event_types, self._extra_cities, text_map
        )

        # Confidence threshold
        events = [e for e in events if e.confidence >= self._min_confidence]

        # Stage 5: Dedup
        events = _dedup(events)

        logger.info(
            "Extraction: %d texts → %d events (min_confidence=%.1f)",
            len(texts), len(events), self._min_confidence,
        )
        return events


def extract_events(
    texts: list[str],
    client: DeepSeekClient,
    *,
    event_types: list[str],
    min_confidence: float = 0.5,
    extra_cities: list[str] | None = None,
    cache_path: str | None = None,
) -> list[ExtractedEvent]:
    """便捷函数 — 单次提取活动信息。

    等价于 EventExtractor(...).extract(texts)，适合一次性使用。
    """
    extractor = EventExtractor(
        client=client,
        event_types=event_types,
        min_confidence=min_confidence,
        extra_cities=extra_cities,
        cache_path=cache_path,
    )
    return extractor.extract(texts)
