"""组件、控制组、燃料类型定义。

数据来源：HBM-NTM-.1.0.27_X5846.jar
- 组件：从 ModBlocks 的 33 个 rbmk_* 方块中，移除自动装填机、ReaSim 进出水口、
  蒸汽导出器以及全部控制/显示设备后，保留 18 种反应堆核心组件；
  中文名取自 assets/hbm/lang/zh_CN.lang
- 控制组 5 色：TileEntityRBMKControlManual$RBMKColor
- 燃料 34 种：ModItems 中 rbmk_fuel_* 注册，逐项精确提取（见 fuel_data.py）
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from rbmk.model.fuel_data import FUEL_DATA


class ComponentType(str, Enum):
    # ---- 反应堆核心组件（18）----
    RBMK_ROD = "rbmk_rod"
    RBMK_ROD_MOD = "rbmk_rod_mod"
    RBMK_ROD_REASIM = "rbmk_rod_reasim"
    RBMK_ROD_REASIM_MOD = "rbmk_rod_reasim_mod"
    RBMK_CONTROL = "rbmk_control"
    RBMK_CONTROL_AUTO = "rbmk_control_auto"
    RBMK_CONTROL_MOD = "rbmk_control_mod"
    RBMK_CONTROL_REASIM = "rbmk_control_reasim"
    RBMK_CONTROL_REASIM_AUTO = "rbmk_control_reasim_auto"
    RBMK_BOILER = "rbmk_boiler"
    RBMK_MODERATOR = "rbmk_moderator"
    RBMK_ABSORBER = "rbmk_absorber"
    RBMK_REFLECTOR = "rbmk_reflector"
    RBMK_OUTGASSER = "rbmk_outgasser"
    RBMK_STORAGE = "rbmk_storage"
    RBMK_COOLER = "rbmk_cooler"
    RBMK_BLANK = "rbmk_blank"
    RBMK_HEATER = "rbmk_heater"


# 标准中文名（assets/hbm/lang/zh_CN.lang） + 界面颜色
COMPONENT_INFO: dict[ComponentType, tuple[str, str]] = {
    ComponentType.RBMK_ROD: ("RBMK反应堆燃料通道", "#e8a33d"),
    ComponentType.RBMK_ROD_MOD: ("RBMK反应堆慢化燃料通道", "#f0c060"),
    ComponentType.RBMK_ROD_REASIM: ("RBMK反应堆燃料通道(ReaSim)", "#d98f2a"),
    ComponentType.RBMK_ROD_REASIM_MOD: ("RBMK反应堆慢化燃料通道(ReaSim)", "#e0b050"),
    ComponentType.RBMK_CONTROL: ("RBMK反应堆控制棒", "#c8d2db"),
    ComponentType.RBMK_CONTROL_AUTO: ("RBMK反应堆自动控制棒", "#aab8c6"),
    ComponentType.RBMK_CONTROL_MOD: ("RBMK反应堆慢化控制棒", "#9aa7b4"),
    ComponentType.RBMK_CONTROL_REASIM: ("RBMK反应堆控制棒 (ReaSim)", "#b8c2cc"),
    ComponentType.RBMK_CONTROL_REASIM_AUTO: ("RBMK反应堆自动控制棒 (ReaSim)", "#8f9aa5"),
    ComponentType.RBMK_BOILER: ("RBMK反应堆蒸汽管道", "#5aa9e6"),
    ComponentType.RBMK_MODERATOR: ("RBMK反应堆石墨慢化剂", "#6b6f76"),
    ComponentType.RBMK_ABSORBER: ("RBMK反应堆硼中子吸收器", "#a78bd6"),
    ComponentType.RBMK_REFLECTOR: ("RBMK反应堆碳化钨中子反射器", "#aab4be"),
    ComponentType.RBMK_OUTGASSER: ("RBMK反应堆辐照通道", "#c98a5a"),
    ComponentType.RBMK_STORAGE: ("RBMK燃料棒存储棒", "#8a8f98"),
    ComponentType.RBMK_COOLER: ("RBMK冷却器", "#38b2a6"),
    ComponentType.RBMK_BLANK: ("RBMK反应堆结构柱", "#3a4149"),
    ComponentType.RBMK_HEATER: ("RBMK流体加热器", "#d08a4a"),
}

# 网格内的简写标记
COMPONENT_SHORT: dict[ComponentType, str] = {
    ComponentType.RBMK_ROD: "燃",
    ComponentType.RBMK_ROD_MOD: "燃M",
    ComponentType.RBMK_ROD_REASIM: "燃R",
    ComponentType.RBMK_ROD_REASIM_MOD: "燃RM",
    ComponentType.RBMK_CONTROL: "控",
    ComponentType.RBMK_CONTROL_AUTO: "自控",
    ComponentType.RBMK_CONTROL_MOD: "控M",
    ComponentType.RBMK_CONTROL_REASIM: "控R",
    ComponentType.RBMK_CONTROL_REASIM_AUTO: "自R",
    ComponentType.RBMK_BOILER: "蒸",
    ComponentType.RBMK_MODERATOR: "慢",
    ComponentType.RBMK_ABSORBER: "吸",
    ComponentType.RBMK_REFLECTOR: "反",
    ComponentType.RBMK_OUTGASSER: "辐",
    ComponentType.RBMK_STORAGE: "存",
    ComponentType.RBMK_COOLER: "冷",
    ComponentType.RBMK_BLANK: "结",
    ComponentType.RBMK_HEATER: "热",
}


class Behavior(str, Enum):
    FUEL = "fuel"
    CONTROL = "control"
    BOILER = "boiler"
    MODERATOR = "moderator"
    ABSORBER = "absorber"
    REFLECTOR = "reflector"
    OUTGASSER = "outgasser"
    STORAGE = "storage"
    COOLER = "cooler"
    BLANK = "blank"
    HEATER = "heater"


COMPONENT_BEHAVIOR: dict[ComponentType, Behavior] = {
    ComponentType.RBMK_ROD: Behavior.FUEL,
    ComponentType.RBMK_ROD_MOD: Behavior.FUEL,
    ComponentType.RBMK_ROD_REASIM: Behavior.FUEL,
    ComponentType.RBMK_ROD_REASIM_MOD: Behavior.FUEL,
    ComponentType.RBMK_CONTROL: Behavior.CONTROL,
    ComponentType.RBMK_CONTROL_AUTO: Behavior.CONTROL,
    ComponentType.RBMK_CONTROL_MOD: Behavior.CONTROL,
    ComponentType.RBMK_CONTROL_REASIM: Behavior.CONTROL,
    ComponentType.RBMK_CONTROL_REASIM_AUTO: Behavior.CONTROL,
    ComponentType.RBMK_BOILER: Behavior.BOILER,
    ComponentType.RBMK_MODERATOR: Behavior.MODERATOR,
    ComponentType.RBMK_ABSORBER: Behavior.ABSORBER,
    ComponentType.RBMK_REFLECTOR: Behavior.REFLECTOR,
    ComponentType.RBMK_OUTGASSER: Behavior.OUTGASSER,
    ComponentType.RBMK_STORAGE: Behavior.STORAGE,
    ComponentType.RBMK_COOLER: Behavior.COOLER,
    ComponentType.RBMK_BLANK: Behavior.BLANK,
    ComponentType.RBMK_HEATER: Behavior.HEATER,
}

CORE_COMPONENTS: list[ComponentType] = list(ComponentType)
AUX_COMPONENTS: list[ComponentType] = []

# 模组里 block.moderated = true 的组件：中子流经过/命中时按 moderatorEfficiency 降低快中子占比
MODERATED_COMPONENTS: frozenset[ComponentType] = frozenset({
    ComponentType.RBMK_ROD_MOD,
    ComponentType.RBMK_ROD_REASIM_MOD,
    ComponentType.RBMK_CONTROL_MOD,
})

# ReaSim 燃料通道：8 方向 45° 扩散（TileEntityRBMKRodReaSim.spreadFlux）
REASIM_COMPONENTS: frozenset[ComponentType] = frozenset({
    ComponentType.RBMK_ROD_REASIM,
    ComponentType.RBMK_ROD_REASIM_MOD,
})

FUEL_COMPONENTS: tuple[ComponentType, ...] = tuple(
    c for c in ComponentType if COMPONENT_BEHAVIOR[c] == Behavior.FUEL
)
CONTROL_COMPONENTS: tuple[ComponentType, ...] = tuple(
    c for c in ComponentType if COMPONENT_BEHAVIOR[c] == Behavior.CONTROL
)


def behavior_of(comp: ComponentType) -> Behavior:
    return COMPONENT_BEHAVIOR[comp]


class ControlGroup(str, Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"
    BLUE = "BLUE"
    PURPLE = "PURPLE"


CONTROL_GROUP_COLORS: dict[ControlGroup, str] = {
    ControlGroup.RED: "#e5484d",
    ControlGroup.YELLOW: "#f0c040",
    ControlGroup.GREEN: "#3ecf8e",
    ControlGroup.BLUE: "#4f9de8",
    ControlGroup.PURPLE: "#a78bd6",
}
CONTROL_GROUP_NAMES: dict[ControlGroup, str] = {
    ControlGroup.RED: "红组",
    ControlGroup.YELLOW: "黄组",
    ControlGroup.GREEN: "绿组",
    ControlGroup.BLUE: "蓝组",
    ControlGroup.PURPLE: "紫组",
}


class NType(str, Enum):
    FAST = "FAST"
    SLOW = "SLOW"
    ANY = "ANY"


# 显示用中文名（引擎里仍使用模组原始枚举值）
NTYPE_NAMES_CN: dict[str, str] = {
    "FAST": "快中子",
    "SLOW": "慢中子",
    "ANY": "任意中子",
}

FUNCTION_NAMES_CN: dict[str, str] = {
    "PASSIVE": "恒定输出",
    "LOG_TEN": "对数型",
    "PLATEU": "平台型",
    "ARCH": "拱形",
    "SIGMOID": "S 形",
    "SQUARE_ROOT": "平方根",
    "LINEAR": "线性",
    "QUADRATIC": "二次方",
    "EXPERIMENTAL": "实验型",
}


@dataclass(frozen=True)
class SteamType:
    """RBMK 蒸汽管道可产出的蒸汽类型（TileEntityRBMKBoiler）。"""
    key: str
    name_cn: str
    heat: float      # getHeatFromSteam()：产汽所需的最低柱温
    factor: float    # getFactorFromSteam()：水 -> 蒸汽的压缩倍率


# 中文名取自 jar 内 assets/hbm/lang/zh_CN.lang 的 hbmfluid.*
STEAM_TYPES: dict[str, SteamType] = {
    "STEAM": SteamType("STEAM", "蒸汽", 100.0, 1.0),
    "HOTSTEAM": SteamType("HOTSTEAM", "热蒸汽", 300.0, 10.0),
    "SUPERHOTSTEAM": SteamType("SUPERHOTSTEAM", "超热蒸汽", 450.0, 100.0),
    "ULTRAHOTSTEAM": SteamType("ULTRAHOTSTEAM", "超浓密蒸汽", 600.0, 1000.0),
}


@dataclass(frozen=True)
class HeatFluid:
    """RBMK 流体加热器可加热的流体（FT_Heatable，HEATEXCHANGER 效率 > 0）。"""
    key: str
    name_cn: str
    out_key: str
    out_name_cn: str
    amount_req: float      # 每次操作消耗的输入流体（mB）
    amount_produced: float # 每次操作产出的热流体（mB）
    heat_req: float        # 每次操作需要的热量（TU）
    out_temp: float        # 产出流体的温度（FluidType.temperature）
    eff: float             # HEATEXCHANGER 效率（加热侧）
    cool_heat: float = 0.0   # 产出流体 FT_Coolable.heatEnergy（TU / 次冷却）
    cool_amount: float = 1.0 # 产出流体 FT_Coolable.amountReq（mB / 次冷却）
    cool_eff: float = 1.0    # 产出流体 FT_Coolable HEATEXCHANGER 效率


# 数据取自 Fluids.java 的 FT_Heatable / FT_Coolable 注册
HEAT_FLUIDS: dict[str, HeatFluid] = {
    "WATER": HeatFluid("WATER", "水", "STEAM", "蒸汽", 1, 100, 200, 100, 0.25, 200, 100, 0.5),
    "OIL": HeatFluid("OIL", "原油", "HOTOIL", "热原油", 1, 1, 10, 350, 1.0, 10, 1, 1.0),
    "OIL_DS": HeatFluid("OIL_DS", "脱硫原油", "HOTOIL_DS", "热的脱硫原油", 1, 1, 10, 350, 1.0, 10, 1, 1.0),
    "CRACKOIL": HeatFluid("CRACKOIL", "裂化油", "HOTCRACKOIL", "热裂化油", 1, 1, 10, 350, 1.0, 10, 1, 1.0),
    "CRACKOIL_DS": HeatFluid("CRACKOIL_DS", "脱硫裂化油", "HOTCRACKOIL_DS", "热的脱硫裂化油", 1, 1, 10, 350, 1.0, 10, 1, 1.0),
    "COOLANT": HeatFluid("COOLANT", "冷却液", "COOLANT_HOT", "热冷却液", 1, 1, 300, 600, 1.0, 300, 1, 1.0),
    "PERFLUOROMETHYL": HeatFluid("PERFLUOROMETHYL", "四氟甲烷", "PERFLUOROMETHYL_HOT", "热四氟甲烷", 1, 1, 300, 250, 1.0, 300, 1, 1.0),
    "MUG": HeatFluid("MUG", "Mug牌树根饮料", "MUG_HOT", "热的Mug牌树根饮料", 1, 1, 400, 500, 1.0, 400, 1, 1.0),
    "BLOOD": HeatFluid("BLOOD", "血", "BLOOD_HOT", "热的血", 1, 1, 500, 666, 1.0, 500, 1, 1.0),
}


class RBMKType(str, Enum):
    ROD = "ROD"
    MODERATOR = "MODERATOR"
    CONTROL_ROD = "CONTROL_ROD"
    REFLECTOR = "REFLECTOR"
    ABSORBER = "ABSORBER"
    OUTGASSER = "OUTGASSER"
    OTHER = "OTHER"


@dataclass(frozen=True)
class FuelType:
    key: str
    name_cn: str
    reactivity: float
    self_rate: float
    function: str
    dep_func: str
    heat: float
    yield_: float
    melting_point: float
    diffusion: float
    x_gen: float
    x_burn: float
    n_type: NType
    r_type: NType
    heat_coeff_start: float
    heat_coeff_length: float

    @property
    def is_self_igniting(self) -> bool:
        """selfRate > 0：模组中的“自燃”燃料，无需外部中子源即可发射中子。"""
        return self.self_rate > 0.0

    def to_dict(self) -> dict:
        return {
            "key": self.key, "name_cn": self.name_cn,
            "reactivity": self.reactivity, "self_rate": self.self_rate,
            "function": self.function, "dep_func": self.dep_func,
            "heat": self.heat, "yield": self.yield_,
            "melting_point": self.melting_point, "diffusion": self.diffusion,
            "x_gen": self.x_gen, "x_burn": self.x_burn,
            "n_type": self.n_type.value, "r_type": self.r_type.value,
            "heat_coeff_start": self.heat_coeff_start,
            "heat_coeff_length": self.heat_coeff_length,
        }


def _build_fuels() -> dict[str, FuelType]:
    out: dict[str, FuelType] = {}
    order = ["rbmk_fuel_empty"] + [k for k in FUEL_DATA if k != "rbmk_fuel_empty"]
    for key in order:
        d = FUEL_DATA[key]
        out[key] = FuelType(
            key=key, name_cn=d["name"],
            reactivity=float(d["reactivity"]), self_rate=float(d["self_rate"]),
            function=d["function"], dep_func=d["dep_func"],
            heat=float(d["heat"]), yield_=float(d["yield"]),
            melting_point=float(d["melting_point"]), diffusion=float(d["diffusion"]),
            x_gen=float(d["x_gen"]), x_burn=float(d["x_burn"]),
            n_type=NType(d["n_type"]), r_type=NType(d["r_type"]),
            heat_coeff_start=float(d["heat_coeff_start"]),
            heat_coeff_length=float(d["heat_coeff_length"]),
        )
    return out


FUELS: dict[str, FuelType] = _build_fuels()
FUEL_KEYS: list[str] = list(FUELS.keys())


def fuel_by_key(key: str) -> FuelType:
    return FUELS[key]
