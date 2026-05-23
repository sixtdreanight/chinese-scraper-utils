"""中文日期解析 — 支持结构化字符串和自由文本提取。"""

import re
from datetime import datetime


# 自由文本日期正则
_DATE_PATTERNS = [
    re.compile(r"(\d{4})[年.\-](\d{1,2})[月.\-](\d{1,2})[日号]?"),
    re.compile(r"(\d{1,2})月(\d{1,2})[日号]"),
    re.compile(r"(\d{1,2})月(\d{1,2})[日号]?\s*[-–—至到]\s*(\d{1,2})[日号]?"),
]


def parse_date(s: str) -> str:
    """解析结构化日期字符串，返回 YYYY-MM-DD 格式。

    支持: 2026-05-04, 2026/05/04, 2026.05.04, 2026-05-04 14:30:00, 20260504, ISO 格式。
    无法解析时返回空字符串（不再静默返回截断垃圾）。
    如需 None 返回值，请使用 try_parse_date()。
    """
    if not s:
        return ""
    s = str(s).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    return ""


def try_parse_date(s: str) -> str | None:
    """同 parse_date()，但无法解析时返回 None 而非空字符串。"""
    result = parse_date(s)
    return result if result else None


def extract_date(text: str) -> str:
    """从中文自由文本中提取日期，返回 YYYY-MM-DD 格式。

    支持: '2026年5月4日', '5月4日', '5月4日-6日'。
    无法提取时返回空字符串。
    """
    year = datetime.now().year
    for pat in _DATE_PATTERNS:
        m = pat.search(text)
        if m:
            groups = m.groups()
            if len(groups) == 2:
                mth, day = int(groups[0]), int(groups[1])
                y = year
            elif len(str(groups[0])) == 4:
                y, mth, day = int(groups[0]), int(groups[1]), int(groups[2])
            else:
                mth, day = int(groups[0]), int(groups[1])
                y = year
            try:
                dt = datetime(y, mth, day)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
    return ""
