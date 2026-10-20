"""反应堆数据模型：网格、柱子、全局控制参数。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rbmk.model.components import (
    COMPONENT_INFO,
    CONTROL_COMPONENTS,
    FUEL_COMPONENTS,
    Behavior,
    ComponentType,
    ControlGroup,
    FUELS,
    FuelType,
    behavior_of,
)

CONTROL_TYPES = CONTROL_COMPONENTS
FUEL_TYPES = FUEL_COMPONENTS


@dataclass
class Cell:
    comp: ComponentType
    fuel: Optional[str] = None          # 燃料 key（燃料类柱子）
    group: Optional[ControlGroup] = None               # None = 空置（默认，不受分组控制）
    insertion: Optional[float] = None   # 单根插入深度 0..100；None=用分组/全局
    burnup: float = 0.0                 # 0..1
    xenon: float = 0.0                  # 0..100（与模组一致）
    temp: float = 25.0
    heat: float = 0.0
    flux: float = 0.0
    steam: float = 0.0
    steam_rate: float = 0.0            # 每 tick 产汽量
    shown_temp: float = 25.0           # 模组该柱自己 tick 结束时的温度快照（控制台显示值）
    seq: int = 0                       # 放置顺序（模组里同一区块的 TE 按加入顺序 tick）
    steam_type: str = "STEAM"          # 蒸汽类型（STEAM/HOTSTEAM/SUPERHOTSTEAM/ULTRAHOTSTEAM）
    heater_fluid: str = "COOLANT"      # 流体加热器输入流体（默认冷却液）
    heater_rate: float = 0.0           # 每刻加热流体产量（mB/tick）
    heater_heat: float = 0.0           # 每刻热量产出（TU/tick）
    water: float = 100.0
    # ---- 中子逐格状态（运行时）----
    flux_q: float = 0.0
    flux_ratio: float = 0.0
    last_flux_q: float = 0.0
    last_flux_ratio: float = 0.0
    has_rod: bool = False
    core_heat: float = 20.0              # 燃料芯温度
    hull_heat: float = 20.0              # 燃料壳温度

    @property
    def fuel_type(self) -> Optional[FuelType]:
        return FUELS.get(self.fuel) if self.fuel else None

    def to_dict(self) -> dict:
        return {
            "comp": self.comp.value,
            "fuel": self.fuel,
            "group": self.group.value if self.group is not None else None,
            "insertion": self.insertion,
            "burnup": self.burnup,
            "xenon": self.xenon,
            "temp": self.temp,
            "steam_type": self.steam_type,
            "heater_fluid": self.heater_fluid,
            "seq": self.seq,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Cell":
        return cls(
            comp=ComponentType(d["comp"]),
            fuel=d.get("fuel"),
            group=ControlGroup(d["group"]) if d.get("group") else None,
            insertion=d.get("insertion"),
            burnup=float(d.get("burnup", 0.0)),
            xenon=float(d.get("xenon", 0.0)),
            temp=float(d.get("temp", 25.0)),
            steam_type=d.get("steam_type", "STEAM"),
            heater_fluid=d.get("heater_fluid", "COOLANT"),
            seq=int(d.get("seq", 0)),
        )


@dataclass
class ReactorModel:
    rows: int = 15
    cols: int = 15
    grid: list[list[Optional[Cell]]] = field(default_factory=list)

    global_insertion: float = 100.0
    group_insertion: dict[str, Optional[float]] = field(default_factory=dict)
    coolant_flow: float = 50.0
    control_mode: str = "global"
    reasim_boilers: bool = False      # ReaSim 锅炉模式：整堆每根柱都产汽（1:1、5%/tick）
    _seq: int = field(default=0, init=False, repr=False, compare=False)

    def __post_init__(self):
        if not self.grid:
            self.grid = [[None for _ in range(self.cols)] for _ in range(self.rows)]

    def cell_at(self, r: int, c: int) -> Optional[Cell]:
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return self.grid[r][c]
        return None

    def place(self, r: int, c: int, comp: ComponentType, **kw) -> Cell:
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            raise IndexError("坐标越界")
        cell = Cell(comp=comp, **kw)
        cell.has_rod = cell.fuel_type is not None and cell.fuel != "rbmk_fuel_empty"
        cell.seq = self._seq
        self._seq += 1
        self.grid[r][c] = cell
        return cell

    def erase(self, r: int, c: int) -> None:
        if 0 <= r < self.rows and 0 <= c < self.cols:
            self.grid[r][c] = None

    def clear(self) -> None:
        self.grid = [[None for _ in range(self.cols)] for _ in range(self.rows)]

    def iter_cells(self):
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.grid[r][c]
                if cell is not None:
                    yield r, c, cell

    def iter_cells_placed(self):
        """按放置顺序遍历（对应模组同一区块内 TE 的 tick 顺序）。"""
        cells = list(self.iter_cells())
        cells.sort(key=lambda x: x[2].seq)
        return iter(cells)

    def counts(self) -> dict[ComponentType, int]:
        out = {t: 0 for t in ComponentType}
        for _, _, cell in self.iter_cells():
            out[cell.comp] += 1
        return out

    def fuel_count(self) -> int:
        return sum(1 for _, _, c in self.iter_cells()
                   if behavior_of(c.comp) == Behavior.FUEL and c.fuel)

    def control_cells(self) -> list[tuple[int, int, Cell]]:
        return [(r, c, cell) for r, c, cell in self.iter_cells()
                if behavior_of(cell.comp) == Behavior.CONTROL]

    def effective_insertion(self, cell: Cell) -> float:
        """单根 > 分组 > 全局。返回 0..100。"""
        if behavior_of(cell.comp) != Behavior.CONTROL:
            return 0.0
        if cell.insertion is not None:
            return _clamp(cell.insertion, 0.0, 100.0)
        if cell.group is not None:
            g = self.group_insertion.get(cell.group.value)
            if g is not None:
                return _clamp(g, 0.0, 100.0)
        return _clamp(self.global_insertion, 0.0, 100.0)

    def to_dict(self) -> dict:
        return {
            "version": 2,
            "rows": self.rows,
            "cols": self.cols,
            "global_insertion": self.global_insertion,
            "group_insertion": dict(self.group_insertion),
            "coolant_flow": self.coolant_flow,
            "control_mode": self.control_mode,
            "reasim_boilers": self.reasim_boilers,
            "cells": [{"r": r, "c": c, **cell.to_dict()} for r, c, cell in self.iter_cells()],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ReactorModel":
        m = cls(
            rows=int(d.get("rows", 15)),
            cols=int(d.get("cols", 15)),
            global_insertion=float(d.get("global_insertion", 100.0)),
            group_insertion=dict(d.get("group_insertion", {})),
            coolant_flow=float(d.get("coolant_flow", 50.0)),
            control_mode=d.get("control_mode", "global"),
            reasim_boilers=bool(d.get("reasim_boilers", False)),
        )
        for item in d.get("cells", []):
            cell = Cell.from_dict(item)
            m.grid[int(item["r"])][int(item["c"])] = cell
            m._seq = max(m._seq, cell.seq + 1)
        return m


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))
