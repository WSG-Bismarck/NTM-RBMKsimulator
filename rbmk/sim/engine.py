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

from rbmk.model.components import (
    HEAT_FLUIDS,
    MODERATED_COMPONENTS,
    REASIM_COMPONENTS,
    STEAM_TYPES,
    Behavior,
    ComponentType,
    FuelType,
    NType,
    behavior_of,
)
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
    "boiler_feed": 10000.0,          # 模组锅炉 feed 罐容量（MB）
    "boiler_water_supply": 10000.0,  # 每 tick 补水速率（mB/tick）；10,000 = 等同于无限供水
    "boiler_tank": 1000000.0,        # 模组锅炉 steam 罐容量（MB）→ 每 tick 产汽上限
    "reasim_boiler_speed": 0.05,     # RBMKKeys: dialReasimBoilerSpeed = 0.05
    "reasim_boiler_capacity": 16000.0,  # ReaSim 单柱水/汽容量（mB）
    "heater_tank": 16000.0,          # 模组加热器输出罐容量（MB）→ 每 tick 加热上限
    "boiler_capacity": 50.0,           # 兼容旧参数（新公式不再使用）
    "control_speed_mod": 1.0,
    "reactivity_mod": 1.0,
    "surge_mod": 1.0,
    "turbine_efficiency": 0.30,   # 兼容旧参数：发电量已改用 FT_Coolable 换算，不再使用
    "power_scale": 100.0,
    "warning_ratio": 0.60,
    "danger_ratio": 0.85,
    "max_substeps": 5000,
    "enable_xenon": True,
}


# ---------- 燃料公式（精确还原） ----------
def depletion_modifier(dep_func: str, enrichment: float) -> float:
    """ItemRBMKRod.reactivityModByEnrichment（switch case 见 ItemRBMKRod$1 映射表）。"""
    e = enrichment
    if dep_func == "STATIC":                       # case 2
        return 1.0
    if dep_func == "BOOSTED_SLOPE":                # case 3
        return e + math.sin((e - 1.0) * (e - 1.0) * math.pi)
    if dep_func == "RAISING_SLOPE":                # case 4
        return e + math.sin(e * math.pi) / 2.0
    if dep_func == "GENTLE_SLOPE":                 # case 5
        return e + math.sin(e * math.pi) / 3.0
    return e  # LINEAR (case 1)


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
            cell.shown_temp = AMBIENT
            cell.heat = 0.0
            cell.flux = 0.0
            cell.steam = 0.0
            cell.steam_rate = 0.0
            cell.heater_rate = 0.0
            cell.heater_heat = 0.0
            cell.water = self.p["boiler_feed"]
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
        if ft.heat_coeff_start != 0.0 and cell.core_heat >= ft.heat_coeff_start and ft.heat_coeff_length > 0:
            prog = min(1.0, (cell.core_heat - ft.heat_coeff_start) / ft.heat_coeff_length)
            enrichment *= math.sin((prog * math.pi + math.pi) / 2.0)

        out_flux = reactivity_function(ft, in_flux, enrichment) * p["reactivity_mod"]
        if ft.yield_ > 0:
            cell.burnup = min(1.0, cell.burnup + in_flux / ft.yield_)
        out_ratio = 0.0 if ft.r_type == NType.SLOW else 1.0
        return out_flux, out_ratio

    def _cast_positions(self, positions, flux: float, ratio: float, origin) -> None:
        """按坐标序列逐格推进中子射线（RBMKNeutronStream.runStreamInteraction）。"""
        p = self.p
        moderated = 0
        for nr, nc in positions:
            if not (0 <= nr < self.model.rows and 0 <= nc < self.model.cols):
                return
            cell = self.model.grid[nr][nc]
            if cell is None:
                continue  # 空气不阻挡中子
            b = behavior_of(cell.comp)

            # 模组：type == MODERATOR || nodeTE.isModerated() → moderateStream()
            if b == Behavior.MODERATOR or cell.comp in MODERATED_COMPONENTS:
                moderated += 1
                ratio *= (1.0 - p["moderator_efficiency"])
                if b == Behavior.MODERATOR:
                    continue

            if b == Behavior.CONTROL:
                if cell.comp == ComponentType.RBMK_CONTROL_AUTO:
                    level = cell.level          # 自动棒：模组 level 即透过率 getMult()
                else:
                    level = 1.0 - self.model.effective_insertion(cell) / 100.0
                if level > 0.0:
                    flux *= level
                    continue
                return

            if b == Behavior.REFLECTOR:
                # 模组：origin 自身带慢化也计一次，再按累计次数把反射流慢化一遍
                if origin.comp in MODERATED_COMPONENTS:
                    moderated += 1
                if ratio > 0.0:
                    for _ in range(moderated):
                        ratio *= (1.0 - p["moderator_efficiency"])
                if p["reflector_efficiency"] == 1.0:
                    # TileEntityRBMKRod.receiveFlux：快/慢通量按数量加权合并，不能覆盖
                    fast = origin.flux_q * origin.flux_ratio + flux * ratio
                    origin.flux_q += flux
                    origin.flux_ratio = fast / origin.flux_q if origin.flux_q > 0 else 0.0
                    return
                flux *= p["reflector_efficiency"]
                continue

            if b == Behavior.ABSORBER:
                # 模组：absorber.heat += absorberHeatConversion * flux，直接加在柱温上
                gained = p["absorber_heat_conversion"] * flux
                cell.temp += gained
                cell.heat = gained
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

    def _cast(self, r: int, c: int, dr: int, dc: int, flux: float, ratio: float, origin) -> None:
        """普通模式：沿 4 个正方向逐格推进。"""
        steps = [(r + dr * i, c + dc * i) for i in range(1, self.p["flux_range"] + 1)]
        self._cast_positions(steps, flux, ratio, origin)

    def _cast_vector(self, r: int, c: int, vx: float, vz: float,
                     flux: float, ratio: float, origin) -> None:
        """ReaSim：按向量步进，位置 = floor(0.5 + v * i)（与模组一致）。"""
        steps = [
            (r + int(math.floor(0.5 + vx * i)), c + int(math.floor(0.5 + vz * i)))
            for i in range(1, self.p["flux_range"] + 1)
        ]
        self._cast_positions(steps, flux, ratio, origin)

    def _spread_reasim(self, r: int, c: int, flux: float, ratio: float, origin) -> None:
        """TileEntityRBMKRodReaSim.spreadFlux：8 条 45° 射线，每条 0.75 倍通量。"""
        f = flux * 0.75
        for deg in range(0, 360, 45):
            rad = math.radians(deg)
            self._cast_vector(r, c, math.cos(rad), math.sin(rad), f, ratio, origin)

    def _begin_tick(self) -> None:
        """清空本 tick 的接收缓冲，并推导是否有燃料棒。"""
        for _, _, cell in self.model.iter_cells():
            cell.flux_q = 0.0
            cell.flux_ratio = 0.0
            cell.has_rod = cell.fuel_type is not None and cell.fuel != "rbmk_fuel_empty"

    def _end_tick(self) -> None:
        """把本 tick 接收到的通量存为下一 tick 的燃烧输入（模组 fluxQuantity → 下一 tick）。"""
        for _, _, cell in self.model.iter_cells():
            if cell.has_rod:
                cell.last_flux_q = cell.flux_q
                cell.last_flux_ratio = cell.flux_ratio

    def _rod_step(self, cell) -> tuple[float, float]:
        """燃料棒 tick 前半段：burn → updateHeat → provideHeat（在 moveHeat 之前）。

        模组里这段和 moveHeat 都在同一根柱自己的 tick 内执行，所以此处的
        cell.temp 可能已经被「先 tick 的邻柱」更新过。
        """
        p = self.p
        ft = cell.fuel_type
        flux_in = flux_from_type(ft, cell.last_flux_q, cell.last_flux_ratio)
        out_flux, out_ratio = self._burn(cell, ft, flux_in)
        cell.flux = out_flux
        cell.heat = out_flux * ft.heat
        cell.core_heat = _clamp(cell.core_heat + cell.heat, 20.0, 1_000_000.0)

        # updateHeat：只有芯温 > 壳温时才向壳传热
        if cell.core_heat > cell.hull_heat:
            mid = (cell.core_heat - cell.hull_heat) / 2.0
            diff = mid * ft.diffusion * p["fuel_diffusion_mod"]
            cell.core_heat = _clamp(cell.core_heat - diff, 20.0, 1_000_000.0)
            cell.hull_heat = _clamp(cell.hull_heat + diff, 20.0, 1_000_000.0)

        # provideHeat
        if cell.hull_heat > ft.melting_point:
            # 条件②：壳温一旦超过燃料熔点即判定熔毁（模组随后仍会做三者均分）
            self.state.melted = True
            avg = (cell.temp + cell.hull_heat + cell.core_heat) / 3.0
            cell.core_heat = avg
            cell.hull_heat = avg
            cell.temp = avg
        elif cell.hull_heat > cell.temp:
            ret = (cell.hull_heat - cell.temp) / 2.0 * p["heat_provision"]
            cell.hull_heat -= ret
            cell.temp += ret
        return out_flux, out_ratio

    def _emit(self, r: int, c: int, cell, out_flux: float, out_ratio: float) -> None:
        if out_flux <= 0.0:
            return
        if cell.comp in REASIM_COMPONENTS:
            self._spread_reasim(r, c, out_flux, out_ratio, cell)
        else:
            for dr, dc in DIRS:
                self._cast(r, c, dr, dc, out_flux, out_ratio, cell)

    # ---------- 热量 ----------
    def _boil_one(self, cell, hpm: float) -> float:
        """单根普通蒸汽管道产汽（TileEntityRBMKBoiler）；模组里在 moveHeat 之前执行。"""
        p = self.p
        # 供水：水箱余量 + 本 tick 补水（管道），不超过 feed 罐容量
        feed = min(cell.water + p["boiler_water_supply"], p["boiler_feed"])
        st = STEAM_TYPES.get(cell.steam_type, STEAM_TYPES["STEAM"])
        heat_provided = cell.temp - st.heat
        if heat_provided <= 0.0:
            return 0.0
        if st.key == "ULTRAHOTSTEAM":
            made = math.floor(heat_provided / hpm * 100.0 / st.factor)
            used = math.floor(made / 100.0 * st.factor)
            if feed < used:
                made = math.floor(feed * 100.0 / st.factor)
                used = math.floor(made / 100.0 * st.factor)
        else:
            used = math.floor(heat_provided / hpm)
            used = min(used, feed)
            made = math.floor(used * 100.0 / st.factor)
        if made > p["boiler_tank"]:
            made = p["boiler_tank"]
            used = made * st.factor / 100.0
        cell.water = max(0.0, feed - used)
        cell.steam += made
        cell.steam_rate += made
        cell.temp -= used * hpm
        return made

    def _boil_one_reasim(self, cell, hpm: float) -> float:
        """单根 ReaSim 锅炉（TileEntityRBMKBase.boilWater）；在 moveHeat + 冷却之后执行。"""
        p = self.p
        if cell.temp < 100.0:
            return 0.0
        avail_heat = (cell.temp - 100.0) / hpm
        made = math.floor(min(avail_heat, p["reasim_boiler_capacity"]) * p["reasim_boiler_speed"])
        if made <= 0.0:
            return 0.0
        cell.steam += made
        cell.steam_rate += made
        cell.reasim_steam_rate += made
        cell.temp -= made * hpm
        return made

    def _heat_one(self, cell) -> None:
        """单根流体加热器（TileEntityRBMKHeater）；模组里在 moveHeat 之前执行。"""
        p = self.p
        cell.heater_rate = 0.0
        cell.heater_heat = 0.0
        hf = HEAT_FLUIDS.get(cell.heater_fluid, HEAT_FLUIDS["COOLANT"])
        if cell.temp <= 50.0:
            return
        temp_range = cell.temp - hf.out_temp
        if temp_range <= 0.0 or hf.eff <= 0.0:
            return
        tu_per_degree = 2000.0 * hf.eff
        ops = temp_range * tu_per_degree / hf.heat_req
        if ops <= 0.0:
            return
        produced = ops * hf.amount_produced
        if produced > p["heater_tank"]:
            ops = p["heater_tank"] / hf.amount_produced
            produced = p["heater_tank"]
        cell.heater_rate = produced
        cell.heater_heat = produced * (hf.cool_heat / hf.cool_amount) * hf.cool_eff
        cell.temp -= hf.heat_req * ops / tu_per_degree * hf.eff

    def _cool_one(self, r: int, c: int, cell) -> None:
        """冷却器（TileEntityRBMKCooler）：每 tick 消耗 50 mB 冷四氟甲烷，
        把 5×5 范围内每根 RBMK 柱的 heat 减去 200（下限 20）。"""
        count = 0
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                other = self.model.cell_at(r + dr, c + dc)
                if other is None:
                    continue
                other.temp -= 200.0
                if other.temp < AMBIENT:
                    other.temp = AMBIENT
                count += 1
        cell.cooler_cells = count
        cell.cooler_rate = 50.0 if count else 0.0

    def _auto_control_step(self, cell) -> None:
        """自动控制棒（TileEntityRBMKControlAuto）：按自身柱温算目标插入度，再按 0.00277/tick 逼近。"""
        p = self.p
        h = cell.temp
        lo = min(cell.heat_lower, cell.heat_upper)
        hi = max(cell.heat_lower, cell.heat_upper)
        if h < lo:
            faux = cell.level_lower
        elif h > hi:
            faux = cell.level_upper
        elif cell.auto_func == "QUAD_UP":
            denom = cell.heat_upper - cell.heat_lower
            faux = ((h - cell.heat_lower) / denom) ** 2 * (cell.level_upper - cell.level_lower) + cell.level_lower if denom else cell.level_lower
        elif cell.auto_func == "QUAD_DOWN":
            denom = cell.heat_lower - cell.heat_upper
            faux = ((h - cell.heat_upper) / denom) ** 2 * (cell.level_lower - cell.level_upper) + cell.level_upper if denom else cell.level_upper
        else:  # LINEAR
            denom = cell.heat_upper - cell.heat_lower
            faux = (h - cell.heat_lower) * ((cell.level_upper - cell.level_lower) / denom) + cell.level_lower if denom else cell.level_lower
        target = _clamp(faux * 0.01, 0.0, 1.0)
        cell.target_level = target
        speed = 0.00277 * p["control_speed_mod"]
        if cell.level < target:
            cell.level = min(target, cell.level + speed)
        elif cell.level > target:
            cell.level = max(target, cell.level - speed)

    def _heat_tick(self) -> None:
        """逐柱执行，顺序与模组 TE tick 一致：
        锅炉/加热器自身逻辑 → moveHeat（自身+四邻）→ 被动冷却 → ReaSim 产汽。"""
        p = self.p
        # 模组里同一区块的 TE 按加入顺序 tick（HashMap 同桶内为插入顺序），
        # 因此逐柱处理必须按放置顺序，否则同一构型换个方向摆放读数就会变。
        cells = [(r, c, cell) for r, c, cell in self.model.iter_cells_placed()]
        hpm = p["boiler_heat_consumption"]       # 0.1 热量 / MB 水
        reasim = self.model.reasim_boilers
        steam = 0.0
        for _, _, cell in cells:
            cell.steam_rate = 0.0
            cell.reasim_steam_rate = 0.0
            cell.shown_temp = cell.temp

        for r, c, cell in cells:
            b = behavior_of(cell.comp)
            emitted = None
            if b == Behavior.COOLER:
                self._cool_one(r, c, cell)
            elif b == Behavior.FUEL and cell.has_rod and cell.fuel_type is not None:
                emitted = self._rod_step(cell)
            elif b == Behavior.CONTROL and cell.comp == ComponentType.RBMK_CONTROL_AUTO:
                self._auto_control_step(cell)
            elif b == Behavior.BOILER:
                # 模组：TileEntityRBMKBoiler 自己的产汽逻辑无条件执行，
                # 之后 super.func_145845_h() 里再（在 ReaSim 开启时）跑一次 boilWater
                steam += self._boil_one(cell, hpm)
            elif b == Behavior.HEATER:
                self._heat_one(cell)

            # moveHeat：取「自身 + 存在的四邻」的平均值，自身与每个邻柱都按此调整
            nb = [self.model.cell_at(r + dr, c + dc) for dr, dc in DIRS]
            nb = [n for n in nb if n is not None]
            avg = (cell.temp + sum(n.temp for n in nb)) / (len(nb) + 1)
            for x in (cell, *nb):
                x.temp += (avg - x.temp) * p["column_heat_flow"]

            # coolPassively：只降自己，邻接越少散热越强
            n = len(nb)
            outer = p["passive_cooling"]
            inner = p["passive_cooling_inner"]
            cell.temp -= inner + (outer - inner) * ((4 - min(max(n, 0), 4)) / 4.0)
            if cell.temp < AMBIENT:
                cell.temp = AMBIENT

            if reasim:
                steam += self._boil_one_reasim(cell, hpm)

            if emitted is not None:
                self._emit(r, c, cell, emitted[0], emitted[1])

            # 模组里每根柱在自己的 tick 结束时把 heat 同步给客户端；
            # 控制台/物品提示显示的就是这个「自己 tick 结束时」的快照，
            # 而不是全世界 tick 结束后的值（后者还会被后 tick 的邻柱再改一次）。
            cell.shown_temp = cell.temp

        self._steam_tick = steam

        # 熔毁判定（模组：rod 在自己的 tick 里、moveHeat 之后判定；这里统一在末端判定）
        melt_at = p["max_heat"]
        for _, _, cell in cells:
            if cell.temp > melt_at:
                self.state.melted = True
            ft = cell.fuel_type
            if cell.has_rod and ft is not None and ft.melting_point > 0 and cell.hull_heat > ft.melting_point:
                self.state.melted = True

    def _update_state(self) -> None:
        p = self.p
        s = self.state
        rods = [(r, c, cell) for r, c, cell in self.model.iter_cells()
                if cell.has_rod and cell.fuel_type is not None]
        s.melt_temp = self._melt_threshold()

        total_flux = sum(cell.flux for _, _, cell in rods)
        total_heat = sum(cell.heat for _, _, cell in rods)
        max_temp = max((cell.shown_temp for _, _, cell in self.model.iter_cells()), default=AMBIENT)
        all_cells = [cell for _, _, cell in self.model.iter_cells()]
        s.avg_temperature = (sum(c.shown_temp for c in all_cells) / len(all_cells)) if all_cells else AMBIENT
        s.avg_flux = (total_flux / len(rods)) if rods else 0.0

        prev_temp = s.temperature
        s.time += 0.05
        s.power = total_heat * p["power_scale"]
        s.flux = total_flux
        s.temperature = max_temp
        s.temp_rate = (max_temp - prev_temp) / 0.05
        s.steam = self._steam_tick * 20.0          # mB/s（1 tick = 0.05 s）
        # 蒸汽以 mB 计：100 mB 蒸汽 ≈ 旧模型 1 单位水，除以 100 保持发电量标定不变
        # 瞬时发电量（HE/tick）：每 tick 产出的各类蒸汽，按最优路径（逐级冷却到低压蒸汽）
        # 经汽轮机换算成 HE。汽轮机效率 eff_steam_turbine = 1.0。
        he = 0.0
        for _, _, cell in self.model.iter_cells():
            if cell.steam_rate > 0.0:
                st = STEAM_TYPES.get(cell.steam_type, STEAM_TYPES["STEAM"])
                he += cell.steam_rate * st.he_per_mb
        s.electricity = he
        s.total_energy += he

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
            self._begin_tick()
            self._heat_tick()
            self._end_tick()
            self._update_state()


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))
