"""中国城市提取与规范化。"""

import re

# 50 个主要城市（从 ComiRadar 合并）
CITIES = [
    "上海", "北京", "广州", "深圳", "成都", "杭州", "南京", "武汉", "重庆",
    "西安", "长沙", "苏州", "天津", "郑州", "东莞", "青岛", "沈阳", "宁波",
    "昆明", "大连", "厦门", "合肥", "佛山", "无锡", "福州", "济南", "哈尔滨",
    "长春", "石家庄", "南宁", "贵阳", "南昌", "太原", "乌鲁木齐", "兰州",
    "海口", "银川", "西宁", "拉萨", "珠海", "常州", "南通", "徐州", "温州",
    "绍兴", "嘉兴", "金华", "泉州", "漳州", "三亚",
]

# 城市名后的假后缀 — 表示城市名是更大词的一部分（"西安路" 中的 "路"）
_FALSE_SUFFIXES = frozenset(
    ["路", "街", "道", "村", "区", "县", "镇", "乡", "桥", "站", "门", "楼",
     "河", "湖", "山", "岭", "岗", "庄", "屯", "营", "堡", "铺", "店", "集"]
)


def extract_city(text: str, extra_cities: list[str] | None = None) -> str:
    """从文本中提取第一个匹配的城市名。

    通过假后缀黑名单防止常见误匹配（如 "西安路" 不匹配 "西安"）。
    可通过 extra_cities 传入额外的城市列表。
    """
    cities = CITIES + (extra_cities or [])
    # 按城市名长度降序排列：优先匹配长名称（"石家庄" 优先于 "石"）
    for city in sorted(cities, key=len, reverse=True):
        idx = text.find(city)
        if idx == -1:
            continue
        # 检查城市名后的第一个字符是否为假后缀
        after = idx + len(city)
        if after < len(text) and text[after] in _FALSE_SUFFIXES:
            continue
        return city
    return ""


def normalize_city(city: str) -> str:
    """统一城市名：去空格、去'市'后缀、处理别名。"""
    c = city.strip().rstrip("市")
    aliases = {"中国": "", "全国": ""}
    return aliases.get(c, c)
