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
HEATER = ComponentType.RBMK_HEATER
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
    b.temp = 502.5                   # 模组顺序：锅炉先烧（用 502.5），之后才被动冷却
    e._heat_tick()
    # heatProvided=402.5 → 用水 4025 → 蒸汽 4025*100/1
    assert abs(b.steam_rate - 402500.0) < 1e-6


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


def test_avg_temperature_is_mean_and_avg_flux_is_per_rod():
    m = ReactorModel(5, 5)
    a = m.place(0, 0, MOD)
    b = m.place(4, 4, MOD)
    e = SimulationEngine(m)
    a.temp = 100.0
    b.temp = 300.0
    e._update_state()
    assert e.state.avg_temperature == 200.0
    assert e.state.avg_flux == 0.0

    m2 = ReactorModel(5, 5)
    m2.place(2, 2, ROD, fuel=SRC)
    e2 = SimulationEngine(m2)
    e2.advance(5.0)
    assert e2.state.avg_temperature > 20.0
    assert e2.state.avg_flux > 0.0


# ---------- 流体加热器 ----------
def test_heater_water_produces_steam():
    m = ReactorModel(5, 5)
    h = m.place(2, 2, HEATER)
    e = SimulationEngine(m)
    h.heater_fluid = "WATER"
    h.temp = 400.0
    e._heat_tick()
    # 产出被输出罐容量 16000 mB/tick 限制
    assert abs(h.heater_rate - 16000.0) < 1e-6
    # 热量产出 = 16000 × (200/100) × 0.5 = 16000 TU/tick
    assert abs(h.heater_heat - 16000.0) < 1e-6
    # 热移除 = 200*160/500*0.25 = 16
    assert abs(h.temp - (400.0 - 2.5 - 16.0)) < 1e-6


def test_heater_requires_heat_above_output_temperature():
    m = ReactorModel(5, 5)
    h = m.place(2, 2, HEATER)
    e = SimulationEngine(m)
    h.temp = 400.0
    h.heater_fluid = "BLOOD"                   # 血：产出温度 666
    e._heat_tick()
    assert h.heater_rate == 0.0

    h.temp = 900.0
    e._heat_tick()
    assert h.heater_rate > 0.0


def test_heater_oil_rate_and_heat_removal():
    m = ReactorModel(5, 5)
    h = m.place(2, 2, HEATER)
    e = SimulationEngine(m)
    h.temp = 500.0
    h.heater_fluid = "OIL"                     # 原油：1→1，heatReq 10，产出温度 350
    e._heat_tick()
    # 产出被输出罐容量限制；ops=16000 → 热移除 = 10*16000/2000 = 80
    assert abs(h.heater_rate - 16000.0) < 1e-6
    assert abs(h.heater_heat - 160000.0) < 1e-6
    assert abs(h.temp - 417.5) < 1e-6


def test_heater_default_fluid_is_coolant():
    m = ReactorModel(5, 5)
    h = m.place(2, 2, HEATER)
    assert h.heater_fluid == "COOLANT"


def test_heater_output_capped_at_tank_capacity():
    m = ReactorModel(5, 5)
    h = m.place(2, 2, HEATER)
    e = SimulationEngine(m)
    h.heater_fluid = "WATER"
    h.temp = 700.0
    e._heat_tick()
    assert abs(h.heater_rate - 16000.0) < 1e-6


def test_boiler_steam_capped_at_tank_capacity():
    m = ReactorModel(5, 5)
    b = m.place(2, 2, BOIL)
    e = SimulationEngine(m)
    b.temp = 2000.0
    e._heat_tick()
    assert abs(b.steam_rate - 1000000.0) < 1e-6


# ---------- 自带慢化的组件 ----------
def test_moderated_control_rod_slows_passing_stream():
    m = ReactorModel(1, 5)
    src = m.place(0, 0, ROD, fuel=HEU)
    ctrl = m.place(0, 1, ComponentType.RBMK_CONTROL_MOD)
    ctrl.insertion = 0.0          # 全提出，level=1
    tgt = m.place(0, 2, ROD, fuel=HEU)
    e = SimulationEngine(m)
    e._cast(0, 0, 0, 1, 100.0, 1.0, src)
    assert tgt.flux_q == 100.0
    assert tgt.flux_ratio == 0.0   # moderatorEfficiency=1 → 快中子占比清零


def test_plain_control_rod_does_not_slow_stream():
    m = ReactorModel(1, 5)
    src = m.place(0, 0, ROD, fuel=HEU)
    ctrl = m.place(0, 1, ComponentType.RBMK_CONTROL)
    ctrl.insertion = 0.0
    tgt = m.place(0, 2, ROD, fuel=HEU)
    e = SimulationEngine(m)
    e._cast(0, 0, 0, 1, 100.0, 1.0, src)
    assert tgt.flux_q == 100.0
    assert tgt.flux_ratio == 1.0


def test_moderated_fuel_rod_receives_slow_flux():
    m = ReactorModel(1, 4)
    src = m.place(0, 0, ROD, fuel=HEU)
    rod = m.place(0, 1, ComponentType.RBMK_ROD_MOD, fuel=HEU)
    e = SimulationEngine(m)
    e._cast(0, 0, 0, 1, 100.0, 1.0, src)
    assert rod.flux_q == 100.0
    assert rod.flux_ratio == 0.0


def test_moderated_control_rod_still_attenuates():
    m = ReactorModel(1, 5)
    src = m.place(0, 0, ROD, fuel=HEU)
    ctrl = m.place(0, 1, ComponentType.RBMK_CONTROL_MOD)
    ctrl.insertion = 50.0        # level=0.5
    tgt = m.place(0, 2, ROD, fuel=HEU)
    e = SimulationEngine(m)
    e._cast(0, 0, 0, 1, 100.0, 1.0, src)
    assert tgt.flux_q == 50.0
    assert tgt.flux_ratio == 0.0


def test_moderated_origin_reflected_stream_is_slowed():
    m = ReactorModel(1, 4)
    src = m.place(0, 0, ComponentType.RBMK_ROD_MOD, fuel=HEU)
    m.place(0, 1, REFL)
    e = SimulationEngine(m)
    e._cast(0, 0, 0, 1, 100.0, 1.0, src)
    assert src.flux_q == 100.0
    assert src.flux_ratio == 0.0

    m2 = ReactorModel(1, 4)
    src2 = m2.place(0, 0, ROD, fuel=HEU)
    m2.place(0, 1, REFL)
    e2 = SimulationEngine(m2)
    e2._cast(0, 0, 0, 1, 100.0, 1.0, src2)
    assert src2.flux_ratio == 1.0


# ---------- ReaSim 组件（只有 ReaSim 方块才 8 向扩散）----------
def test_normal_channel_does_not_hit_diagonal_cells():
    m = ReactorModel(5, 5)
    m.place(2, 2, ROD, fuel=SRC)
    d = m.place(3, 3, ROD, fuel=HEU)
    e = SimulationEngine(m)
    e._neutron_tick()
    assert d.flux_q == 0.0


def test_reasim_rod_component_spreads_8_ways():
    m = ReactorModel(5, 5)
    m.place(2, 2, ComponentType.RBMK_ROD_REASIM, fuel=SRC)
    d = m.place(3, 3, ROD, fuel=HEU)
    e = SimulationEngine(m)
    e._neutron_tick()
    assert abs(d.flux_q - 50.0 * 0.75) < 1e-9


def test_reasim_mod_rod_component_spreads_8_ways():
    m = ReactorModel(5, 5)
    m.place(2, 2, ComponentType.RBMK_ROD_REASIM_MOD, fuel=SRC)
    d = m.place(3, 3, ROD, fuel=HEU)
    e = SimulationEngine(m)
    e._neutron_tick()
    assert abs(d.flux_q - 50.0 * 0.75) < 1e-9


# ---------- ReaSim 锅炉模式 ----------
def test_reasim_boilers_every_column_produces_steam():
    m = ReactorModel(5, 5)
    rod = m.place(2, 2, ROD, fuel=HEU)
    mod = m.place(0, 0, MOD)
    m.reasim_boilers = True
    e = SimulationEngine(m)
    rod.temp = 500.0
    mod.temp = 500.0
    e._heat_tick()
    # 冷却后 497.5；avail=(497.5-100)/0.1=3975；made=3975*0.05=198.75
    assert abs(rod.steam_rate - 198.0) < 1e-9     # floor(3975*0.05)=198
    assert abs(mod.steam_rate - 198.0) < 1e-9
    assert abs(rod.temp - (497.5 - 19.8)) < 1e-9


def test_reasim_boiler_cap_is_800_per_tick():
    m = ReactorModel(5, 5)
    cell = m.place(2, 2, MOD)
    m.reasim_boilers = True
    e = SimulationEngine(m)
    cell.temp = 5000.0
    e._heat_tick()
    assert abs(cell.steam_rate - 800.0) < 1e-9


def test_normal_boiler_mode_does_not_boil_non_boiler_columns():
    m = ReactorModel(5, 5)
    mod = m.place(2, 2, MOD)
    e = SimulationEngine(m)
    mod.temp = 500.0
    e._heat_tick()
    assert mod.steam_rate == 0.0


# ---------- 热量模型与模组对齐 ----------
def test_hull_heat_reaches_column_even_without_flux():
    """无中子输出时，残留芯/壳热仍应继续传向柱体（模组每 tick 都跑 updateHeat/provideHeat）。"""
    m = ReactorModel(5, 5)
    rod = m.place(2, 2, ROD, fuel=HEU)
    e = SimulationEngine(m)
    rod.core_heat = 1000.0
    rod.hull_heat = 800.0
    rod.temp = 20.0
    e._neutron_tick()
    # mid=100, diff=100*0.02=2 → core 998, hull 802
    # ret=(802-20)/2*0.2=78.2 → hull 723.8, 柱温 98.2
    assert abs(rod.core_heat - 998.0) < 1e-9
    assert abs(rod.hull_heat - 723.8) < 1e-9
    assert abs(rod.temp - 98.2) < 1e-9


def test_core_heat_does_not_flow_back_to_hull():
    """芯温低于壳温时，模组不做逆向传热。"""
    m = ReactorModel(5, 5)
    rod = m.place(2, 2, ROD, fuel=HEU)
    e = SimulationEngine(m)
    rod.core_heat = 100.0
    rod.hull_heat = 500.0
    rod.temp = 20.0
    e._neutron_tick()
    assert abs(rod.core_heat - 100.0) < 1e-9
    assert abs(rod.hull_heat - 452.0) < 1e-9
    assert abs(rod.temp - 68.0) < 1e-9


def test_hull_above_melting_point_equalizes_core_hull_column():
    """壳温 > 燃料熔点：芯/壳/柱取三者平均（ItemRBMKRod.provideHeat 分支）。"""
    m = ReactorModel(5, 5)
    rod = m.place(2, 2, ROD, fuel=HEU)   # 熔点 2865
    e = SimulationEngine(m)
    rod.core_heat = 3000.0
    rod.hull_heat = 3000.0
    rod.temp = 300.0
    e._neutron_tick()
    assert abs(rod.core_heat - 2100.0) < 1e-9
    assert abs(rod.hull_heat - 2100.0) < 1e-9
    assert abs(rod.temp - 2100.0) < 1e-9


def test_heat_coeff_uses_core_temperature():
    """热系数只看芯温，柱温不影响。"""
    m1 = ReactorModel(3, 3)
    r1 = m1.place(1, 1, ROD, fuel="rbmk_fuel_uzh")
    e1 = SimulationEngine(m1)
    r1.core_heat = 20.0
    r1.temp = 20.0
    base = e1._burn(r1, r1.fuel_type, 100.0)[0]

    m2 = ReactorModel(3, 3)
    r2 = m2.place(1, 1, ROD, fuel="rbmk_fuel_uzh")
    e2 = SimulationEngine(m2)
    r2.core_heat = 20.0
    r2.temp = 2000.0                 # 柱温很高，但芯温低 → 不应触发热系数
    cold = e2._burn(r2, r2.fuel_type, 100.0)[0]
    assert abs(cold - base) < 1e-12

    m3 = ReactorModel(3, 3)
    r3 = m3.place(1, 1, ROD, fuel="rbmk_fuel_uzh")
    e3 = SimulationEngine(m3)
    r3.core_heat = 1250.0            # 芯温进入热系数区间
    r3.temp = 20.0
    hot = e3._burn(r3, r3.fuel_type, 100.0)[0]
    # LOG_TEN 对富集度是分母关系，乘上 mult 后输出会变化（方向不重要，关键是“芯温生效”）
    assert abs(hot - base) > 1e-6


def test_boiler_infinite_water_removes_heat_up_to_feed_cap():
    """无限供水：每 tick 最多按 10,000 mB 水带走 1,000 热量。"""
    m = ReactorModel(3, 3)
    b = m.place(1, 1, BOIL)
    e = SimulationEngine(m)
    b.temp = 2000.0
    b.water = 0.0
    e._heat_tick()
    # heatProvided=1900 → 需求 19000 mB，水箱 10000 → 移除 1000，再被动冷却 2.5
    assert abs(b.temp - 997.5) < 1e-9
    assert b.water == 10000.0


def test_boiler_full_tank_cools_to_steam_threshold():
    """水箱充足时，锅炉仍会把柱温压到当前蒸汽类型的阈值。"""
    m = ReactorModel(3, 3)
    b = m.place(1, 1, BOIL)
    e = SimulationEngine(m)
    b.temp = 800.0
    b.water = 10000.0
    e._heat_tick()
    # 锅炉先压到阈值 100，随后 moveHeat 的被动冷却再降 2.5
    assert abs(b.temp - 97.5) < 1e-9


# ---------- 反射体 / 吸收体 ----------
def test_reflector_does_not_generate_heat_from_flux():
    """模组反射体（TileEntityRBMKReflector）没有中子吸热逻辑，只把流反射回源棒。"""
    m = ReactorModel(1, 5)
    src = m.place(0, 0, ROD, fuel=HEU)
    refl = m.place(0, 1, REFL)
    e = SimulationEngine(m)
    e._cast(0, 0, 0, 1, 100.0, 1.0, src)
    assert refl.temp == 20.0          # 中子 tick 不改变反射体柱温
    assert refl.heat == 0.0           # 没有直接吸热
    assert src.flux_q == 100.0        # 全额反射回源棒


def test_reflector_heats_only_by_conduction():
    m = ReactorModel(5, 5)
    rod = m.place(2, 2, ROD, fuel=HEU)
    refl = m.place(2, 3, REFL)
    e = SimulationEngine(m)
    rod.temp = 1000.0
    refl.temp = 20.0
    e._heat_tick()
    assert refl.temp > 20.0           # 通过四邻扩散升温
    assert refl.heat == 0.0


def test_absorber_heat_goes_into_column_temperature():
    """模组：absorber.heat += absorberHeatConversion(0.05) * flux，加在柱温上。"""
    m = ReactorModel(1, 5)
    src = m.place(0, 0, ROD, fuel=HEU)
    absb = m.place(0, 1, ABS)
    e = SimulationEngine(m)
    e._cast(0, 0, 0, 1, 100.0, 1.0, src)
    assert abs(absb.temp - 25.0) < 1e-9
    assert abs(absb.heat - 5.0) < 1e-9


def test_depletion_modifier_matches_jar():
    """ItemRBMKRod.reactivityModByEnrichment 五种函数的精确值（含耗损后的富集度）。"""
    import math
    from rbmk.sim.engine import depletion_modifier as dm
    for e in (1.0, 0.62, 0.35):
        assert abs(dm("LINEAR", e) - e) < 1e-12
        assert abs(dm("STATIC", e) - 1.0) < 1e-12
        assert abs(dm("BOOSTED_SLOPE", e) - (e + math.sin((e - 1.0) ** 2 * math.pi))) < 1e-12
        assert abs(dm("RAISING_SLOPE", e) - (e + math.sin(e * math.pi) / 2.0)) < 1e-12
        assert abs(dm("GENTLE_SLOPE", e) - (e + math.sin(e * math.pi) / 3.0)) < 1e-12


def test_gentle_slope_fuel_scales_with_enrichment():
    """回归：GENTLE_SLOPE 曾被错写成 sin/2（应为 sin/3），耗损后反应性偏高。"""
    import math
    from rbmk.model.components import FUELS
    from rbmk.sim.engine import reactivity_function
    ft = FUELS["rbmk_fuel_heu235"]        # SQUARE_ROOT + GENTLE_SLOPE, r=50
    e = 0.5
    flux = 100.0 * (e + math.sin(e * math.pi) / 3.0)
    expected = math.sqrt(flux) * ft.reactivity / 10.0
    assert abs(reactivity_function(ft, 100.0, e) - expected) < 1e-9
    assert reactivity_function(ft, 100.0, e) < reactivity_function(ft, 100.0, 1.0)


def test_raising_slope_fuel_uses_raising_curve_not_static():
    """回归：RAISING_SLOPE 曾被错写成 STATIC(1.0)，耗损后输出必须随富集度变化。"""
    import math
    from rbmk.model.components import FUELS
    from rbmk.sim.engine import reactivity_function
    ft = FUELS["rbmk_fuel_ueu"]           # LOG_TEN + RAISING_SLOPE, r=15
    e = 0.75
    flux = 100.0 * (e + math.sin(e * math.pi) / 2.0)
    expected = math.log10(flux + 1.0) * 0.5 * ft.reactivity
    assert abs(reactivity_function(ft, 100.0, e) - expected) < 1e-9
    # STATIC 会得到 log10(101)*0.5*15 ≈ 15.03，与正确值不同
    assert abs(reactivity_function(ft, 100.0, e) - math.log10(101.0) * 0.5 * 15.0) > 1e-6
