"""阶段 5 风险判定测试：稳定/升温倒计时/熔毁。"""
from rbmk.model.components import ComponentType
from rbmk.model.reactor import ReactorModel
from rbmk.sim.engine import SimulationEngine
from rbmk.sim.risk import assess, format_duration

ROD = ComponentType.RBMK_ROD
BOIL = ComponentType.RBMK_BOILER


def _model(with_boiler=False):
    m = ReactorModel(7, 7)
    m.place(3, 3, ROD, fuel="rbmk_fuel_po210be")
    m.place(3, 4, ROD, fuel="rbmk_fuel_heu235")
    if with_boiler:
        for r, c in [(2, 3), (4, 3), (2, 4), (4, 4)]:
            m.place(r, c, BOIL)
    return m


def test_stable_reactor_has_no_countdown():
    e = SimulationEngine(_model(with_boiler=True))
    for _ in range(60):
        e.advance(1.0)
    r = assess(e)
    assert r.time_to_meltdown is None


def test_heating_reactor_has_finite_countdown():
    e = SimulationEngine(_model())
    e.advance(2.0)
    r = assess(e)
    assert r.time_to_meltdown is not None
    assert r.time_to_meltdown > 0


def test_meltdown_reports_zero():
    e = SimulationEngine(_model())
    for _ in range(100):
        e.advance(1.0)
        if e.state.melted:
            break
    r = assess(e)
    assert r.level == "meltdown"
    assert r.time_to_meltdown == 0.0


def test_format_duration():
    assert format_duration(None) == "稳定（无熔毁风险）"
    assert format_duration(0) == "0:00:00"
    assert format_duration(3661) == "01:01:01"
