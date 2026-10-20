"""模拟引擎：中子学、热、蒸汽、发电、燃料消耗、氙毒、熔毁。

纯逻辑，不依赖界面，可单独测试。
数值常量见 DEFAULT_PARAMS（v1 建模值，见 spec/rbmk-mechanics.md 6.3）。
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from rbmk.model.components import ComponentType
from rbmk.model.reactor import CONTROL_TYPES, FUEL_TYPES, ReactorModel

AMBIENT = 25.0

DEFAULT_PARAMS = {
    "moderator_efficiency": 0.30,
    "absorber_efficiency": 0.08,
    "reflector_efficiency": 0.25,
    "control_efficiency": 0.06,
    "heat_coeff": 12.0,
    "cooling_coeff": 0.03,
    "passive_cooling": 0.005,
    "turbine_efficiency": 0.30,
    "power_scale": 100.0,
    "burn_rate": 0.00008,
    "xenon_scale": 0.10,
    "warning_ratio": 0.60,
    "danger_ratio": 0.85,
    "max_substeps": 5000,
}


@dataclass
class EngineState:
    time: float = 0.0            # 模拟秒
    power: float = 0.0           # 热功率（MW 量级）
    flux: float = 0.0
    temperature: float = AMBIENT # 最高柱温 °C
    steam: float = 0.0
    electricity: float = 0.0     # 瞬时发电（MW）
    total_energy: float = 0.0    # 累计发电（MWh）
    fuel_remaining: float = 100.0
    xenon: float = 0.0
    status: str = "normal"       # normal/warning/danger/meltdown
    melted: bool = False
    melt_temp: float = 2800.0
    temp_rate: float = 0.0       # 温度变化率 °C/模拟秒（用于安全时长估算）


class SimulationEngine:
    def __init__(self, model: ReactorModel, params: dict | None = None):
        self.model = model
        self.p = {**DEFAULT_PARAMS, **(params or {})}
        self.state = EngineState(melt_temp=self._min_melting())
        self._reset()

    # ---------- 初始化 ----------
    def _reset(self) -> None:
        for _, _, cell in self.model.iter_cells():
            cell.temp = AMBIENT
            cell.heat = 0.0
            cell.flux = 0.0
            cell.steam = 0.0
            cell.water = 100.0
        self.state = EngineState(melt_temp=self._min_melting())

    def reset(self) -> None:
        self._reset()

    def _min_melting(self) -> float:
        best = None
        for _, _, cell in self.model.iter_cells():
            ft = cell.fuel_type
            if cell.comp in FUEL_TYPES and ft and ft.melting_point > 0:
                best = ft.melting_point if best is None else min(best, ft.melting_point)
        return best or 2800.0

    # ---------- 邻居/统计 ----------
    def _neighbors(self, r: int, c: int):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nb = self.model.cell_at(r + dr, c + dc)
                if nb is not None:
                    yield nb

    def _control_absorption(self) -> float:
        total = 0.0
        for _, _, cell in self.model.control_cells():
            total += self.model.effective_insertion(cell) / 100.0
        return total

    def _fuel_cells(self):
        return [
            (r, c, cell)
            for r, c, cell in self.model.iter_cells()
            if cell.comp in FUEL_TYPES and cell.fuel_type is not None
        ]

    # ---------- 单步 ----------
    def _substep(self, dt: float) -> None:
        p = self.p
        s = self.state
        if s.melted:
            return

        prev_temp = s.temperature
        fuel = self._fuel_cells()
        max_temp = s.temperature

        mod = sum(1 for _, _, c in self.model.iter_cells() if c.comp == ComponentType.MODERATOR)
        refl = sum(1 for _, _, c in self.model.iter_cells() if c.comp == ComponentType.REFLECTOR)
        absb = sum(1 for _, _, c in self.model.iter_cells() if c.comp == ComponentType.ABSORBER)
        boiler = sum(1 for _, _, c in self.model.iter_cells() if c.comp == ComponentType.BOILER)
        ctrl = self._control_absorption()

        mod_factor = 1.0 + p["moderator_efficiency"] * math.sqrt(mod)
        refl_factor = 1.0 + p["reflector_efficiency"] * math.sqrt(refl)
        abs_factor = 1.0 / (1.0 + p["absorber_efficiency"] * absb + p["control_efficiency"] * ctrl)

        flow = self.model.coolant_flow / 100.0
        cooling = flow * p["cooling_coeff"] + p["passive_cooling"]

        total_flux = 0.0
        total_heat = 0.0
        burn_sum = 0.0
        xenon_sum = 0.0

        for r, c, cell in fuel:
            ft = cell.fuel_type
            local = ft.reactivity * (1.0 - cell.burnup) * (1.0 - 0.5 * cell.xenon)
            nmod = sum(1 for nb in self._neighbors(r, c) if nb.comp == ComponentType.MODERATOR)
            local *= (1.0 + 0.10 * nmod)
            cell.flux = local * mod_factor * refl_factor * abs_factor
            total_flux += cell.flux

            cell.heat = cell.flux * ft.heat
            total_heat += cell.heat

            # 温度：一阶惯性
            dtemp = (cell.heat * p["heat_coeff"] - cooling * (cell.temp - AMBIENT)) * dt
            cell.temp += dtemp
            if cell.temp > max_temp:
                max_temp = cell.temp

            # 燃料燃耗
            cell.burnup = min(1.0, cell.burnup + cell.flux * p["burn_rate"] * dt)
            burn_sum += cell.burnup

            # 氙毒：生成 - 燃耗
            gen = ft.x_gen * p["xenon_scale"] * cell.flux
            burn = ft.x_burn * cell.xenon * cell.flux
            cell.xenon = _clamp(cell.xenon + (gen - burn) * dt, 0.0, 1.0)
            xenon_sum += cell.xenon

        # 生产链：热 -> 锅炉产蒸汽 -> 涡轮发电（无锅炉则无蒸汽/发电）
        if fuel:
            steam_frac = min(1.0, boiler / max(1, len(fuel)))
            s.steam = total_heat * steam_frac
            s.electricity = s.steam * p["turbine_efficiency"] * p["power_scale"]
        else:
            s.steam = 0.0
            s.electricity = 0.0
            for _, _, cell in self.model.iter_cells():
                cell.temp += (AMBIENT - cell.temp) * min(1.0, dt * 0.05)
            max_temp = max((c.temp for _, _, c in self.model.iter_cells()), default=AMBIENT)

        # 更新状态
        s.time += dt
        s.power = total_heat * p["power_scale"]
        s.flux = total_flux
        s.temperature = max_temp
        s.total_energy += s.electricity * dt / 3600.0
        if fuel:
            s.fuel_remaining = 100.0 * (1.0 - burn_sum / len(fuel))
            s.xenon = xenon_sum / len(fuel)

        # 温度趋势（用于安全时长）
        s.temp_rate = (s.temperature - prev_temp) / dt if dt > 0 else 0.0

        # 熔毁判定
        melt = s.melt_temp
        if max_temp >= melt:
            s.melted = True
        ratio = max_temp / melt if melt > 0 else 0.0
        if s.melted:
            s.status = "meltdown"
        elif ratio >= p["danger_ratio"]:
            s.status = "danger"
        elif ratio >= p["warning_ratio"]:
            s.status = "warning"
        else:
            s.status = "normal"

    # ---------- 推进 ----------
    def advance(self, dt_total: float) -> None:
        """把 dt_total 秒模拟时间拆成 0.05s 子步推进。"""
        if dt_total <= 0:
            return
        dt = 0.05
        n = max(1, min(int(round(dt_total / dt)), int(self.p["max_substeps"])))
        for _ in range(n):
            if self.state.melted:
                break
            self._substep(dt)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))
