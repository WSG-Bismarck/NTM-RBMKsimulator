"""组件、控制组、燃料类型定义。

数据来源：HBM-NTM-.1.0.27_X5846.jar
- 组件方块清单：com/hbm/blocks/ModBlocks 中全部 rbmk_* 方块；中文名取自 assets/hbm/lang/zh_CN.lang
- 控制组 5 色：TileEntityRBMKControlManual$RBMKColor
- 燃料 34 种：ModItems 中 rbmk_fuel_* 注册，逐项精确提取（见 fuel_data.py）
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from rbmk.model.fuel_data import FUEL_DATA


class ComponentType(str, Enum):
    # ---- 反应堆核心柱子（22）----
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
    RBMK_AUTOLOADER = "rbmk_autoloader"
    RBMK_STEAM_INLET = "rbmk_steam_inlet"
    RBMK_STEAM_OUTLET = "rbmk_steam_outlet"
    RBMK_LOADER = "rbmk_loader"
    # ---- 控制 / 显示设备（11）----
    RBMK_CONSOLE = "rbmk_console"
    RBMK_CRANE_CONSOLE = "rbmk_crane_console"
    RBMK_DISPLAY = "rbmk_display"
    RBMK_DISPLAY_BLANK = "rbmk_display_blank"
    RBMK_GAUGE = "rbmk_gauge"
    RBMK_GRAPH = "rbmk_graph"
    RBMK_INDICATOR = "rbmk_indicator"
    RBMK_KEY_PAD = "rbmk_key_pad"
    RBMK_LEVER = "rbmk_lever"
    RBMK_NUMITRON = "rbmk_numitron"
    RBMK_TERMINAL = "rbmk_terminal"


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
    ComponentType.RBMK_AUTOLOADER: ("RBMK燃料自动装填机", "#7fbf7f"),
    ComponentType.RBMK_STEAM_INLET: ("RBMK ReaSim进水口", "#4f9de8"),
    ComponentType.RBMK_STEAM_OUTLET: ("RBMK ReaSim蒸汽出口", "#e08a4a"),
    ComponentType.RBMK_LOADER: ("RBMK反应堆蒸汽导出器", "#6ab0d0"),
    ComponentType.RBMK_CONSOLE: ("RBMK石墨式反应堆控制台", "#c0c8d0"),
    ComponentType.RBMK_CRANE_CONSOLE: ("RBMK起重机控制台", "#b0b8c0"),
    ComponentType.RBMK_DISPLAY: ("RBMK显示面板", "#4fc3e8"),
    ComponentType.RBMK_DISPLAY_BLANK: ("无线红石信号空白面板", "#607080"),
    ComponentType.RBMK_GAUGE: ("无线红石信号流量控制器面板", "#607080"),
    ComponentType.RBMK_GRAPH: ("无线红石信号图表面板", "#607080"),
    ComponentType.RBMK_INDICATOR: ("无线红石信号指示灯", "#607080"),
    ComponentType.RBMK_KEY_PAD: ("无线红石信号按钮面板", "#607080"),
    ComponentType.RBMK_LEVER: ("无线红石信号拉杆", "#607080"),
    ComponentType.RBMK_NUMITRON: ("无线红石信号数字显示器", "#607080"),
    ComponentType.RBMK_TERMINAL: ("无线红石信号发信终端", "#607080"),
}

# 网格内的简写标记
COMPONENT_SHORT: dict[ComponentType, str] = {
    ComponentType.RBMK_ROD: "燃",
    ComponentType.RBMK_ROD_MOD: "燃M",
    ComponentType.RBMK_ROD_REASIM: "燃R",
    ComponentType.RBMK_ROD_REASIM_MOD: "燃M",
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
    ComponentType.RBMK_AUTOLOADER: "装",
    ComponentType.RBMK_STEAM_INLET: "进",
    ComponentType.RBMK_STEAM_OUTLET: "出",
    ComponentType.RBMK_LOADER: "导",
    ComponentType.RBMK_CONSOLE: "台",
    ComponentType.RBMK_CRANE_CONSOLE: "吊",
    ComponentType.RBMK_DISPLAY: "显",
    ComponentType.RBMK_DISPLAY_BLANK: "空",
    ComponentType.RBMK_GAUGE: "流",
    ComponentType.RBMK_GRAPH: "图",
    ComponentType.RBMK_INDICATOR: "灯",
    ComponentType.RBMK_KEY_PAD: "键",
    ComponentType.RBMK_LEVER: "杆",
    ComponentType.RBMK_NUMITRON: "数",
    ComponentType.RBMK_TERMINAL: "终",
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
    AUTOLOADER = "autoloader"
    STEAM = "steam"
    LOADER = "loader"
    AUX = "aux"


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
    ComponentType.RBMK_AUTOLOADER: Behavior.AUTOLOADER,
    ComponentType.RBMK_STEAM_INLET: Behavior.STEAM,
    ComponentType.RBMK_STEAM_OUTLET: Behavior.STEAM,
    ComponentType.RBMK_LOADER: Behavior.LOADER,
    ComponentType.RBMK_CONSOLE: Behavior.AUX,
    ComponentType.RBMK_CRANE_CONSOLE: Behavior.AUX,
    ComponentType.RBMK_DISPLAY: Behavior.AUX,
    ComponentType.RBMK_DISPLAY_BLANK: Behavior.AUX,
    ComponentType.RBMK_GAUGE: Behavior.AUX,
    ComponentType.RBMK_GRAPH: Behavior.AUX,
    ComponentType.RBMK_INDICATOR: Behavior.AUX,
    ComponentType.RBMK_KEY_PAD: Behavior.AUX,
    ComponentType.RBMK_LEVER: Behavior.AUX,
    ComponentType.RBMK_NUMITRON: Behavior.AUX,
    ComponentType.RBMK_TERMINAL: Behavior.AUX,
}

CORE_COMPONENTS: list[ComponentType] = [c for c in ComponentType if COMPONENT_BEHAVIOR[c] != Behavior.AUX]
AUX_COMPONENTS: list[ComponentType] = [c for c in ComponentType if COMPONENT_BEHAVIOR[c] == Behavior.AUX]

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
