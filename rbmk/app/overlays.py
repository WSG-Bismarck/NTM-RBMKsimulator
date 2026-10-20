"""控制台叠加层几何计算（复刻 GUIRBMKConsole 的柱阵列绘制）。

坐标系统一用「game 像素」：每根柱 10×10，左上角为 (0,0)。
主网格按 cell_size / 10 缩放后直接画这些矩形。
"""
from __future__ import annotations

import math

from rbmk.model.components import ComponentType as C

MAX_HEAT = 1500.0
BOILER_WATER_MAX = 10000.0
HEATER_IN_MAX = 16000.0

KIND_OF = {
    C.RBMK_ROD: "FUEL", C.RBMK_ROD_MOD: "FUEL",
    C.RBMK_ROD_REASIM: "FUEL_SIM", C.RBMK_ROD_REASIM_MOD: "FUEL_SIM",
    C.RBMK_CONTROL: "CONTROL", C.RBMK_CONTROL_MOD: "CONTROL", C.RBMK_CONTROL_REASIM: "CONTROL",
    C.RBMK_CONTROL_AUTO: "CONTROL_AUTO", C.RBMK_CONTROL_REASIM_AUTO: "CONTROL_AUTO",
    C.RBMK_BOILER: "BOILER", C.RBMK_MODERATOR: "MODERATOR", C.RBMK_ABSORBER: "ABSORBER",
    C.RBMK_REFLECTOR: "REFLECTOR", C.RBMK_OUTGASSER: "OUTGASSER", C.RBMK_STORAGE: "STORAGE",
    C.RBMK_COOLER: "COOLER", C.RBMK_BLANK: "BLANK", C.RBMK_HEATER: "HEATEX",
}

# 颜色取样自 gui_rbmk_console.png
C_HEAT = (169, 0, 0)
C_SKIN = (255, 135, 0)
C_ENRICH = (59, 200, 0)
C_XENON = (139, 0, 200)
C_WATER = (72, 99, 255)
C_HEATEX_IN = (23, 183, 196)
C_AUTO = (100, 111, 120)
CTRL_COLORS = [(255, 0, 0), (255, 216, 0), (76, 255, 0), (0, 38, 255), (178, 0, 255)]
GROUP_INDEX = {"RED": 0, "YELLOW": 1, "GREEN": 2, "BLUE": 3, "PURPLE": 4}
STEAM_DOT = {
    "STEAM": (255, 255, 255),
    "HOTSTEAM": (255, 235, 235),
    "SUPERHOTSTEAM": (255, 195, 195),
    "ULTRAHOTSTEAM": (255, 139, 139),
}


def column_overlays(cell, model, max_heat: float = MAX_HEAT):
    """返回该柱在 10×10 单元格内的叠加矩形：[(x, y, w, h, rgb), ...]（game 像素）。

    顺序与 GUIRBMKConsole.drawScreen 一致：
      热量红线 → 燃料三色条 / 蒸汽管道水条与类型点 / 加热器进口条 → 控制棒分组色 → 插入条
    """
    out: list[tuple[float, float, float, float, tuple[int, int, int]]] = []
    kind = KIND_OF.get(cell.comp, "BLANK")

    heat = cell.shown_temp if cell.shown_temp else cell.temp
    hh = int(min(max(math.ceil((heat - 20.0) * 10.0 / max_heat), 0), 10))

    if kind in ("FUEL", "FUEL_SIM"):
        ft = cell.fuel_type
        if ft is not None:
            melt = float(getattr(ft, "melting_point", 0.0) or 0.0)
            fh = 0 if melt <= 0 else int(min(max(math.ceil((cell.hull_heat - 20.0) * 10.0 / melt), 0), 10))
            fe = int(min(max(math.ceil((1.0 - cell.burnup) * 10.0), 0), 10))
            fx = int(min(max(math.ceil(cell.xenon * 10.0 / 100.0), 0), 10))
            # 三根状态条并排铺满整格（1..4 / 4..7 / 7..10），高度按整格 10 计、贴底生长
            out.append((1, 10 - fh, 3, fh, C_SKIN))
            out.append((4, 10 - fe, 3, fe, C_ENRICH))
            out.append((7, 10 - fx, 3, fx, C_XENON))

    elif kind == "BOILER":
        fw = int(min(max(math.ceil(cell.water * 10.0 / BOILER_WATER_MAX), 0), 10))
        # 水条铺满整格宽度（贴底生长），不再只占左三分之一而留下大片灰底
        out.append((0, 10 - fw, 10, fw, C_WATER))
        dot = STEAM_DOT.get(cell.steam_type)
        if dot:
            out.append((4, 4, 2, 2, dot))

    elif kind == "HEATEX":
        fw = int(min(max(math.ceil(cell.water * 10.0 / HEATER_IN_MAX), 0), 10))
        out.append((0, 10 - fw, 10, fw, C_HEATEX_IN))

    # 模组里 CONTROL 没有 break，会穿透到 CONTROL_AUTO 的插入条
    if kind == "CONTROL":
        idx = GROUP_INDEX.get(getattr(cell.group, "value", None))
        if idx is not None:
            color = CTRL_COLORS[idx]
            out.append((2, 0, 2, 10, color))
            out.append((6, 0, 2, 10, color))

    if kind in ("CONTROL", "CONTROL_AUTO"):
        if kind == "CONTROL_AUTO":
            frac = max(0.0, min(1.0, 1.0 - cell.level))
        else:
            frac = max(0.0, min(1.0, model.effective_insertion(cell) / 100.0))
        fr = 10 - int(math.ceil(frac * 10.0))
        out.append((4, 0, 3, fr, C_AUTO))

    # 热量条最后叠加，保证状态条再满也能看到左右两条红线
    if hh > 0:
        out.append((0, 10 - hh, 1, hh, C_HEAT))
        out.append((9, 10 - hh, 1, hh, C_HEAT))

    return [r for r in out if r[3] > 0 and r[2] > 0]
