"""阶段 4 引擎测试：功率/温度/生产链/燃料消耗/熔毁。"""
from rbmk.model.components import ComponentType, ControlGroup, FUELS
from rbmk.model.reactor import ReactorModel
from rbmk.sim.engine import SimulationEngine, reactivity_function


def _model(coolant=50.0, insertion=100.0, with_control=False, with_mod=False,
           with_abs=False, with_boiler=False, fuel="rbmk_fuel_heu235"):
    m = ReactorModel(rows=6, cols=6)
    m.coolant_flow = coolant
    m.global_insertion = insertion
    m.place(2, 2, ComponentType.FUEL, fuel=fuel)
    if with_control:
        m.place(2, 3, ComponentType.CONTROL, group=ControlGroup.RED)
    if with_mod:
        m.place(3, 2, ComponentType.MODERATOR)
    if with_abs:
        m.place(3, 3, ComponentType.ABSORBER)
    if with_boiler:
        m.place(1, 1, ComponentType.BOILER)
    return m


def test_no_fuel_zero_power():
    e = SimulationEngine(ReactorModel(rows=6, cols=6))
    e.advance(10)
    assert e.state.power == 0.0
    assert e.state.electricity == 0.0
    assert e.state.status == "normal"


def test_fuel_produces_power():
    e = SimulationEngine(_model())
    e.advance(10)
    assert e.state.power > 0
    assert e.state.flux > 0


def test_control_rod_reduces_power():
    rods_out = SimulationEngine(_model(with_control=True, insertion=0.0))
    rods_in = SimulationEngine(_model(with_control=True, insertion=100.0))
    rods_out.advance(10)
    rods_in.advance(10)
    assert rods_in.state.power < rods_out.state.power


def test_moderator_increases_power():
    base = SimulationEngine(_model())
    modded = SimulationEngine(_model(with_mod=True))
    base.advance(10)
    modded.advance(10)
    assert modded.state.power > base.state.power


def test_absorber_reduces_power():
    base = SimulationEngine(_model())
    absorbed = SimulationEngine(_model(with_abs=True))
    base.advance(10)
    absorbed.advance(10)
    assert absorbed.state.power < base.state.power


def test_coolant_lowers_temperature():
    hot = SimulationEngine(_model(coolant=10.0))
    cool = SimulationEngine(_model(coolant=100.0))
    for _ in range(20):
        hot.advance(60)
        cool.advance(60)
    assert cool.state.temperature < hot.state.temperature


def test_fuel_burns_down_over_time():
    e = SimulationEngine(_model())
    e.advance(100)
    first = e.state.fuel_remaining
    e.advance(500)
    assert e.state.fuel_remaining < first <= 100.0


def test_boiler_required_for_electricity():
    no_boiler = SimulationEngine(_model())
    with_boiler = SimulationEngine(_model(with_boiler=True))
    no_boiler.advance(10)
    with_boiler.advance(10)
    assert no_boiler.state.electricity == 0.0
    assert with_boiler.state.electricity > 0.0


def test_total_energy_accumulates():
    e = SimulationEngine(_model(with_boiler=True))
    e.advance(60)
    assert e.state.total_energy > 0.0


def test_meltdown_without_coolant():
    e = SimulationEngine(_model(coolant=0.0))
    for _ in range(30):
        e.advance(60)
        if e.state.melted:
            break
    assert e.state.melted
    assert e.state.status == "meltdown"


def test_reactivity_function_square_root_exact():
    """HEU235: SQUARE_ROOT, reactivity=50, GENTLE_SLOPE(e=1)=1 -> sqrt(100)*50/10=50"""
    ft = FUELS["rbmk_fuel_heu235"]
    assert abs(reactivity_function(ft, 100.0, 1.0) - 50.0) < 1e-9


def test_reactivity_function_linear_exact():
    """HEP239: LINEAR, reactivity=30 -> 100/100*30=30"""
    ft = FUELS["rbmk_fuel_hep239"]
    assert abs(reactivity_function(ft, 100.0, 1.0) - 30.0) < 1e-9


def test_reactivity_function_passive_exact():
    """PO210BE: PASSIVE, self_rate=50 -> 50*enrichment"""
    ft = FUELS["rbmk_fuel_po210be"]
    assert abs(reactivity_function(ft, 100.0, 0.5) - 25.0) < 1e-9
