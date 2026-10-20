"""模拟引擎：中子学、热、蒸汽、发电、燃料消耗、氙毒、熔毁。

燃料反应性/燃烧/氙毒公式与常量来自 HBM-NTM-.1.0.27_X5846.jar 反编译
（ItemRBMKRod.reactivityFunc / burn / xenonGenFunc / xenonBurnFunc）。
热工与全局通量标度为模型层（见 spec/rbmk-mechanics.md）。
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from rbmk.model.components import Behavior, FuelType, behavior_of
from rbmk.model.reactor import FUEL_TYPES, ReactorModel

AMBIENT = 25.0

DEFAULT_PARAMS = {
    "base_flux": 40.0,
    "moderator_efficiency": 0.30,
    "absorber_efficiency": 0.08,
    "reflector_efficiency": 0.25,
    "control_efficiency": 0.50,
    "heat_coeff": 0.50,
    "cooling_coeff": 0.03,
    "passive_cooling": 0.005,
    "turbine_efficiency": 0.30,
    "power_scale": 100.0,
    "warning_ratio": 0.60,
    "danger_ratio": 0.85,
    "max_substeps": 5000,
    "enable_xenon": True,
}


def depletion_modifier(dep_func: str, enrichment: float) -> float:
    e = enrichment
    if dep_func == "RAISING_SLOPE":
        return 1.0
    if dep_func == "BOOSTED_SLOPE":
        return e + math.sin((e - 1.0) * (e - 1.0) * math.pi)
    if dep_func == "GENTLE_SLOPE":
        return e + math.sin(e * math.pi) / 2.0
    if dep_func == "STATIC":
        return e + math.sin(e * math.pi) / 3.0
    return e  # LINEAR


def reactivity_function(ft: FuelType, in_flux: float, enrichment: float) -> float:
    flux = in_flux * depletion_modifier(ft.dep_func, enrichment)
    r = ft.reactivity
    f = ft.function
    if f == "PASSIVE":
        return ft.self_rate * enrichment
    if f == "LOG_TEN":
        return math.log10(flux + 1.0) * 0.5 * r
    if f == "PLATEU":
        return (1.0 - math.pow(math.e, -flux / 25.0)) * r
    if f == "ARCH":
        return max((flux - flux * flux / 10000.0) / 100.0 * r, 0.0)
    if f == "SIGMOID":
        return r / (1.0 + math.pow(math.e, -(flux - 50.0) / 10.0))
    if f == "SQUARE_ROOT":
        return math.sqrt(max(0.0, flux)) * r / 10.0
    if f == "LINEAR":
        return flux / 100.0 * r
    if f == "QUADRATIC":
        return flux * flux / 10000.0 * r
    if f == "EXPERIMENTAL":
        return flux * (math.sin(flux) + 1.0) * r
    return 0.0


@dataclass
class EngineState:
    time: float = 0.0
    power: float = 0.0
    flux: float = 0.0
    temperature: float = AMBIENT
    steam: float = 0.0
    electricity: float = 0.0
    total_energy: float = 0.0
    fuel_remaining: float = 100.0
    xenon: float = 0.0
    status: str = "normal"
    melted: bool = False
    melt_temp: float = 2800.0
    temp_rate: float = 0.0


class SimulationEngine:
    def __init__(self, model: ReactorModel, params: dict | None = None):
        self.model = model
        self.p = {**DEFAULT_PARAMS, **(params or {})}
        self.state = EngineState(melt_temp=self._min_melting())
        self._reset()

    def _reset(self) -> None:
        for _, _, cell in self.model.iter_cells():
            cell.temp = AMBIENT
            cell.heat = 0.0
            cell.flux = 0.0
            cell.steam = 0.0
            cell.water = 100.0
            cell.xenon = 0.0
        self.state = EngineState(melt_temp=self._min_melting())

    def reset(self) -> None:
        self._reset()

    def _min_melting(self) -> float:
        best = None
        for _, _, cell in self.model.iter_cells():
            ft = cell.fuel_type
            if behavior_of(cell.comp) == Behavior.FUEL and ft and ft.melting_point > 0:
                best = ft.melting_point if best is None else min(best, ft.melting_point)
        return best or 2800.0

    def _neighbors(self, r: int, c: int):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nb = self.model.cell_at(r + dr, c + dc)
                if nb is not None:
                    yield nb

    def _count(self, b: Behavior) -> int:
        return sum(1 for _, _, c in self.model.iter_cells() if behavior_of(c.comp) == b)

    def _control_absorption(self) -> float:
        total = 0.0
        for _, _, cell in self.model.control_cells():
            total += self.model.effective_insertion(cell) / 100.0
        return total

    def _fuel_cells(self):
        return [
            (r, c, cell)
            for r, c, cell in self.model.iter_cells()
            if behavior_of(cell.comp) == Behavior.FUEL and cell.fuel_type is not None
        ]

    def _substep(self, dt: float) -> None:
        p = self.p
        s = self.state
        if s.melted:
            return

        prev_temp = s.temperature
        fuel = self._fuel_cells()
        max_temp = s.temperature

        mod = self._count(Behavior.MODERATOR)
        refl = self._count(Behavior.REFLECTOR)
        absb = self._count(Behavior.ABSORBER)
        boiler = self._count(Behavior.BOILER)
        cooler = self._count(Behavior.COOLER)
        ctrl = self._control_absorption()

        mod_factor = 1.0 + p["moderator_efficiency"] * math.sqrt(mod)
        refl_factor = 1.0 + p["reflector_efficiency"] * math.sqrt(refl)
        abs_factor = 1.0 / (1.0 + p["absorber_efficiency"] * absb + p["control_efficiency"] * ctrl)

        flow = self.model.coolant_flow / 100.0
        # 冷却器额外提供冷却能力
        cooling = flow * p["cooling_coeff"] * (1.0 + 0.15 * cooler) + p["passive_cooling"]

        total_flux = 0.0
        total_heat = 0.0
        burn_sum = 0.0
        xenon_sum = 0.0

        for r, c, cell in fuel:
            ft = cell.fuel_type
            nmod = sum(1 for nb in self._neighbors(r, c)
                       if behavior_of(nb.comp) == Behavior.MODERATOR)
            in_flux = p["base_flux"] * mod_factor * refl_factor * abs_factor * (1.0 + 0.10 * nmod)
            in_flux += ft.self_rate

            if p["enable_xenon"] and ft.x_burn > 0:
                x0 = cell.xenon
                burn = in_flux * in_flux / ft.x_burn
                in_flux *= max(0.0, 1.0 - x0 / 100.0)
                gen = in_flux * ft.x_gen
                cell.xenon = _clamp(x0 - burn + gen, 0.0, 100.0)

            enrichment = max(0.0, 1.0 - cell.burnup)
            out_flux = reactivity_function(ft, in_flux, enrichment)
            cell.flux = out_flux
            cell.heat = out_flux * ft.heat
            total_flux += out_flux
            total_heat += cell.heat

            if ft.yield_ > 0:
                cell.burnup = min(1.0, cell.burnup + in_flux / ft.yield_)
            burn_sum += cell.burnup
            xenon_sum += cell.xenon

            dtemp = (cell.heat * p["heat_coeff"] - cooling * (cell.temp - AMBIENT)) * dt
            cell.temp += dtemp
            if cell.temp > max_temp:
                max_temp = cell.temp

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

        s.time += dt
        s.power = total_heat * p["power_scale"]
        s.flux = total_flux
        s.temperature = max_temp
        s.total_energy += s.electricity * dt / 3600.0
        if fuel:
            s.fuel_remaining = 100.0 * (1.0 - burn_sum / len(fuel))
            s.xenon = xenon_sum / len(fuel)
        s.temp_rate = (s.temperature - prev_temp) / dt if dt > 0 else 0.0

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

    def advance(self, dt_total: float) -> None:
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
