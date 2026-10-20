"""逐格方向性 RBMK 模拟引擎。

交互逻辑来源：HBM-NTM-.1.0.27_X5846.jar（CFR 反编译）：
- 中子：RBMKNeutronHandler.RBMKNeutronStream（4 方向射线、射程 fluxRange=5、
  慢化剂改快/慢比、反射体衰减、吸收体吸热、控制棒按 level 衰减、燃料棒接收即停）
- 燃料：ItemRBMKRod.reactivityFunc / burn / xenonGenFunc / xenonBurnFunc（精确）
- 热量：TileEntityRBMKBase.moveHeat / coolPassively（四邻平均扩散 + 按邻接数被动冷却）
- 锅炉：TileEntityRBMKBoiler（热量 -> 蒸汽，heat -= waterUsed * heatPerMB）
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from rbmk.model.components import HEAT_FLUIDS, STEAM_TYPES, Behavior, FuelType, NType, behavior_of
from rbmk.model.reactor import ReactorModel

AMBIENT = 20.0
DIRS = ((0, 1), (1, 0), (0, -1), (-1, 0))  # 东南西北

DEFAULT_PARAMS = {
    "flux_range": 5,                 # RBMKKeys: dialFluxRange = 5
    "max_heat": 1500.0,             # TileEntityRBMKBase.maxHeat()：柱温熔毁阈值
    "column_height": 4,              # RBMKKeys: dialColumnHeight = 4
    "column_heat_flow": 0.2,         # RBMKKeys: dialColumnHeatFlow = 0.2
    "passive_cooling": 2.5,          # RBMKKeys: dialPassiveCooling = 2.5
    "passive_cooling_inner": 0.1,    # RBMKKeys: dialPassiveCoolingInner = 0.1
    "fuel_diffusion_mod": 1.0,       # RBMKKeys: dialDiffusionMod = 1.0
    "heat_provision": 0.2,           # RBMKKeys: dialHeatProvision = 0.2
    "moderator_efficiency": 1.0,     # RBMKKeys: dialModeratorEfficiency = 1.0
    "reflector_efficiency": 1.0,     # RBMKKeys: dialReflectorEfficiency = 1.0
    "absorber_efficiency": 1.0,      # RBMKKeys: dialAbsorberEfficiency = 1.0
    "absorber_heat_conversion": 0.05,  # RBMKKeys: dialAbsorberHeatConversion = 0.05
    "boiler_heat_consumption": 0.1,  # RBMKKeys: dialBoilerHeatConsumption = 0.1
    "boiler_feed": 10000.0,          # 模组锅炉 feed 罐容量（MB），视为持续供水
    "boiler_capacity": 50.0,           # 兼容旧参数（新公式不再使用）
    "control_speed_mod": 1.0,
    "reactivity_mod": 1.0,
    "surge_mod": 1.0,
    "turbine_efficiency": 0.30,
    "power_scale": 100.0,
    "warning_ratio": 0.60,
    "danger_ratio": 0.85,
    "max_substeps": 5000,
    "enable_xenon": True,
}


# ---------- 燃料公式（精确还原） ----------
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


def flux_from_type(ft: FuelType, quantity: float, ratio: float) -> float:
    """TileEntityRBMKRod.fluxFromType：按燃料对快/慢中子的敏感度取加权通量。"""
    fast = quantity * ratio
    slow = quantity * (1.0 - ratio)
    if ft.n_type == NType.SLOW:
        return slow + fast * 0.5
    if ft.n_type == NType.FAST:
        return fast + slow * 0.3
    return quantity


@dataclass
class EngineState:
    time: float = 0.0
    power: float = 0.0
    flux: float = 0.0
    temperature: float = AMBIENT
    avg_temperature: float = AMBIENT
    avg_flux: float = 0.0
    steam: float = 0.0
    electricity: float = 0.0
    total_energy: float = 0.0
    fuel_remaining: float = 100.0
    xenon: float = 0.0
    status: str = "normal"
    melted: bool = False
    melt_temp: float = 1500.0
    temp_rate: float = 0.0


class SimulationEngine:
    def __init__(self, model: ReactorModel, params: dict | None = None):
        self.model = model
        self.p = {**DEFAULT_PARAMS, **(params or {})}
        self.state = EngineState(melt_temp=self._melt_threshold())
        self._steam_tick = 0.0
        self._reset()

    # ---------- 初始化 ----------
    def _reset(self) -> None:
        for _, _, cell in self.model.iter_cells():
            cell.temp = AMBIENT
            cell.heat = 0.0
            cell.flux = 0.0
            cell.steam = 0.0
            cell.steam_rate = 0.0
            cell.heater_rate = 0.0
            cell.water = 100.0
            cell.xenon = 0.0
            cell.burnup = 0.0
            cell.flux_q = 0.0
            cell.flux_ratio = 0.0
            cell.last_flux_q = 0.0
            cell.last_flux_ratio = 0.0
            cell.has_rod = cell.fuel_type is not None and cell.fuel != "rbmk_fuel_empty"
            cell.core_heat = 20.0
            cell.hull_heat = 20.0
        self.state = EngineState(melt_temp=self._melt_threshold())

    def reset(self) -> None:
        self._reset()

    def _melt_threshold(self) -> float:
        """模组熔毁阈值：TileEntityRBMKBase.maxHeat() = 1500（与燃料熔点无关）。"""
        return float(self.p["max_heat"])

    # ---------- 中子 ----------
    def _burn(self, cell, ft: FuelType, flux_in: float) -> tuple[float, float]:
        p = self.p
        in_flux = flux_in + ft.self_rate
        if p["enable_xenon"] and ft.x_burn > 0:
            x0 = cell.xenon
            burn = in_flux * in_flux / ft.x_burn
            in_flux *= max(0.0, 1.0 - x0 / 100.0)
            gen = in_flux * ft.x_gen
            cell.xenon = _clamp(x0 - burn + gen, 0.0, 100.0)

        enrichment = max(0.0, 1.0 - cell.burnup)
        # 热系数（ItemRBMKRod.burn 中的 mult）
        if ft.heat_coeff_start != 0.0 and cell.temp >= ft.heat_coeff_start and ft.heat_coeff_length > 0:
            prog = min(1.0, (cell.temp - ft.heat_coeff_start) / ft.heat_coeff_length)
            enrichment *= math.sin((prog * math.pi + math.pi) / 2.0)

        out_flux = reactivity_function(ft, in_flux, enrichment)
        if ft.yield_ > 0:
            cell.burnup = min(1.0, cell.burnup + in_flux / ft.yield_)
        out_ratio = 0.0 if ft.r_type == NType.SLOW else 1.0
        return out_flux, out_ratio

    def _cast(self, r: int, c: int, dr: int, dc: int, flux: float, ratio: float, origin) -> None:
        """沿一个方向逐格推进中子射线（RBMKNeutronStream.runStreamInteraction）。"""
        p = self.p
        for i in range(1, p["flux_range"] + 1):
            nr, nc = r + dr * i, c + dc * i
            if not (0 <= nr < self.model.rows and 0 <= nc < self.model.cols):
                return
            cell = self.model.grid[nr][nc]
            if cell is None:
                continue  # 空气不阻挡中子
            b = behavior_of(cell.comp)

            if b == Behavior.MODERATOR:
                ratio *= (1.0 - p["moderator_efficiency"])
                continue

            if b == Behavior.CONTROL:
                level = 1.0 - self.model.effective_insertion(cell) / 100.0
                if level > 0.0:
                    flux *= level
                    continue
                return

            if b == Behavior.REFLECTOR:
                if p["reflector_efficiency"] == 1.0:
                    origin.flux_q += flux
                    origin.flux_ratio = ratio
                    return
                flux *= p["reflector_efficiency"]
                continue

            if b == Behavior.ABSORBER:
                cell.heat += p["absorber_heat_conversion"] * flux
                if p["absorber_efficiency"] == 1.0:
                    return
                flux *= p["absorber_efficiency"]
                continue

            if b == Behavior.FUEL:
                if not cell.has_rod or cell.fuel_type is None:
                    continue
                fast = cell.flux_q * cell.flux_ratio + flux * ratio
                cell.flux_q += flux
                cell.flux_ratio = fast / cell.flux_q if cell.flux_q > 0 else 0.0
                return

            # OTHER（结构柱/存储/冷却器/加热器/辐照通道）：中子直接穿过
            continue

    def _neutron_tick(self) -> None:
        p = self.p
        for _, _, cell in self.model.iter_cells():
            cell.flux_q = 0.0
            cell.flux_ratio = 0.0
            # 每 tick 从当前燃料推导，确保后放入/改过燃料的棒也会被处理
            cell.has_rod = cell.fuel_type is not None and cell.fuel != "rbmk_fuel_empty"

        rods = [(r, c, cell) for r, c, cell in self.model.iter_cells()
                if cell.has_rod and cell.fuel_type is not None]

        for r, c, cell in rods:
            ft = cell.fuel_type
            flux_in = flux_from_type(ft, cell.last_flux_q, cell.last_flux_ratio)
            out_flux, out_ratio = self._burn(cell, ft, flux_in)
            cell.flux = out_flux
            cell.heat = out_flux * ft.heat
            # 芯 -> 壳 -> 柱 热链（ItemRBMKRod.updateHeat / provideHeat）
            if cell.heat > 0.0:
                core = min(1_000_000.0, max(20.0, cell.core_heat + cell.heat))
                mid = (core - cell.hull_heat) / 2.0
                diff = mid * ft.diffusion * p["fuel_diffusion_mod"]
                cell.core_heat = core - diff
                cell.hull_heat += diff
                if cell.hull_heat > cell.temp:
                    ret = (cell.hull_heat - cell.temp) / 2.0 * p["heat_provision"]
                    cell.hull_heat -= ret
                    cell.temp += ret
            if out_flux > 0.0:
                for dr, dc in DIRS:
                    self._cast(r, c, dr, dc, out_flux, out_ratio, cell)

        for _, _, cell in rods:
            cell.last_flux_q = cell.flux_q
            cell.last_flux_ratio = cell.flux_ratio

    # ---------- 热量 ----------
    def _heat_tick(self) -> None:
        p = self.p
        cells = [(r, c, cell) for r, c, cell in self.model.iter_cells()]

        # 四邻平均扩散
        for r, c, cell in cells:
            nb = [self.model.cell_at(r + dr, c + dc) for dr, dc in DIRS]
            nb = [n for n in nb if n is not None]
            total = cell.temp + sum(n.temp for n in nb)
            avg = total / (len(nb) + 1)
            cell.temp += (avg - cell.temp) * p["column_heat_flow"]

        # 按邻接数被动冷却（邻接越少冷却越强）
        for r, c, cell in cells:
            n = sum(1 for dr, dc in DIRS if self.model.cell_at(r + dr, c + dc) is not None)
            outer = p["passive_cooling"]
            inner = p["passive_cooling_inner"]
            cooling = inner + (outer - inner) * ((4 - min(max(n, 0), 4)) / 4.0)
            cell.temp -= cooling
            if cell.temp < AMBIENT:
                cell.temp = AMBIENT

        # 锅炉：热量 -> 蒸汽
        steam = 0.0
        hpm = p["boiler_heat_consumption"]       # 0.1 热量 / MB 水
        feed = p["boiler_feed"]
        for r, c, cell in cells:
            if behavior_of(cell.comp) != Behavior.BOILER:
                continue
            cell.steam_rate = 0.0
            st = STEAM_TYPES.get(cell.steam_type, STEAM_TYPES["STEAM"])
            # 模组：heatProvided = heat - getHeatFromSteam(当前蒸汽类型)
            heat_provided = cell.temp - st.heat
            if heat_provided <= 0.0:
                continue
            # 模组产汽公式（TileEntityRBMKBoiler.func_145845_h）
            if st.key == "ULTRAHOTSTEAM":
                made = heat_provided / hpm * 100.0 / st.factor
                used = made / 100.0 * st.factor
                if feed < used:
                    made = feed * 100.0 / st.factor
                    used = made / 100.0 * st.factor
            else:
                used = min(heat_provided / hpm, feed)
                made = used * 100.0 / st.factor
            cell.water = max(0.0, feed - used)
            cell.steam += made
            cell.steam_rate = made
            cell.temp -= used * hpm
            steam += made
        self._steam_tick = steam

        # 流体加热器（TileEntityRBMKHeater，FT_Heatable / HEATEXCHANGER）
        for r, c, cell in cells:
            if behavior_of(cell.comp) != Behavior.HEATER:
                continue
            cell.heater_rate = 0.0
            hf = HEAT_FLUIDS.get(cell.heater_fluid, HEAT_FLUIDS["WATER"])
            if cell.temp <= 50.0:
                continue
            temp_range = cell.temp - hf.out_temp
            if temp_range <= 0.0 or hf.eff <= 0.0:
                continue
            tu_per_degree = 2000.0 * hf.eff
            # 模组：ops = min(输入量, 输出空间, 温度允许量)；这里用水池无限、输出直连
            ops = min(cell.heater_output / hf.amount_produced,
                      temp_range * tu_per_degree / hf.heat_req)
            if ops <= 0.0:
                continue
            cell.heater_rate = ops * hf.amount_produced
            cell.temp -= hf.heat_req * ops / tu_per_degree * hf.eff

        # 熔毁判定（满足任一即熔毁）：
        #   1) 任一组件柱温 > maxHeat() = 1500
        #   2) 燃料棒壳温（hull_heat）> 该燃料熔点
        melt_at = self.p["max_heat"]
        for _, _, cell in cells:
            if cell.temp > melt_at:
                self.state.melted = True
            ft = cell.fuel_type
            if cell.has_rod and ft and ft.melting_point > 0 and cell.hull_heat > ft.melting_point:
                self.state.melted = True

    # ---------- 状态 ----------
    def _update_state(self) -> None:
        p = self.p
        s = self.state
        rods = [(r, c, cell) for r, c, cell in self.model.iter_cells()
                if cell.has_rod and cell.fuel_type is not None]
        s.melt_temp = self._melt_threshold()

        total_flux = sum(cell.flux for _, _, cell in rods)
        total_heat = sum(cell.heat for _, _, cell in rods)
        max_temp = max((cell.temp for _, _, cell in self.model.iter_cells()), default=AMBIENT)
        all_cells = [cell for _, _, cell in self.model.iter_cells()]
        s.avg_temperature = (sum(c.temp for c in all_cells) / len(all_cells)) if all_cells else AMBIENT
        s.avg_flux = (total_flux / len(rods)) if rods else 0.0

        prev_temp = s.temperature
        s.time += 0.05
        s.power = total_heat * p["power_scale"]
        s.flux = total_flux
        s.temperature = max_temp
        s.temp_rate = (max_temp - prev_temp) / 0.05
        s.steam = self._steam_tick * 20.0          # mB/s（1 tick = 0.05 s）
        # 蒸汽以 mB 计：100 mB 蒸汽 ≈ 旧模型 1 单位水，除以 100 保持发电量标定不变
        s.electricity = s.steam / 100.0 * p["turbine_efficiency"] * p["power_scale"]
        s.total_energy += s.electricity * 0.05 / 3600.0

        if rods:
            s.fuel_remaining = 100.0 * (1.0 - sum(cell.burnup for _, _, cell in rods) / len(rods))
            s.xenon = sum(cell.xenon for _, _, cell in rods) / len(rods)

        melt = s.melt_temp or self.p["max_heat"]
        if s.melted:
            s.status = "meltdown"
        else:
            ratio = max_temp / melt if melt > 0 else 0.0
            if ratio >= p["danger_ratio"]:
                s.status = "danger"
            elif ratio >= p["warning_ratio"]:
                s.status = "warning"
            else:
                s.status = "normal"

    # ---------- 推进 ----------
    def advance(self, dt_total: float) -> None:
        if dt_total <= 0:
            return
        dt = 0.05
        n = max(1, min(int(round(dt_total / dt)), int(self.p["max_substeps"])))
        for _ in range(n):
            if self.state.melted:
                break
            self._neutron_tick()
            self._heat_tick()
            self._update_state()


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))
