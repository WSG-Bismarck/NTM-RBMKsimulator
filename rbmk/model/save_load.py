"""设计文件保存 / 导出 / 导入（JSON，可分享）。"""
from __future__ import annotations

import json
from pathlib import Path

from rbmk.model.reactor import ReactorModel

SAVE_VERSION = 1


def to_json(model: ReactorModel) -> str:
    return json.dumps(model.to_dict(), ensure_ascii=False, indent=2)


def from_json(text: str) -> ReactorModel:
    data = json.loads(text)
    _validate(data)
    return ReactorModel.from_dict(data)


def _validate(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("设计文件格式错误：根节点不是对象")
    for k in ("rows", "cols"):
        if k not in data:
            raise ValueError(f"设计文件缺少字段：{k}")
        if not isinstance(data[k], int) or data[k] <= 0:
            raise ValueError(f"字段 {k} 非法：{data[k]}")
    rows, cols = data["rows"], data["cols"]
    for item in data.get("cells", []):
        r, c = item.get("r"), item.get("c")
        if not isinstance(r, int) or not isinstance(c, int):
            raise ValueError("设计文件中的坐标非法")
        if not (0 <= r < rows and 0 <= c < cols):
            raise ValueError(f"坐标越界：({r},{c})")


def save(model: ReactorModel, path: str | Path) -> None:
    Path(path).write_text(to_json(model), encoding="utf-8")


def load(path: str | Path) -> ReactorModel:
    return from_json(Path(path).read_text(encoding="utf-8"))


# 导出/分享 = 保存为通用 JSON；对方用同一函数导入
export = save
import_file = load
