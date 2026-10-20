"""阶段 4 引擎测试：方向性中子、慢化/反射/吸收/控制、热扩散、锅炉、熔毁。"""
from rbmk.model.components import ComponentType, FUELS
from rbmk.model.reactor import ReactorModel
from rbmk.sim.engine import SimulationEngine, reactivity_function

ROD = ComponentType.RBMK_ROD
CTRL = ComponentType.RBMK_CONTROL
MOD = ComponentType.RBMK_MODERATOR
REFL = ComponentType.RBMK_REFLECTOR
ABS = ComponentType.RBMK_ABSORBER
BOIL = ComponentType.RBMK_BOILER
SRC = "rbmk_fuel_po210be"
HEU = "rbmk_fuel_heu235"


# ---------- 精确燃料公式 ----------
def test_reactivity_function_square_root_exact():
    ft = FUELS[HEU]
    assert abs(reactivity_function(ft, 100.0, 1.0) - 50.0) < 1e-9


def test_reactivity_function_linear_exact():
    ft = FUELS["rbmk_fuel_hep239"]
    assert abs(reactivity_function(ft, 100.0, 1.0) - 30.0) < 1e-9


def test_reactivity_function_passive_exact():
    ft = FUELS[SRC]
    assert abs(reactivity_function(ft, 100.0, 0.5) - 25.0) < 1e-9


# ---------- 中子射线的组件交互 ----------
def _cast_model(middle=None, insertion=0.0):
    m = ReactorModel(7, 7)
    m.global_insertion = insertion
    origin = m.place(3, 1, ROD, fuel=HEU)
    target = m.place(3, 3, ROD, fuel=HEU)
    if middle is not None:
        m.place(3, 2, middle)
    e = SimulationEngine(m)
    return m, e, origin, target


def test_cast_fuel_receives_flux():
    m, e, origin, target = _cast_model()
    e._cast(3, 1, 0, 1, 50.0, 0.0, origin)
    assert target.flux_q == 50.0


def test_cast_range_limit_is_5():
    m = ReactorModel(10, 10)
    origin = m.place(3, 3, ROD, fuel=HEU)
    far = m.place(3, 9, ROD, fuel=HEU)  # 6 格，超出射程
    e = SimulationEngine(m)
    e._cast(3, 3, 0, 1, 50.0, 0.0, origin)
    assert far.flux_q == 0.0


def test_cast_moderator_fully_slows_fast_neutrons():
    m, e, origin, target = _cast_model(middle=MOD)
    e._cast(3, 1, 0, 1, 100.0, 1.0, origin)
    assert abs(target.flux_ratio - 0.0) < 1e-9


def test_cast_absorber_blocks_and_heats():
    m, e, origin, target = _cast_model(middle=ABS)
    absorber = m.cell_at(3, 2)
    e._cast(3, 1, 0, 1, 100.0, 0.0, origin)
    assert target.flux_q == 0.0
    assert abs(absorber.heat - 5.0) < 1e-9


def test_cast_reflector_reflects_back_to_origin():
    m, e, origin, target = _cast_model(middle=REFL)
    e._cast(3, 1, 0, 1, 100.0, 0.0, origin)
    assert target.flux_q == 0.0
    assert abs(origin.flux_q - 100.0) < 1e-9


def test_cast_control_blocks_when_fully_inserted():
    m, e, origin, target = _cast_model(middle=CTRL, insertion=100.0)
    e._cast(3, 1, 0, 1, 100.0, 0.0, origin)
    assert target.flux_q == 0.0


def test_cast_control_attenuates_when_partial():
    m, e, origin, target = _cast_model(middle=CTRL, insertion=50.0)
    e._cast(3, 1, 0, 1, 100.0, 0.0, origin)
    assert abs(target.flux_q - 50.0) < 1e-9


# ---------- 热 ----------
def test_heat_diffuses_to_colder_neighbor():
    m = ReactorModel(5, 5)
    hot = m.place(2, 2, ROD, fuel=HEU)
    cold = m.place(2, 3, ROD, fuel=HEU)
    e = SimulationEngine(m)
    hot.temp = 200.0
    cold.temp = 20.0
    e._heat_tick()
    assert hot.temp < 200.0
    assert cold.temp > 20.0


def test_passive_cooling_lowers_isolated_column():
    m = ReactorModel(5, 5)
    c = m.place(2, 2, ROD, fuel=HEU)
    e = SimulationEngine(m)
    c.temp = 500.0
    e._heat_tick()
    assert c.temp < 500.0


def test_boiler_turns_heat_into_steam():
    m = ReactorModel(5, 5)
    b = m.place(2, 2, BOIL)
    e = SimulationEngine(m)
    b.temp = 500.0
    e._heat_tick()
    assert e._steam_tick > 0
    assert b.temp < 500.0


# ---------- 完整运行 ----------
def test_no_source_no_power():
    m = ReactorModel(5, 5)
    m.place(2, 2, ROD, fuel=HEU)
    e = SimulationEngine(m)
    e.advance(5)
    assert e.state.power == 0.0
    assert e.state.flux == 0.0


def test_source_drives_chain_reaction():
    m = ReactorModel(5, 5)
    m.place(2, 2, ROD, fuel=SRC)
    m.place(2, 3, ROD, fuel=HEU)
    e = SimulationEngine(m)
    e.advance(5)
    assert e.state.power > 0
    assert e.state.flux > 0


def test_fuel_burns_down_over_time():
    m = ReactorModel(5, 5)
    m.place(2, 2, ROD, fuel=SRC)
    rod = m.place(2, 3, ROD, fuel=HEU)
    e = SimulationEngine(m)
    e.advance(10)
    first = rod.burnup
    e.advance(100)
    assert rod.burnup > first


def test_meltdown_without_cooling():
    m = ReactorModel(5, 5)
    m.place(2, 2, ROD, fuel=SRC)
    m.place(2, 3, ROD, fuel=HEU)
    e = SimulationEngine(m)
    for _ in range(100):
        e.advance(1.0)
        if e.state.melted:
            break
    assert e.state.melted
    assert e.state.status == "meltdown"


def test_boilers_prevent_meltdown():
    m = ReactorModel(7, 7)
    m.place(3, 3, ROD, fuel=SRC)
    m.place(3, 4, ROD, fuel=HEU)
    for r, c in [(2, 3), (4, 3), (2, 4), (4, 4)]:
        m.place(r, c, BOIL)
    e = SimulationEngine(m)
    e.advance(60)
    assert not e.state.melted


# ---------- 自燃燃料 ----------
def test_all_self_igniting_fuels_emit_without_source():
    self_igniting = [k for k, f in FUELS.items() if f.is_self_igniting]
    assert len(self_igniting) == 10
    for key in self_igniting:
        m = ReactorModel(5, 5)
        m.place(2, 2, ROD, fuel=key)
        e = SimulationEngine(m)
        e.advance(1.0)
        assert e.state.power > 0, key
        assert e.state.flux > 0, key


def test_non_self_igniting_fuel_needs_source():
    m = ReactorModel(5, 5)
    m.place(2, 2, ROD, fuel=HEU)
    e = SimulationEngine(m)
    e.advance(2.0)
    assert e.state.power == 0.0
    assert e.state.flux == 0.0


def test_self_igniting_emission_follows_burn_function():
    """LEA：SQUARE_ROOT，self=10，reac=60 → sqrt(10)*60/10 = 18.97"""
    m = ReactorModel(5, 5)
    rod = m.place(2, 2, ROD, fuel="rbmk_fuel_lea")
    e = SimulationEngine(m)
    e.advance(0.05)  # 恰好 1 tick
    ft = FUELS["rbmk_fuel_lea"]
    expected = reactivity_function(ft, ft.self_rate, 1.0)
    assert abs(rod.flux - expected) < 1e-6


def test_rod_placed_after_engine_creation_starts():
    """回归：界面是“先建引擎、后放柱子”，后放的燃料棒也必须参与反应。"""
    m = ReactorModel(5, 5)
    e = SimulationEngine(m)          # 空模型时就创建引擎
    m.place(2, 2, ROD, fuel=SRC)     # 之后再放自燃燃料棒
    e.advance(1.0)
    assert e.state.power > 0
    assert e.state.flux > 0


def test_melt_threshold_is_mod_max_heat():
    m = ReactorModel(5, 5)
    m.place(2, 2, ROD, fuel=HEU)
    e = SimulationEngine(m)
    assert e.state.melt_temp == 1500.0


def test_fuel_melts_above_1500_even_if_fuel_melting_point_higher():
    """模组用 maxHeat()=1500 判定，不看燃料熔点（HEU 熔点 2865）。"""
    m = ReactorModel(5, 5)
    rod = m.place(2, 2, ROD, fuel=HEU)
    e = SimulationEngine(m)
    rod.temp = 1600.0
    e._heat_tick()
    e._update_state()
    assert e.state.melted
    assert e.state.status == "meltdown"


def test_fuel_below_1500_does_not_melt():
    m = ReactorModel(5, 5)
    rod = m.place(2, 2, ROD, fuel=HEU)
    e = SimulationEngine(m)
    rod.temp = 1490.0
    e._heat_tick()
    e._update_state()
    assert not e.state.melted


def test_any_column_above_1500_melts():
    """条件1：任一组件（含非燃料柱）柱温 > 1500 即熔毁。"""
    m = ReactorModel(5, 5)
    cell = m.place(2, 2, MOD)
    e = SimulationEngine(m)
    cell.temp = 2000.0
    e._heat_tick()
    e._update_state()
    assert e.state.melted


def test_fuel_hull_above_melting_point_melts():
    """条件2：柱温不高，但燃料壳温超过自身熔点。"""
    m = ReactorModel(5, 5)
    rod = m.place(2, 2, ROD, fuel=HEU)   # 熔点 2865
    e = SimulationEngine(m)
    rod.temp = 300.0
    rod.hull_heat = 2900.0
    e._heat_tick()
    e._update_state()
    assert e.state.melted


def test_fuel_hull_below_melting_point_does_not_melt():
    m = ReactorModel(5, 5)
    rod = m.place(2, 2, ROD, fuel=HEU)
    e = SimulationEngine(m)
    rod.temp = 300.0
    rod.hull_heat = 2800.0
    e._heat_tick()
    e._update_state()
    assert not e.state.melted


# ---------- 锅炉蒸汽类型 ----------
def test_boiler_steam_type_threshold():
    m = ReactorModel(5, 5)
    b = m.place(2, 2, BOIL)
    e = SimulationEngine(m)
    b.temp = 400.0
    e._heat_tick()
    assert b.steam_rate > 0          # 蒸汽阈值 100
    b.temp = 400.0
    b.steam_type = "SUPERHOTSTEAM"   # 阈值 450
    e._heat_tick()
    assert b.steam_rate == 0.0


def test_boiler_steam_formula_exact():
    m = ReactorModel(5, 5)
    b = m.place(2, 2, BOIL)
    e = SimulationEngine(m)
    b.temp = 502.5                   # 被动冷却 2.5 后为 500
    e._heat_tick()
    # heatProvided=400 → 用水 4000 → 蒸汽 4000*100/1
    assert abs(b.steam_rate - 400000.0) < 1e-6


def test_boiler_steam_factor_ratio():
    m = ReactorModel(5, 5)
    b = m.place(2, 2, BOIL)
    e = SimulationEngine(m)
    b.temp = 502.5                   # 冷却后 500，蒸汽 heatProvided=400
    e._heat_tick()
    s1 = b.steam_rate
    b.temp = 702.5                   # 冷却后 700，热蒸汽 heatProvided=400
    b.steam_type = "HOTSTEAM"
    e._heat_tick()
    s10 = b.steam_rate
    assert s1 > 0 and s10 > 0
    assert abs(s1 / s10 - 10.0) < 1e-6
