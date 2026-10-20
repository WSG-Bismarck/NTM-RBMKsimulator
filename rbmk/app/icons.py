"""组件图标：直接使用模组方块贴图（assets/hbm/textures/blocks/rbmk/*_top.png）。

图标来源：HBM-NTM-.1.0.27_X5846.jar 内 rbmk_* 方块的 _top 贴图，已按组件 key 复制到
rbmk/assets/icons/<component>.png。运行期用 PIL 缩放到单元大小并缓存。
"""
from __future__ import annotations

import os
import sys

_CACHE: dict[tuple[str, int], object] = {}


def icons_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS", ""), "rbmk", "assets", "icons")
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "assets", "icons")


def icon_path(key: str) -> str:
    return os.path.join(icons_dir(), f"{key}.png")


def get_icon(key: str, size: int):
    """返回缩放到 size×size 的 tk.PhotoImage（带缓存）。缺图或 PIL 不可用时返回 None。"""
    cache_key = (key, int(size))
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    img = None
    path = icon_path(key)
    if os.path.exists(path):
        try:
            from PIL import Image, ImageTk

            im = Image.open(path).convert("RGBA")
            im = im.resize((cache_key[1], cache_key[1]), Image.NEAREST)
            img = ImageTk.PhotoImage(im)
        except Exception:
            img = None
    _CACHE[cache_key] = img
    return img


def clear_cache() -> None:
    _CACHE.clear()
