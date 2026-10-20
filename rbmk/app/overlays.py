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

    坐标严格照抄 GUIRBMKConsole.drawScreen 的 drawTexturedModalRect 参数（含末尾 -1 偏移）：
      heat  : (0, 192-h, 10, h)            h  = min(ceil((heat-20)*10/maxHeat), 10)
      fuel  : (x+1, size-fh-1, 2, fh)      fh = min(ceil((c_heat-20)*8/c_maxHeat), 8)
              (x+4, size-fe-1, 2, fe)      fe = min(ceil(enrichment*8), 8)
              (x+7, size-fx-1, 2, fx)      fx = min(ceil(xenon*8/100), 8)
      boiler: (x+1, size-fw-1, 3, fw)      fw = ceil(water*8/maxWater)
              (x+6, size-fs-1, 3, fs)      fs = ceil(steam*8/maxSteam)（模型无蒸汽缓冲 → 0）
              蒸汽类型点 (x+4, y+1/3/5/7, 2, 2)
      control:(x+3, y+1, 1, 8) / (x+6, y+1, 1, 8) 分组色
      auto  : (x+4, y+1, 2, fr)            fr = 8 - ceil(level*8)
      heatex: (x+1, size-cc-1, 3, cc) / (x+6, size-hc-1, 3, hc)
    """
    out: list[tuple[float, float, float, float, tuple[int, int, int]]] = []
    kind = KIND_OF.get(cell.comp, "BLANK")

    # 1) 热量条（模组里先画，类型状态条后画会盖住它的一部分）
    heat = cell.shown_temp if cell.shown_temp else cell.temp
    hh = int(min(max(math.ceil((heat - 20.0) * 10.0 / max_heat), 0), 10))
    if hh > 0:
        out.append((0, 10 - hh, 1, hh, C_HEAT))
        out.append((9, 10 - hh, 1, hh, C_HEAT))

    # 2) 按类型的状态条
    if kind in ("FUEL", "FUEL_SIM"):
        ft = cell.fuel_type
        if ft is not None:
            melt = float(getattr(ft, "melting_point", 0.0) or 0.0)
            fh = 0 if melt <= 0 else int(min(max(math.ceil((cell.hull_heat - 20.0) * 8.0 / melt), 0), 8))
            fe = int(min(max(math.ceil((1.0 - cell.burnup) * 8.0), 0), 8))
            fx = int(min(max(math.ceil(cell.xenon * 8.0 / 100.0), 0), 8))
            out.append((1, 9 - fh, 2, fh, C_SKIN))
            out.append((4, 9 - fe, 2, fe, C_ENRICH))
            out.append((7, 9 - fx, 2, fx, C_XENON))

    elif kind == "BOILER":
        fw = int(min(max(math.ceil(cell.water * 8.0 / BOILER_WATER_MAX), 0), 8))
        out.append((1, 9 - fw, 3, fw, C_WATER))
        # 模型不设蒸汽缓冲（产汽直接外送），模组的蒸汽条 (x+6) 高度恒为 0
        dot = STEAM_DOT.get(cell.steam_type)
        if dot:
            dy = {"STEAM": 1, "HOTSTEAM": 3, "SUPERHOTSTEAM": 5, "ULTRAHOTSTEAM": 7}[cell.steam_type]
            out.append((4, dy, 2, 2, dot))

    elif kind == "HEATEX":
        fw = int(min(max(math.ceil(cell.water * 8.0 / HEATER_IN_MAX), 0), 8))
        out.append((1, 9 - fw, 3, fw, C_HEATEX_IN))

    # 3) 控制棒分组色（模组 case CONTROL 没有 break，会继续执行插入条）
    if kind == "CONTROL":
        idx = GROUP_INDEX.get(getattr(cell.group, "value", None))
        if idx is not None:
            color = CTRL_COLORS[idx]
            out.append((3, 1, 1, 8, color))
            out.append((6, 1, 1, 8, color))

    if kind in ("CONTROL", "CONTROL_AUTO"):
        if kind == "CONTROL_AUTO":
            frac = max(0.0, min(1.0, 1.0 - cell.level))
        else:
            frac = max(0.0, min(1.0, model.effective_insertion(cell) / 100.0))
        fr = 8 - int(math.ceil(frac * 8.0))
        out.append((4, 1, 2, fr, C_AUTO))

    return [r for r in out if r[3] > 0 and r[2] > 0]
