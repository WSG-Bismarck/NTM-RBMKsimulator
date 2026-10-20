"""阶段 5 风险判定测试：正常/稳定/有限倒计时/熔毁。"""
from rbmk.model.components import ComponentType
from rbmk.model.reactor import ReactorModel
from rbmk.sim.engine import SimulationEngine
from rbmk.sim.risk import assess, format_duration


def _model(coolant=50.0):
    m = ReactorModel(rows=6, cols=6)
    m.coolant_flow = coolant
    m.place(2, 2, ComponentType.RBMK_ROD, fuel="rbmk_fuel_heu235")
    return m


def test_stable_reactor_has_no_countdown():
    e = SimulationEngine(_model(coolant=100.0))
    for _ in range(20):
        e.advance(60)
    r = assess(e)
    assert r.level in ("normal", "warning")
    assert r.time_to_meltdown is None
    assert "稳定" in format_duration(r.time_to_meltdown)


def test_heating_reactor_has_finite_countdown():
    e = SimulationEngine(_model(coolant=0.0))
    e.advance(20)  # 升温中
    r = assess(e)
    assert r.time_to_meltdown is not None
    assert r.time_to_meltdown > 0


def test_meltdown_reports_zero():
    e = SimulationEngine(_model(coolant=0.0))
    for _ in range(30):
        e.advance(60)
        if e.state.melted:
            break
    r = assess(e)
    assert r.level == "meltdown"
    assert r.time_to_meltdown == 0.0


def test_format_duration():
    assert format_duration(None) == "稳定（无熔毁风险）"
    assert format_duration(0) == "0:00:00"
    assert format_duration(3661) == "01:01:01"
