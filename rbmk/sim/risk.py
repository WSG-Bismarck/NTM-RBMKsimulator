"""风险判定与安全运行时长（基于一阶热模型的平衡温度精确估算）。"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from rbmk.model.reactor import FUEL_TYPES
from rbmk.sim.engine import AMBIENT, SimulationEngine

LEVEL_NAMES = {"normal": "正常", "warning": "警告", "danger": "危险", "meltdown": "熔毁"}

_MSG = {
    "normal": "运行正常，温度在安全范围",
    "warning": "温度偏高，建议加大冷却或插入控制棒",
    "danger": "温度接近燃料熔点，随时可能熔毁",
    "meltdown": "堆芯已熔毁",
}


@dataclass
class RiskReport:
    level: str
    temperature: float
    melt_temp: float
    ratio: float
    time_to_meltdown: Optional[float]   # 剩余安全秒数；None = 平衡温度低于熔点，稳定
    message: str


def _cooling_coeff(engine: SimulationEngine) -> float:
    p = engine.p
    flow = engine.model.coolant_flow / 100.0
    return flow * p["cooling_coeff"] + p["passive_cooling"]


def equilibrium_temperature(engine: SimulationEngine) -> float:
    """按 dT/dt = heat*k - cooling*(T-T0) 的平衡点估算最热柱温度。"""
    k = _cooling_coeff(engine)
    if k <= 0:
        return float("inf")
    best = AMBIENT
    for _, _, cell in engine.model.iter_cells():
        if cell.comp in FUEL_TYPES and cell.heat > 0:
            teq = AMBIENT + cell.heat * engine.p["heat_coeff"] / k
            if teq > best:
                best = teq
    return best


def estimate_time_to_melt(engine: SimulationEngine) -> Optional[float]:
    """用一阶热模型 T(t)=Teq+(T0-Teq)e^(-kt) 求到达熔点的精确时间。

    返回 None 表示平衡温度低于熔点（不会熔毁）；0 表示已熔毁/已达熔点。
    """
    s = engine.state
    melt = s.melt_temp or 2800.0
    if s.melted:
        return 0.0
    k = _cooling_coeff(engine)
    if k <= 0:
        return None

    best_teq = AMBIENT
    best_t = s.temperature
    for _, _, cell in engine.model.iter_cells():
        if cell.comp in FUEL_TYPES and cell.heat > 0:
            teq = AMBIENT + cell.heat * engine.p["heat_coeff"] / k
            if teq > best_teq:
                best_teq = teq
                best_t = cell.temp

    if best_teq <= melt:
        return None
    if best_t >= melt:
        return 0.0
    ratio = (melt - best_teq) / (best_t - best_teq)
    if ratio <= 0:
        return None
    return max(0.0, -math.log(ratio) / k)


def assess(engine: SimulationEngine) -> RiskReport:
    s = engine.state
    melt = s.melt_temp or 2800.0
    ratio = (s.temperature / melt) if melt > 0 else 0.0
    if s.melted:
        return RiskReport("meltdown", s.temperature, melt, ratio, 0.0, _MSG["meltdown"])

    t = estimate_time_to_melt(engine)
    level = s.status if s.status in _MSG else "normal"
    return RiskReport(level, s.temperature, melt, ratio, t, _MSG[level])


def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "稳定（无熔毁风险）"
    if seconds <= 0:
        return "0:00:00"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
