"""确定性的 SHA256 稳定 ID 生成，替代 Python 不稳定的 hash()。"""

import hashlib


def stable_id(*parts: str) -> str:
    """生成确定性的短 ID，跨进程重启不变。

    用 '|' 连接输入片段，SHA256 哈希后取前 16 位 hex。
    """
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]
