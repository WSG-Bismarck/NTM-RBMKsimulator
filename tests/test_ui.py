"""阶段 2 界面测试：6 区域、组件栏 14 项、4 个标签页、放置/选择、速度/运行。"""
from rbmk.app.main_window import create_app
from rbmk.model.components import ComponentType, FUELS


def _fresh():
    win, root = create_app()
    root.update()
    return win, root


def test_six_zones_and_counts():
    win, root = _fresh()
    try:
        assert hasattr(win, "grid_editor")
        assert hasattr(win, "chart")
        assert hasattr(win, "panel")
        assert hasattr(win, "sb_state")
        assert len(win._palette_items) == 18
        assert len(win._tab_btns) == 4
        # 6 项关键数值标签
        assert set(win._metric_labels) == {"temp", "flux", "steam", "power", "total", "fuel"}
    finally:
        root.destroy()


def test_place_and_overview():
    win, root = _fresh()
    try:
        win.select_tool(ComponentType.RBMK_ROD.value)
        win.model.place(2, 2, ComponentType.RBMK_ROD, fuel="rbmk_fuel_heu235")
        win.model.place(2, 3, ComponentType.RBMK_CONTROL)
        win.on_model_changed()
        win.set_tab("overview")
        win.render_panel()
        assert win.model.fuel_count() == 1
        assert win.model.counts()[ComponentType.RBMK_CONTROL] == 1
        assert len(win.panel.winfo_children()) > 0
    finally:
        root.destroy()


def test_select_shows_properties():
    win, root = _fresh()
    try:
        win.model.place(3, 3, ComponentType.RBMK_ROD, fuel="rbmk_fuel_ueu")
        win.on_select((3, 3))
        assert win.tab == "prop"
        assert len(win.panel.winfo_children()) > 0
    finally:
        root.destroy()


def test_speed_and_run_toggle():
    win, root = _fresh()
    try:
        win.set_speed(10)
        assert win.speed == 10
        win.toggle_run()
        assert win.running is True
        win.toggle_run()
        assert win.running is False
    finally:
        root.destroy()


def test_all_tabs_render():
    win, root = _fresh()
    try:
        for t in ("prop", "overview", "control", "risk"):
            win.set_tab(t)
            win.render_panel()
            assert win.tab == t
    finally:
        root.destroy()


def test_simulation_advances_when_running():
    win, root = _fresh()
    try:
        win.model.place(5, 5, ComponentType.RBMK_ROD, fuel="rbmk_fuel_heu235")
        win.on_model_changed()
        win.set_speed(100)
        win.toggle_run()
        win._tick()  # 手动推进一次
        assert win.engine.state.time > 0
    finally:
        root.destroy()


def test_control_slider_does_not_destroy_panel():
    """回归：拖动全局插入深度滑块不应重建面板导致控件消失。"""
    win, root = _fresh()
    try:
        win.set_tab("control")
        win.render_panel()
        win._set_global(30)
        assert win.model.global_insertion == 30
        assert win._lbl_global.winfo_exists()
        win.render_panel()  # 仍可正常重绘
    finally:
        root.destroy()


def test_grid_paint_drag_erase_select():
    win, root = _fresh()
    try:
        win.select_tool(ComponentType.RBMK_ROD.value)
        win.grid_editor._paint((2, 2))
        assert win.model.cell_at(2, 2).comp == ComponentType.RBMK_ROD
        win.grid_editor._paint((2, 3))  # 模拟拖动连续放置
        assert win.model.cell_at(2, 3) is not None
        win.select_tool("erase")
        win.grid_editor._paint((2, 2))
        assert win.model.cell_at(2, 2) is None
        win.select_tool("select")
        win.grid_editor._paint((2, 3))
        assert win.selected_cell == (2, 3)
    finally:
        root.destroy()


def test_grid_zoom_and_pan():
    win, root = _fresh()
    try:
        old = win.grid_editor.cell

        class _E:
            delta = 120

        win.grid_editor._on_wheel(_E())
        assert win.grid_editor.cell > old

        ox0, oy0 = win.grid_editor._origin()
        win.grid_editor.pan_x = 30
        win.grid_editor.pan_y = 20
        ox1, oy1 = win.grid_editor._origin()
        assert (ox1 - ox0, oy1 - oy0) == (30, 20)
    finally:
        root.destroy()


def test_prop_panel_shows_component_parameters():
    win, root = _fresh()
    try:
        win.model.place(3, 3, ComponentType.RBMK_ROD, fuel="rbmk_fuel_heu235")
        win.on_select((3, 3))
        assert win._prop_labels
        for key in ("temp", "core", "hull", "flux", "fast", "slow", "ratio", "outflux", "selfrate"):
            assert key in win._prop_labels
        assert "°C" in win._prop_labels["temp"].cget("text")
        assert win._prop_labels["fast"].cget("text") != "—"
        assert win._prop_labels["slow"].cget("text") != "—"
    finally:
        root.destroy()


def test_prop_panel_control_and_boiler_fields():
    win, root = _fresh()
    try:
        win.model.place(2, 2, ComponentType.RBMK_CONTROL)
        win.model.place(2, 3, ComponentType.RBMK_BOILER)
        win.on_select((2, 2))
        assert "level" in win._prop_labels
        win.on_select((2, 3))
        assert "steam" in win._prop_labels
    finally:
        root.destroy()


def test_prop_panel_marks_self_igniting_fuel():
    win, root = _fresh()
    try:
        win.model.place(2, 2, ComponentType.RBMK_ROD, fuel="rbmk_fuel_lea")
        win.on_select((2, 2))

        def texts(w):
            out = []
            for ch in w.winfo_children():
                try:
                    if "text" in ch.keys():
                        out.append(ch.cget("text"))
                except Exception:
                    pass
                out.extend(texts(ch))
            return out

        assert "自燃" in texts(win.panel)
    finally:
        root.destroy()


def test_ui_place_self_igniting_rod_starts():
    """回归：在界面里先建引擎、再放自燃燃料棒，运行后必须发电。"""
    win, root = _fresh()
    try:
        win.select_tool(ComponentType.RBMK_ROD.value)
        win.grid_editor._paint((2, 2))
        win._set_fuel(win.model.cell_at(2, 2), FUELS["rbmk_fuel_lea"].name_cn)
        win.set_speed(100)
        win.toggle_run()
        win._tick()
        assert win.engine.state.power > 0
    finally:
        root.destroy()


def test_reset_pauses_and_clears_state_keeping_layout():
    win, root = _fresh()
    try:
        win.model.place(2, 2, ComponentType.RBMK_ROD, fuel="rbmk_fuel_po210be")
        win.model.place(2, 3, ComponentType.RBMK_ROD, fuel="rbmk_fuel_heu235")
        win.on_model_changed()
        win.set_speed(100)
        win.toggle_run()
        win._tick()
        assert win.running
        assert win.engine.state.time > 0
        before_fuel = win.model.fuel_count()
        before_cells = sum(1 for _ in win.model.iter_cells())

        win.reset_simulation()

        assert win.running is False
        assert win.engine.state.time == 0
        assert win.engine.state.power == 0
        assert win.engine.state.total_energy == 0
        assert win.engine.state.temperature == 20.0
        # 组件必须保留
        assert win.model.fuel_count() == before_fuel
        assert sum(1 for _ in win.model.iter_cells()) == before_cells
        c = win.model.cell_at(2, 3)
        assert c is not None
        assert c.burnup == 0.0
        assert c.temp == 20.0
        assert win.run_btn.cget("text") == "▶ 运行"
    finally:
        root.destroy()


def test_prop_panel_hides_core_hull_for_non_fuel():
    """非燃料通道不显示芯温/壳温，燃料通道仍显示。"""
    win, root = _fresh()
    try:
        win.model.place(2, 2, ComponentType.RBMK_BOILER)
        win.on_select((2, 2))
        assert "core" not in win._prop_labels
        assert "hull" not in win._prop_labels
        assert "temp" in win._prop_labels

        win.model.place(2, 3, ComponentType.RBMK_ROD, fuel="rbmk_fuel_heu235")
        win.on_select((2, 3))
        assert "core" in win._prop_labels
        assert "hull" in win._prop_labels
    finally:
        root.destroy()


def test_prop_panel_hides_neutron_rows_for_non_fuel():
    """非燃料通道（含辐照通道）不显示通量/快慢中子计数/快中子占比。"""
    win, root = _fresh()
    try:
        for col, comp in ((1, ComponentType.RBMK_BOILER),
                          (2, ComponentType.RBMK_OUTGASSER),
                          (3, ComponentType.RBMK_MODERATOR)):
            win.model.place(2, col, comp)
            win.on_select((2, col))
            for key in ("flux", "fast", "slow", "ratio", "outflux"):
                assert key not in win._prop_labels, (comp, key)
            assert "temp" in win._prop_labels

        win.model.place(2, 4, ComponentType.RBMK_ROD, fuel="rbmk_fuel_heu235")
        win.on_select((2, 4))
        for key in ("flux", "fast", "slow", "ratio", "outflux"):
            assert key in win._prop_labels
    finally:
        root.destroy()


def test_prop_panel_hides_burnup_for_fuel():
    """燃料通道不再显示燃耗，但保留剩余寿命与氙毒。"""
    win, root = _fresh()
    try:
        win.model.place(2, 2, ComponentType.RBMK_ROD, fuel="rbmk_fuel_heu235")
        win.on_select((2, 2))
        assert "burnup" not in win._prop_labels
        assert "life" in win._prop_labels
        assert "xenon" in win._prop_labels
    finally:
        root.destroy()


def test_prop_panel_hides_reactivity_for_fuel():
    """燃料通道不再显示反应性，保留燃烧函数与自发射率。"""
    win, root = _fresh()
    try:
        win.model.place(2, 2, ComponentType.RBMK_ROD, fuel="rbmk_fuel_heu235")
        win.on_select((2, 2))
        assert "reactivity" not in win._prop_labels
        assert "function" in win._prop_labels
        assert "selfrate" in win._prop_labels
    finally:
        root.destroy()


def test_prop_panel_function_chinese_and_split_neutron_types():
    """燃烧函数显示中文；中子类型拆成所需/产生两行。"""
    win, root = _fresh()
    try:
        win.model.place(2, 2, ComponentType.RBMK_ROD, fuel="rbmk_fuel_heu235")
        win.on_select((2, 2))
        assert "ntype" not in win._prop_labels
        assert win._prop_labels["function"].cget("text") == "平方根"
        assert win._prop_labels["ntype_in"].cget("text") == "慢中子"
        assert win._prop_labels["ntype_out"].cget("text") == "快中子"

        win.model.place(2, 3, ComponentType.RBMK_ROD, fuel="rbmk_fuel_po210be")
        win.on_select((2, 3))
        assert win._prop_labels["function"].cget("text") == "恒定输出"
    finally:
        root.destroy()


def test_boiler_prop_shows_steam_per_tick():
    """锅炉属性显示每 tick 产汽量（/tick），不是累计值。"""
    win, root = _fresh()
    try:
        boiler = win.model.place(2, 2, ComponentType.RBMK_BOILER)
        boiler.temp = 200.0
        win.engine._heat_tick()
        win.on_select((2, 2))
        text = win._prop_labels["steam"].cget("text")
        assert text.endswith("mB/tick")
        assert float(text.split()[0]) > 0

        win.engine._heat_tick()          # 温度降到 100 以下后不再产汽
        win.engine._heat_tick()
        win.engine._heat_tick()
        win.engine._heat_tick()
        win._refresh_prop_values()
        assert win._prop_labels["steam"].cget("text") == "0 mB/tick"
    finally:
        root.destroy()


def test_boiler_prop_has_steam_type_selector():
    """锅炉属性里有蒸汽类型下拉框，可切换为模组四种蒸汽。"""
    win, root = _fresh()
    try:
        win.model.place(2, 2, ComponentType.RBMK_BOILER)
        win.on_select((2, 2))

        def texts(w):
            out = []
            for ch in w.winfo_children():
                try:
                    if "text" in ch.keys():
                        out.append(ch.cget("text"))
                except Exception:
                    pass
                out.extend(texts(ch))
            return out

        assert "蒸汽类型" in texts(win.panel)
        cell = win.model.cell_at(2, 2)
        for name, key in (("蒸汽", "STEAM"), ("热蒸汽", "HOTSTEAM"),
                          ("超热蒸汽", "SUPERHOTSTEAM"), ("超浓密蒸汽", "ULTRAHOTSTEAM")):
            win._set_steam_type(cell, name)
            assert cell.steam_type == key
    finally:
        root.destroy()


def test_control_panel_has_no_coolant_control():
    """冷却水流量控制已移除。"""
    win, root = _fresh()
    try:
        win.set_tab("control")
        win.render_panel()
        assert not hasattr(win, "_lbl_coolant")
        assert not hasattr(win, "_set_coolant")
    finally:
        root.destroy()


def test_overview_global_steam_type_selector():
    """总览里可以一键切换所有蒸汽管道的蒸汽类型。"""
    win, root = _fresh()
    try:
        win.model.place(2, 2, ComponentType.RBMK_BOILER, steam_type="STEAM")
        win.model.place(2, 3, ComponentType.RBMK_BOILER, steam_type="HOTSTEAM")
        win.set_tab("overview")
        win.render_panel()

        def texts(w):
            out = []
            for ch in w.winfo_children():
                try:
                    if "text" in ch.keys():
                        out.append(ch.cget("text"))
                except Exception:
                    pass
                out.extend(texts(ch))
            return out

        assert "全部蒸汽管道蒸汽类型" in texts(win.panel)
        win._set_all_steam_types("超浓密蒸汽")
        assert win.model.cell_at(2, 2).steam_type == "ULTRAHOTSTEAM"
        assert win.model.cell_at(2, 3).steam_type == "ULTRAHOTSTEAM"
    finally:
        root.destroy()


def test_metrics_bar_titles_and_placeholders():
    """下方 6 项：平均温度、平均通量、蒸汽(mB/s)、瞬时发电(HE/tick)、累计发电(HE)、平均寿命。"""
    win, root = _fresh()
    try:
        win.model.place(2, 2, ComponentType.RBMK_ROD, fuel="rbmk_fuel_heu235")
        win.on_model_changed()
        win.engine.advance(1.0)
        win._refresh_state()

        def texts(w):
            out = []
            for ch in w.winfo_children():
                try:
                    if "text" in ch.keys():
                        out.append(ch.cget("text"))
                except Exception:
                    pass
                out.extend(texts(ch))
            return out

        titles = texts(win.metrics)
        for title in ("反应堆平均温度", "平均中子通量", "蒸汽产量",
                      "瞬时发电量", "累计发电量", "燃料平均寿命"):
            assert title in titles

        assert win._metric_labels["temp"].cget("text").endswith("°C")
        assert win._metric_labels["steam"].cget("text").endswith("mB/s")
        assert win._metric_labels["power"].cget("text").endswith("HE/tick")
        assert win._metric_labels["total"].cget("text").endswith("HE")
        assert win._metric_labels["fuel"].cget("text").endswith("%")
    finally:
        root.destroy()


def test_heater_prop_has_fluid_and_output_controls():
    """流体加热器属性：流体类型下拉框 + 每刻加热流体产量可调。"""
    win, root = _fresh()
    try:
        win.model.place(2, 2, ComponentType.RBMK_HEATER)
        win.on_select((2, 2))

        def texts(w):
            out = []
            for ch in w.winfo_children():
                try:
                    if "text" in ch.keys():
                        out.append(ch.cget("text"))
                except Exception:
                    pass
                out.extend(texts(ch))
            return out

        t = texts(win.panel)
        assert "流体类型" in t
        assert "每刻加热流体产量" in t
        assert "每刻热量产出" in t

        cell = win.model.cell_at(2, 2)
        win._set_heater_fluid(cell, "血")
        assert cell.heater_fluid == "BLOOD"
        assert not hasattr(win, "_set_heater_output")
        assert "heater" in win._prop_labels
        assert "heater_heat" in win._prop_labels
    finally:
        root.destroy()


def test_overview_global_heater_fluid_selector():
    """总览里可以一键切换所有流体加热器的流体类型。"""
    win, root = _fresh()
    try:
        win.model.place(2, 2, ComponentType.RBMK_HEATER, heater_fluid="WATER")
        win.model.place(2, 3, ComponentType.RBMK_HEATER, heater_fluid="OIL")
        win.set_tab("overview")
        win.render_panel()

        def texts(w):
            out = []
            for ch in w.winfo_children():
                try:
                    if "text" in ch.keys():
                        out.append(ch.cget("text"))
                except Exception:
                    pass
                out.extend(texts(ch))
            return out

        assert "全部流体加热器流体类型" in texts(win.panel)
        win._set_all_heater_fluids("血")
        assert win.model.cell_at(2, 2).heater_fluid == "BLOOD"
        assert win.model.cell_at(2, 3).heater_fluid == "BLOOD"
    finally:
        root.destroy()


def test_toolbar_toggles_reasim_boiler_mode():
    win, root = _fresh()
    try:
        assert win.model.reasim_boilers is False
        assert win.boiler_btn.cget("text") == "锅炉：普通"
        win.toggle_boiler_mode()
        assert win.model.reasim_boilers is True
        assert win.boiler_btn.cget("text") == "锅炉：ReaSim"
        win.toggle_boiler_mode()
        assert win.model.reasim_boilers is False
        assert win.boiler_btn.cget("text") == "锅炉：普通"
    finally:
        root.destroy()


def test_prop_panel_has_no_neighbor_count_or_heat_power():
    """属性面板不再显示邻接数与热功率。"""
    from rbmk.model.components import ComponentType
    win, root = _fresh()
    try:
        win.select_tool(ComponentType.RBMK_ROD.value)
        win.grid_editor._paint((2, 2))
        win.on_select((2, 2))
        assert "neighbors" not in win._prop_labels
        assert "heat" not in win._prop_labels
        assert "temp" in win._prop_labels
        assert "cooling" in win._prop_labels
    finally:
        root.destroy()


def test_control_group_can_be_set_to_vacant():
    """控制棒控制组可以选「空置」：不受分组滑块影响，回落到全局/单根。"""
    from rbmk.model.components import ComponentType
    win, root = _fresh()
    try:
        win.select_tool(ComponentType.RBMK_CONTROL.value)
        win.grid_editor._paint((2, 2))
        cell = win.model.cell_at(2, 2)
        win._set_group(cell, "空置")
        assert cell.group is None
        win.model.group_insertion["RED"] = 10.0
        assert win.model.effective_insertion(cell) == win.model.global_insertion
        win._set_group(cell, "红组")
        assert cell.group is not None
        assert win.model.effective_insertion(cell) == 10.0
    finally:
        root.destroy()


def test_chart_shows_avg_temp_flux_and_electricity():
    """实时曲线的三条线：平均温度 / 中子通量 / 瞬时发电量。"""
    from rbmk.model.components import ComponentType
    win, root = _fresh()
    try:
        assert set(win.chart.hist) == {"temp", "elec", "flux"}
        win.model.place(2, 2, ComponentType.RBMK_ROD, fuel="rbmk_fuel_po210be")
        win.model.place(2, 3, ComponentType.RBMK_BOILER)
        win.on_model_changed()
        win.set_speed(1)
        win.toggle_run()
        for _ in range(5):
            win._tick()
        win.toggle_run()
        st = win.engine.state
        assert abs(win.chart.hist["temp"][-1] - st.avg_temperature) < 1e-9
        assert abs(win.chart.hist["elec"][-1] - st.electricity) < 1e-9
        assert abs(win.chart.hist["flux"][-1] - st.flux) < 1e-9
    finally:
        root.destroy()


def test_auto_control_sliders_accept_manual_input():
    """自动控制棒四个参数：滑块旁有输入框，回车/失焦生效、超范围夹紧、非法输入回退。"""
    from rbmk.model.components import ComponentType
    win, root = _fresh()
    try:
        win.select_tool(ComponentType.RBMK_CONTROL_AUTO.value)
        win.grid_editor._paint((2, 2))
        win.on_select((2, 2))
        cell = win.model.cell_at(2, 2)

        def walk(w):
            for ch in w.winfo_children():
                yield ch
                yield from walk(ch)

        entries = [w for w in walk(win.panel) if w.winfo_class() == "Entry"]
        assert len(entries) == 4
        ent = entries[0]                       # 温度下限
        assert ent.bind("<Return>")            # 已绑定回车
        assert ent.bind("<FocusOut>")          # 已绑定失焦
        scale = ent._auto_scale
        assert cell.heat_lower == 0.0

        def apply(text):
            ent.delete(0, "end")
            ent.insert(0, text)
            win._auto_entry_applied(cell, "heat_lower", ent, scale)

        apply("321")
        assert cell.heat_lower == 321.0
        assert ent.get() == "321"
        assert float(scale.get()) == 321.0

        apply("99999")
        assert cell.heat_lower == 1500.0       # 夹到滑块上限

        apply("abc")
        assert cell.heat_lower == 1500.0       # 非法输入恢复原值
        assert ent.get() == "1500"
    finally:
        root.destroy()


def test_cooler_prop_shows_cold_perfluoromethyl_per_tick():
    """冷却器属性显示每刻消耗冷四氟甲烷。"""
    from rbmk.model.components import ComponentType
    win, root = _fresh()
    try:
        win.select_tool(ComponentType.RBMK_COOLER.value)
        win.grid_editor._paint((2, 2))
        win.on_select((2, 2))
        assert win._prop_labels["cooler_use"].cget("text") == "0 mB/tick"
        win.set_speed(1)
        win.toggle_run()
        for _ in range(3):
            win._tick()
        win.toggle_run()
        assert win._prop_labels["cooler_use"].cget("text") == "50 mB/tick"
        assert win._prop_labels["cooler_cells"].cget("text") == "1"
    finally:
        root.destroy()


def test_reasim_mode_shows_component_reasim_steam_row():
    """切换到 ReaSim 锅炉模式后，属性面板出现「每刻 ReaSim 蒸汽产量」。"""
    from rbmk.model.components import ComponentType
    win, root = _fresh()
    try:
        win.select_tool(ComponentType.RBMK_BLANK.value)
        win.grid_editor._paint((2, 2))
        win.on_select((2, 2))
        assert "reasim_steam" not in win._prop_labels
        win.toggle_boiler_mode()
        assert "reasim_steam" in win._prop_labels
        cell = win.model.cell_at(2, 2)
        cell.temp = 500.0
        win.set_speed(1)
        win.toggle_run()
        win._tick()
        win.toggle_run()
        assert win._prop_labels["reasim_steam"].cget("text").endswith("mB/tick")
        win.toggle_boiler_mode()
        assert "reasim_steam" not in win._prop_labels
    finally:
        root.destroy()


def test_components_use_mod_block_icons():
    """网格与左侧组件栏使用模组方块贴图（rbmk_*_top.png），不是纯色块。"""
    from rbmk.model.components import ComponentType
    from rbmk.app.icons import get_icon
    win, root = _fresh()
    try:
        assert get_icon(ComponentType.RBMK_BOILER.value, 16) is not None
        win.select_tool(ComponentType.RBMK_BOILER.value)
        win.grid_editor._paint((2, 2))
        win.grid_editor.redraw()
        cv = win.grid_editor.canvas
        images = [i for i in cv.find_all() if cv.type(i) == "image"]
        assert images, "网格里应绘制组件图标"
        # 左侧组件栏：至少一个组件行里是带 image 的 Label
        has_icon_label = False
        for row in win._palette_items.values():
            for ch in row.winfo_children():
                if ch.winfo_class() == "Label" and ch.cget("image"):
                    has_icon_label = True
        assert has_icon_label
    finally:
        root.destroy()


def test_column_overlays_match_console_coordinates():
    """叠加层几何：热量红线高度、燃料三色条、控制棒分组色坐标与模组一致。"""
    from rbmk.app.overlays import column_overlays, C_HEAT, C_SKIN, C_ENRICH, C_XENON
    from rbmk.model.components import ComponentType, ControlGroup
    from rbmk.model.reactor import ReactorModel

    m = ReactorModel(3, 3)
    m.place(1, 1, ComponentType.RBMK_ROD)
    rod = m.cell_at(1, 1)
    rod.fuel = "rbmk_fuel_flashlead"
    rod.shown_temp = 770.0        # ceil(750*10/1500) = 5
    rod.hull_heat = 2030.0       # 熔点 2050 → ceil(2010*8/2050) = 8
    rod.burnup = 0.0
    rod.xenon = 50.0
    rects = column_overlays(rod, m)
    colors = {(r[0], r[1], r[2], r[3]): r[4] for r in rects}
    # 热量红线：左右各 1 宽，高 5，自底向上
    assert colors[(0, 5, 1, 5)] == C_HEAT
    assert colors[(9, 5, 1, 5)] == C_HEAT
    # 燃料三色条：x+1 壳温 / x+4 浓缩度 / x+7 氙毒，均为 3px 宽铺满内容区
    assert colors[(1, 1, 2, 8)] == C_SKIN      # 壳温接近熔点 → 满 8（模组上限）
    assert colors[(4, 1, 2, 8)] == C_ENRICH    # 燃耗 0 → 满 8
    assert colors[(7, 5, 2, 4)] == C_XENON     # 氙 50% → 4/8

    m.place(1, 2, ComponentType.RBMK_CONTROL)
    ctl = m.cell_at(1, 2)
    ctl.group = ControlGroup.BLUE
    ctl.insertion = 25.0
    rects = column_overlays(ctl, m)
    colors = {(r[0], r[1], r[2], r[3]): r[4] for r in rects}
    assert colors[(3, 1, 1, 8)] == (0, 38, 255)   # 分组色两条竖线 x+3 / x+6
    assert colors[(6, 1, 1, 8)] == (0, 38, 255)
    # 手动棒穿透到插入条：fr = 8 - ceil(0.25*8) = 6
    assert any(r[:4] == (4, 1, 2, 6) for r in rects)


def test_grid_cells_stay_aligned_when_overlays_drawn():
    """回归：绘制叠加层时不得覆盖网格原点变量，所有格子必须落在网格坐标上。"""
    from rbmk.model.components import ComponentType
    win, root = _fresh()
    try:
        ge = win.grid_editor
        cs = ge.cell
        ox, oy = ge._origin()
        # 两个燃料格 + 一个蒸汽管道格，确保叠加层被绘制
        win.model.place(2, 2, ComponentType.RBMK_ROD)
        c = win.model.cell_at(2, 2)
        c.fuel = "rbmk_fuel_flashlead"
        c.shown_temp = 770.0
        c.hull_heat = 300.0
        c.xenon = 40.0
        win.model.place(5, 6, ComponentType.RBMK_BOILER)
        ge.redraw()
        cv = ge.canvas
        boxes = [cv.coords(i) for i in cv.find_all() if cv.type(i) == "rectangle"]
        # 每个格子背景矩形（尺寸≈cs）都应严格对齐 (ox+2+c*(cs+2), oy+2+r*(cs+2), +cs)
        backgrounds = [b for b in boxes
                       if abs((b[2] - b[0]) - cs) < 1.5 and abs((b[3] - b[1]) - cs) < 1.5]
        assert len(backgrounds) >= win.model.rows * win.model.cols - 1
        for b in backgrounds:
            dx = (b[0] - ox) % cs
            dy = (b[1] - oy) % cs
            assert min(dx, cs - dx) < 1.5, f"矩形 x 未对齐网格: {b}"
            assert min(dy, cs - dy) < 1.5, f"矩形 y 未对齐网格: {b}"
        # 燃料格背景必须存在于预期坐标
        x = ox + 2 * cs
        y = oy + 2 * cs
        assert any(abs(b[0] - x) < 1 and abs(b[1] - y) < 1 and b[2] - b[0] >= cs - 1 for b in boxes)
        # 不得有格子被推到网格区域外
        right = ox + win.model.cols * cs
        bottom = oy + win.model.rows * cs
        for b in boxes:
            assert b[2] <= right and b[3] <= bottom, f"图元超出网格区域: {b}"
    finally:
        root.destroy()


def test_grid_icons_fill_cell_exactly():
    """图标必须铺满整格并与格子左上角对齐，否则叠加层会与图标错位。"""
    from rbmk.model.components import ComponentType
    win, root = _fresh()
    try:
        ge = win.grid_editor
        win.model.place(2, 2, ComponentType.RBMK_ROD)
        ge.redraw()
        cv = ge.canvas
        cs = ge.cell
        ox, oy = ge._origin()
        images = [i for i in cv.find_all() if cv.type(i) == "image"]
        assert images
        b = cv.bbox(images[0])
        x = ox + 2 * cs
        y = oy + 2 * cs
        assert abs(b[0] - x) <= 1, f"图标左边未与格子对齐: {b} vs {x}"
        assert abs(b[1] - y) <= 1, f"图标上边未与格子对齐: {b} vs {y}"
        assert abs((b[2] - b[0] + 1) - cs) <= 2, f"图标宽度未铺满格子: {b}"
        assert abs((b[3] - b[1] + 1) - cs) <= 2, f"图标高度未铺满格子: {b}"
    finally:
        root.destroy()


def test_toolbar_has_no_console_button():
    """按用户要求移除工具栏的「控制台」入口。"""
    win, root = _fresh()
    try:
        texts = []
        for w in win.root.winfo_children():
            if w.winfo_class() != "Frame":
                continue
            for c in w.winfo_children():
                if c.winfo_class() == "Button":
                    texts.append(c.cget("text"))
        assert "控制台" not in texts
        assert not hasattr(win, "open_console")
    finally:
        root.destroy()


def test_grid_cells_are_adjacent_without_gap():
    """已放置组件之间不再有间隙：相邻格子的左边界相差正好一个格子边长。"""
    win, root = _fresh()
    try:
        ge = win.grid_editor
        cs = ge.cell
        ox, oy = ge._origin()
        ge.redraw()
        cv = ge.canvas
        xs = sorted({cv.coords(i)[0] for i in cv.find_all()
                     if cv.type(i) == "rectangle" and abs((cv.coords(i)[2] - cv.coords(i)[0]) - (cs - 1)) < 1.5})
        assert len(xs) >= win.model.cols - 1
        for a, b in zip(xs[:win.model.cols - 1], xs[1:win.model.cols]):
            assert abs((b - a) - cs) < 0.01, f"相邻格子间距应为 {cs}，实际 {b - a}"
        assert abs(xs[0] - ox) < 0.01
    finally:
        root.destroy()


def test_control_rod_has_no_group_color_frame():
    """控制棒不再用分组颜色做外框：格子描边统一为常规深色、1px。"""
    from rbmk.model.components import ComponentType, ControlGroup
    win, root = _fresh()
    try:
        ge = win.grid_editor
        cs = ge.cell
        ox, oy = ge._origin()
        win.model.place(3, 3, ComponentType.RBMK_CONTROL)
        win.model.cell_at(3, 3).group = ControlGroup.RED
        ge.redraw()
        cv = ge.canvas
        x, y = ox + 3 * cs, oy + 3 * cs
        target = None
        for i in cv.find_all():
            if cv.type(i) != "rectangle":
                continue
            co = cv.coords(i)
            if abs(co[0] - x) < 1 and abs(co[1] - y) < 1 and abs((co[2] - co[0]) - (cs - 1)) < 1.5:
                target = i
        assert target is not None
        assert cv.itemcget(target, "outline") == ""
        assert float(cv.itemcget(target, "width")) == 1.0
    finally:
        root.destroy()
