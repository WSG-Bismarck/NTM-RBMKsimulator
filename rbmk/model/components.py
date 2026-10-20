"""组件、控制组、燃料类型定义。

数据来源：HBM-NTM-.1.0.27_X5846.jar（CFR 0.152 反编译，见 spec/rbmk-mechanics.md）
- 组件 14 种：TileEntityRBMKConsole$ColumnType
- 控制组 5 色：TileEntityRBMKControlManual$RBMKColor
- 燃料 34 种：ModItems 中 rbmk_fuel_* 注册，逐项 setStats/setHeat/setMeltingPoint/... 精确提取
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from rbmk.model.fuel_data import FUEL_DATA


class ComponentType(str, Enum):
    BLANK = "BLANK"
    FUEL = "FUEL"
    FUEL_SIM = "FUEL_SIM"
    CONTROL = "CONTROL"
    CONTROL_AUTO = "CONTROL_AUTO"
    BOILER = "BOILER"
    MODERATOR = "MODERATOR"
    ABSORBER = "ABSORBER"
    REFLECTOR = "REFLECTOR"
    OUTGASSER = "OUTGASSER"
    BREEDER = "BREEDER"
    STORAGE = "STORAGE"
    COOLER = "COOLER"
    HEATEX = "HEATEX"


COMPONENT_INFO: dict[ComponentType, tuple[str, str]] = {
    ComponentType.BLANK: ("空柱", "#3a4149"),
    ComponentType.FUEL: ("燃料棒", "#e8a33d"),
    ComponentType.FUEL_SIM: ("模拟燃料棒", "#f0c060"),
    ComponentType.CONTROL: ("控制棒", "#c8d2db"),
    ComponentType.CONTROL_AUTO: ("自动控制棒", "#aab8c6"),
    ComponentType.BOILER: ("锅炉/蒸汽通道", "#5aa9e6"),
    ComponentType.MODERATOR: ("慢化剂(石墨)", "#6b6f76"),
    ComponentType.ABSORBER: ("中子吸收体", "#a78bd6"),
    ComponentType.REFLECTOR: ("中子反射体", "#aab4be"),
    ComponentType.OUTGASSER: ("除气器", "#c98a5a"),
    ComponentType.BREEDER: ("增殖柱", "#7fbf7f"),
    ComponentType.STORAGE: ("储存柱", "#8a8f98"),
    ComponentType.COOLER: ("冷却器", "#38b2a6"),
    ComponentType.HEATEX: ("热交换器", "#d08a4a"),
}


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
            "key": self.key,
            "name_cn": self.name_cn,
            "reactivity": self.reactivity,
            "self_rate": self.self_rate,
            "function": self.function,
            "dep_func": self.dep_func,
            "heat": self.heat,
            "yield": self.yield_,
            "melting_point": self.melting_point,
            "diffusion": self.diffusion,
            "x_gen": self.x_gen,
            "x_burn": self.x_burn,
            "n_type": self.n_type.value,
            "r_type": self.r_type.value,
            "heat_coeff_start": self.heat_coeff_start,
            "heat_coeff_length": self.heat_coeff_length,
        }


def _build_fuels() -> dict[str, FuelType]:
    out: dict[str, FuelType] = {}
    # 空燃料棒排最前，其余保持 jar 注册顺序
    order = ["rbmk_fuel_empty"] + [k for k in FUEL_DATA if k != "rbmk_fuel_empty"]
    for key in order:
        d = FUEL_DATA[key]
        out[key] = FuelType(
            key=key,
            name_cn=d["name"],
            reactivity=float(d["reactivity"]),
            self_rate=float(d["self_rate"]),
            function=d["function"],
            dep_func=d["dep_func"],
            heat=float(d["heat"]),
            yield_=float(d["yield"]),
            melting_point=float(d["melting_point"]),
            diffusion=float(d["diffusion"]),
            x_gen=float(d["x_gen"]),
            x_burn=float(d["x_burn"]),
            n_type=NType(d["n_type"]),
            r_type=NType(d["r_type"]),
            heat_coeff_start=float(d["heat_coeff_start"]),
            heat_coeff_length=float(d["heat_coeff_length"]),
        )
    return out


FUELS: dict[str, FuelType] = _build_fuels()
FUEL_KEYS: list[str] = list(FUELS.keys())


def fuel_by_key(key: str) -> FuelType:
    return FUELS[key]
