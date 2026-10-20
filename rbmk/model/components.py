"""组件、控制组、燃料类型定义。

清单来源：HBM-NTM-.1.0.27_X5846.jar（见 spec/rbmk-mechanics.md）
说明：燃料逐项数值为 v1 建模值（命名层级 + 家族倍数），尚未逐项对齐 jar 字节码；
      清单本身（组件/燃料/分组/参数键）100% 来自 jar。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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


# 枚举值 -> (中文名, 界面颜色)
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
    tier: str
    family: str
    reactivity: float
    heat: float
    yield_: float
    melting_point: float
    diffusion: float
    x_gen: float
    x_burn: float
    n_type: NType = NType.SLOW
    r_type: RBMKType = RBMKType.ROD

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name_cn": self.name_cn,
            "tier": self.tier,
            "family": self.family,
            "reactivity": self.reactivity,
            "heat": self.heat,
            "yield": self.yield_,
            "melting_point": self.melting_point,
            "diffusion": self.diffusion,
            "x_gen": self.x_gen,
            "x_burn": self.x_burn,
            "n_type": self.n_type.value,
            "r_type": self.r_type.value,
        }


_TIER = {
    "LE": (0.35, 0.90, 0.75),
    "ME": (0.55, 1.30, 1.00),
    "HE": (0.85, 2.00, 1.40),
    "SP": (1.20, 3.00, 2.00),
    "NS": (0.08, 0.15, 0.10),
}
_FAM = {"U": 1.0, "Pu": 1.12, "Am": 1.18, "Np": 1.08, "Th": 0.90, "Sr": 0.80, "Be": 1.0, "X": 1.0}
_MELT = {"U": 2800, "Pu": 2750, "Am": 2850, "Np": 2780, "Th": 3000, "Sr": 2600, "Be": 2000, "X": 3200}

# (key, 中文名, tier, family)
_FUEL_TABLE = [
    ("rbmk_fuel_empty", "空燃料棒", None, None),
    ("rbmk_fuel_ueu", "低浓缩铀", "LE", "U"),
    ("rbmk_fuel_meu", "中浓缩铀", "ME", "U"),
    ("rbmk_fuel_heu233", "高浓缩铀-233", "HE", "U"),
    ("rbmk_fuel_heu235", "高浓缩铀-235", "HE", "U"),
    ("rbmk_fuel_uzh", "铀锆燃料", "LE", "U"),
    ("rbmk_fuel_thmeu", "钍-中浓缩铀", "ME", "Th"),
    ("rbmk_fuel_lep", "低浓缩钚", "LE", "Pu"),
    ("rbmk_fuel_mep", "中浓缩钚", "ME", "Pu"),
    ("rbmk_fuel_hep239", "高浓缩钚-239", "HE", "Pu"),
    ("rbmk_fuel_hep241", "高浓缩钚-241", "HE", "Pu"),
    ("rbmk_fuel_lea", "低浓缩镅", "LE", "Am"),
    ("rbmk_fuel_mea", "中浓缩镅", "ME", "Am"),
    ("rbmk_fuel_hea241", "高浓缩镅-241", "HE", "Am"),
    ("rbmk_fuel_hea242", "高浓缩镅-242", "HE", "Am"),
    ("rbmk_fuel_heaus", "高浓缩镅(混合)", "HE", "Am"),
    ("rbmk_fuel_hen", "高浓缩镎", "HE", "Np"),
    ("rbmk_fuel_hep", "高浓缩钚(混合)", "HE", "Pu"),
    ("rbmk_fuel_hes", "高浓缩锶", "HE", "Sr"),
    ("rbmk_fuel_men", "中浓缩镎", "ME", "Np"),
    ("rbmk_fuel_mes", "中浓缩锶", "ME", "Sr"),
    ("rbmk_fuel_mox", "MOX燃料", "ME", "U"),
    ("rbmk_fuel_po210be", "钋-210/铍", "NS", "Be"),
    ("rbmk_fuel_pu238be", "钚-238/铍", "NS", "Be"),
    ("rbmk_fuel_ra226be", "镭-226/铍", "NS", "Be"),
    ("rbmk_fuel_leaus", "低浓缩镅(混合)", "LE", "Am"),
    ("rbmk_fuel_les", "低浓缩锶", "LE", "Sr"),
    ("rbmk_fuel_zfb_am_mix", "ZFB镅混合", "ME", "Am"),
    ("rbmk_fuel_zfb_bismuth", "ZFB铋", "LE", "X"),
    ("rbmk_fuel_zfb_pu241", "ZFB钚-241", "HE", "Pu"),
    ("rbmk_fuel_balefire", "妖火燃料", "SP", "X"),
    ("rbmk_fuel_balefire_gold", "妖火-金", "SP", "X"),
    ("rbmk_fuel_drx", "DRX燃料", "SP", "X"),
    ("rbmk_fuel_flashlead", "闪光铅", "LE", "X"),
    ("rbmk_fuel_test", "测试燃料", "ME", "U"),
]


def _build_fuels() -> dict[str, FuelType]:
    fuels: dict[str, FuelType] = {}
    for key, name, tier, fam in _FUEL_TABLE:
        if tier is None or fam is None:
            fuels[key] = FuelType(
                key=key, name_cn=name, tier="EMPTY", family="X",
                reactivity=0.0, heat=0.0, yield_=0.0, melting_point=0.0,
                diffusion=0.0, x_gen=0.0, x_burn=0.0,
            )
            continue
        r, h, y = _TIER[tier]
        fm = _FAM[fam]
        reac = round(r * fm, 4)
        heat = round(h * fm, 4)
        yld = round(y * fm, 4)
        melt = _MELT[fam] + (300 if tier == "SP" else 0)
        diff = round(0.3 + reac * 0.5, 4)
        xg = round(0.02 + reac * 0.02, 4)
        xb = round(0.015 + reac * 0.015, 4)
        nt = NType.FAST if tier == "NS" else NType.SLOW
        fuels[key] = FuelType(
            key=key, name_cn=name, tier=tier, family=fam,
            reactivity=reac, heat=heat, yield_=yld, melting_point=melt,
            diffusion=diff, x_gen=xg, x_burn=xb, n_type=nt,
        )
    return fuels


FUELS: dict[str, FuelType] = _build_fuels()
FUEL_KEYS: list[str] = list(FUELS.keys())


def fuel_by_key(key: str) -> FuelType:
    return FUELS[key]
