"""风险判定与安全运行时长（基于当前温度变化率）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from rbmk.sim.engine import SimulationEngine

LEVEL_NAMES = {"normal": "正常", "warning": "警告", "danger": "危险", "meltdown": "熔毁"}

_MSG = {
    "normal": "运行正常，温度在安全范围",
    "warning": "温度偏高，建议加大冷却或插入控制棒",
    "danger": "柱温接近 1500°C 熔毁线，随时可能熔毁",
    "meltdown": "堆芯已熔毁",
}

STABLE_RATE = 0.5  # °C/s：低于此值视为已趋于平衡


@dataclass
class RiskReport:
    level: str
    temperature: float
    melt_temp: float
    ratio: float
    time_to_meltdown: Optional[float]
    message: str


def estimate_time_to_melt(engine: SimulationEngine) -> Optional[float]:
    s = engine.state
    melt = s.melt_temp or 1500.0
    if s.melted:
        return 0.0
    rate = s.temp_rate
    if rate <= STABLE_RATE:
        return None
    return max(0.0, (melt - s.temperature) / rate)


def assess(engine: SimulationEngine) -> RiskReport:
    s = engine.state
    melt = s.melt_temp or 1500.0
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
