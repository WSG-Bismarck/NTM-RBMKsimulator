"""阶段 2 界面测试：6 区域、组件栏 14 项、4 个标签页、放置/选择、速度/运行。"""
from rbmk.app.main_window import create_app
from rbmk.model.components import ComponentType


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
        assert set(win._metric_labels) == {"temp", "power", "energy", "steam", "flux", "fuel"}
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
    """回归：拖动全局/冷却滑块不应重建面板导致控件消失。"""
    win, root = _fresh()
    try:
        win.set_tab("control")
        win.render_panel()
        win._set_global(30)
        win._set_coolant(80)
        assert win.model.global_insertion == 30
        assert win.model.coolant_flow == 80
        assert win._lbl_global.winfo_exists()
        assert win._lbl_coolant.winfo_exists()
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
        win._set_fuel(win.model.cell_at(2, 2), "低浓缩镅")
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
