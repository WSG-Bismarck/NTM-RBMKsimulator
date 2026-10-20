"""阶段 2/3 数据模型测试：组件清单、燃料清单、网格操作、控制棒优先级。"""
import pytest

from rbmk.model.components import (
    COMPONENT_INFO,
    CONTROL_GROUP_COLORS,
    FUELS,
    ComponentType,
    ControlGroup,
)
from rbmk.model.reactor import ReactorModel


def test_component_count_is_14():
    assert len(ComponentType) == 14
    assert len(COMPONENT_INFO) == 14


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
    m.place(1, 1, ComponentType.FUEL, fuel="rbmk_fuel_heu235")
    m.place(1, 2, ComponentType.MODERATOR)
    m.place(2, 2, ComponentType.CONTROL, group=ControlGroup.RED)
    counts = m.counts()
    assert counts[ComponentType.FUEL] == 1
    assert counts[ComponentType.MODERATOR] == 1
    assert counts[ComponentType.CONTROL] == 1
    assert m.fuel_count() == 1
    m.erase(1, 1)
    assert m.cell_at(1, 1) is None
    assert m.counts()[ComponentType.FUEL] == 0


def test_control_insertion_priority():
    m = ReactorModel(rows=3, cols=3)
    m.global_insertion = 40.0
    cell = m.place(0, 0, ComponentType.CONTROL, group=ControlGroup.RED)
    # 默认用全局
    assert m.effective_insertion(cell) == 40.0
    # 分组覆盖
    m.group_insertion["RED"] = 75.0
    assert m.effective_insertion(cell) == 75.0
    # 单根覆盖优先于分组
    cell.insertion = 10.0
    assert m.effective_insertion(cell) == 10.0
    # 非控制棒返回 0
    fuel = m.place(1, 1, ComponentType.FUEL, fuel="rbmk_fuel_ueu")
    assert m.effective_insertion(fuel) == 0.0


def test_out_of_bounds_raises():
    m = ReactorModel(rows=3, cols=3)
    with pytest.raises(IndexError):
        m.place(5, 5, ComponentType.FUEL, fuel="rbmk_fuel_ueu")
