"""阶段 2/3 数据模型测试：组件清单、燃料清单、网格操作、控制棒优先级。"""
import pytest

from rbmk.model.components import (
    AUX_COMPONENTS,
    COMPONENT_INFO,
    CONTROL_GROUP_COLORS,
    CORE_COMPONENTS,
    FUELS,
    ComponentType,
    ControlGroup,
)
from rbmk.model.reactor import ReactorModel


def test_component_count_is_18():
    assert len(ComponentType) == 18
    assert len(COMPONENT_INFO) == 18


def test_removed_components_absent():
    names = {c.value for c in ComponentType}
    removed = [
        "rbmk_autoloader", "rbmk_steam_inlet", "rbmk_steam_outlet", "rbmk_loader",
        "rbmk_console", "rbmk_crane_console", "rbmk_display", "rbmk_display_blank",
        "rbmk_gauge", "rbmk_graph", "rbmk_indicator", "rbmk_key_pad", "rbmk_lever",
        "rbmk_numitron", "rbmk_terminal",
    ]
    for gone in removed:
        assert gone not in names


def test_component_groups_and_names():
    assert len(CORE_COMPONENTS) == 18
    assert len(AUX_COMPONENTS) == 0
    # 名称必须来自 zh_CN.lang（抽查）
    assert COMPONENT_INFO[ComponentType.RBMK_ROD][0] == "RBMK反应堆燃料通道"
    assert COMPONENT_INFO[ComponentType.RBMK_CONTROL][0] == "RBMK反应堆控制棒"
    assert COMPONENT_INFO[ComponentType.RBMK_ABSORBER][0] == "RBMK反应堆硼中子吸收器"
    assert COMPONENT_INFO[ComponentType.RBMK_REFLECTOR][0] == "RBMK反应堆碳化钨中子反射器"


def test_control_groups_are_5():
    assert len(ControlGroup) == 5
    assert set(CONTROL_GROUP_COLORS) == set(ControlGroup)


def test_fuel_list_is_34():
    assert len(FUELS) == 34
    assert "rbmk_fuel_ueu" in FUELS
    assert "rbmk_fuel_empty" in FUELS
    assert FUELS["rbmk_fuel_empty"].reactivity == 0.0
    # HEU 反应性应高于 LEU（均为 jar 精确值）
    assert FUELS["rbmk_fuel_heu235"].reactivity > FUELS["rbmk_fuel_ueu"].reactivity
    # 抽查反编译得到的精确值（ModItems / ItemRBMKRod）
    assert FUELS["rbmk_fuel_ueu"].reactivity == 15.0
    assert FUELS["rbmk_fuel_heu235"].reactivity == 50.0
    assert FUELS["rbmk_fuel_heu235"].function == "SQUARE_ROOT"
    assert FUELS["rbmk_fuel_uzh"].melting_point == 1845.0
    assert FUELS["rbmk_fuel_uzh"].heat_coeff_start == 1000.0
    assert FUELS["rbmk_fuel_lea"].self_rate == 10.0


def test_place_erase_counts():
    m = ReactorModel(rows=5, cols=5)
    m.place(1, 1, ComponentType.RBMK_ROD, fuel="rbmk_fuel_heu235")
    m.place(1, 2, ComponentType.RBMK_MODERATOR)
    m.place(2, 2, ComponentType.RBMK_CONTROL, group=ControlGroup.RED)
    counts = m.counts()
    assert counts[ComponentType.RBMK_ROD] == 1
    assert counts[ComponentType.RBMK_MODERATOR] == 1
    assert counts[ComponentType.RBMK_CONTROL] == 1
    assert m.fuel_count() == 1
    m.erase(1, 1)
    assert m.cell_at(1, 1) is None
    assert m.counts()[ComponentType.RBMK_ROD] == 0


def test_control_insertion_priority():
    m = ReactorModel(rows=3, cols=3)
    m.global_insertion = 40.0
    cell = m.place(0, 0, ComponentType.RBMK_CONTROL, group=ControlGroup.RED)
    # 默认用全局
    assert m.effective_insertion(cell) == 40.0
    # 分组覆盖
    m.group_insertion["RED"] = 75.0
    assert m.effective_insertion(cell) == 75.0
    # 单根覆盖优先于分组
    cell.insertion = 10.0
    assert m.effective_insertion(cell) == 10.0
    # 非控制棒返回 0
    fuel = m.place(1, 1, ComponentType.RBMK_ROD, fuel="rbmk_fuel_ueu")
    assert m.effective_insertion(fuel) == 0.0


def test_out_of_bounds_raises():
    m = ReactorModel(rows=3, cols=3)
    with pytest.raises(IndexError):
        m.place(5, 5, ComponentType.RBMK_ROD, fuel="rbmk_fuel_ueu")


def test_fuel_names_match_in_game_lang():
    """燃料中文名必须与 zh_CN.lang 的标准译名一致。"""
    from rbmk.model.components import FUELS
    assert FUELS["rbmk_fuel_heu235"].name_cn == "HEU-235 RBMK反应堆高浓缩度铀-235燃料棒"
    assert FUELS["rbmk_fuel_ueu"].name_cn == "NU RBMK反应堆未浓缩铀燃料棒"
    assert FUELS["rbmk_fuel_hep239"].name_cn == "HEP-239 RBMK反应堆高浓缩度钚-239燃料棒"
    assert FUELS["rbmk_fuel_balefire"].name_cn == "RBMK反应堆野火燃料棒"
    assert FUELS["rbmk_fuel_po210be"].name_cn == "钋210-铍 RBMK反应堆中子源"
    # DRX 在语言文件里带 §c / §r 颜色码，显示时必须去掉
    assert FUELS["rbmk_fuel_drx"].name_cn == "RBMK反应堆F迪伽马粒子燃料棒"
    for ft in FUELS.values():
        assert "§" not in ft.name_cn
        if ft.key != "rbmk_fuel_test":      # 测试燃料在语言文件里没有条目
            assert "RBMK" in ft.name_cn


def test_fuel_diffusion_values_from_jar():
    """扩散值来自 ItemRBMKRod.setDiffusion / 默认 0.02。"""
    from rbmk.model.components import FUELS
    assert FUELS["rbmk_fuel_heu235"].diffusion == 0.02      # 默认值
    assert FUELS["rbmk_fuel_uzh"].diffusion == 0.1          # 铀氢锆
    assert FUELS["rbmk_fuel_ra226be"].diffusion == 0.5      # 镭226-铍中子源
    assert FUELS["rbmk_fuel_po210be"].diffusion == 0.05     # 钋210-铍中子源
    assert FUELS["rbmk_fuel_empty"].diffusion == 0.0


def test_control_rod_defaults_to_vacant_group():
    """新放置的控制棒默认控制组为「空置」。"""
    from rbmk.model.components import ComponentType
    m = ReactorModel(3, 3)
    rod = m.place(1, 1, ComponentType.RBMK_CONTROL)
    assert rod.group is None
    m.group_insertion["RED"] = 0.0
    assert m.effective_insertion(rod) == m.global_insertion


def test_turbine_capacity_and_count():
    """单台汽轮机输出上限与所需台数：工业按 750k 罐 20%，利维坦 512k 罐且受 1 亿上限与 85%。"""
    from rbmk.model.components import (
        STEAM_TYPES, turbine_capacity_he, turbines_needed,
        TURBINE_INDUSTRIAL, TURBINE_LEVIATHAN,
    )

    steam = STEAM_TYPES["STEAM"]           # 2 HE/mB
    assert abs(turbine_capacity_he(TURBINE_INDUSTRIAL, steam.he_per_mb) - 750_000 * 0.2 * 2) < 1e-6
    assert abs(turbine_capacity_he(TURBINE_LEVIATHAN, steam.he_per_mb) - 512_000 * 0.2 * 2 * 0.85) < 1e-6

    ultra = STEAM_TYPES["ULTRAHOTSTEAM"]   # 2500 HE/mB
    # 利维坦受 maxPower = 100,000,000 限制，再乘 0.85
    assert abs(turbine_capacity_he(TURBINE_LEVIATHAN, ultra.he_per_mb) - 85_000_000) < 1e-6
    # 工业不设常量上限：750k × 20% × 2500
    assert abs(turbine_capacity_he(TURBINE_INDUSTRIAL, ultra.he_per_mb) - 375_000_000) < 1e-6

    assert turbines_needed(TURBINE_INDUSTRIAL, 0.0, steam.he_per_mb) == 0
    assert turbines_needed(TURBINE_INDUSTRIAL, 300_000, steam.he_per_mb) == 1
    assert turbines_needed(TURBINE_INDUSTRIAL, 300_001, steam.he_per_mb) == 2
    assert turbines_needed(TURBINE_LEVIATHAN, 300_000, steam.he_per_mb) == 2


def test_turbine_choice_persists():
    """汽轮机选择写入存档并可还原。"""
    m = ReactorModel(4, 4)
    m.set_turbine("SUPERHOTSTEAM", "LEVIATHAN")
    d = m.to_dict()
    assert d["turbines"]["SUPERHOTSTEAM"] == "LEVIATHAN"
    m2 = ReactorModel.from_dict(d)
    assert m2.turbine_of("SUPERHOTSTEAM") == "LEVIATHAN"
    assert m2.turbine_of("STEAM") == "INDUSTRIAL"
