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
        assert len(win._palette_items) == 14
        assert len(win._tab_btns) == 4
        # 6 项关键数值标签
        assert set(win._metric_labels) == {"temp", "power", "energy", "steam", "flux", "fuel"}
    finally:
        root.destroy()


def test_place_and_overview():
    win, root = _fresh()
    try:
        win.select_tool(ComponentType.FUEL.value)
        win.model.place(2, 2, ComponentType.FUEL, fuel="rbmk_fuel_heu235")
        win.model.place(2, 3, ComponentType.CONTROL)
        win.on_model_changed()
        win.set_tab("overview")
        win.render_panel()
        assert win.model.fuel_count() == 1
        assert win.model.counts()[ComponentType.CONTROL] == 1
        assert len(win.panel.winfo_children()) > 0
    finally:
        root.destroy()


def test_select_shows_properties():
    win, root = _fresh()
    try:
        win.model.place(3, 3, ComponentType.FUEL, fuel="rbmk_fuel_ueu")
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
        win.model.place(5, 5, ComponentType.FUEL, fuel="rbmk_fuel_heu235")
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
        win.select_tool(ComponentType.FUEL.value)
        win.grid_editor._paint((2, 2))
        assert win.model.cell_at(2, 2).comp == ComponentType.FUEL
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
