from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """获取环境变量；若不存在则尝试解析 qihuo/.secrets/.env 文件。"""
    val = os.environ.get(key)
    if val:
        return val

    # 尝试读取本地 .env
    candidates = [
        Path("qihuo/.secrets/.env"),
        Path(".secrets/.env"),
    ]
    for p in candidates:
        try:
            if p.exists():
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == key:
                            return v.strip()
        except Exception:
            continue
    return default


