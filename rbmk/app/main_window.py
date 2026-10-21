"""主窗口：装配 6 区域、运行循环、文件操作。"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

from rbmk import BUILD, __version__
from rbmk.app import theme
from rbmk.app import icons as icon_store
from rbmk.app.icons import get_icon
from rbmk.app.chart_panel import ChartPanel
from rbmk.app.grid_editor import GridEditor
from rbmk.model import save_load
from rbmk.model.components import (
    REASIM_CONTROL_COMPONENTS,
    CONTROL_POWER_BUFFER,
    CONTROL_POWER_CONSUMPTION,
    TURBINE_KINDS,
    TURBINE_NAMES_CN,
    turbine_capacity_he,
    turbines_needed,
    COMPONENT_INFO,
    CONTROL_GROUP_COLORS,
    CONTROL_GROUP_NAMES,
    CORE_COMPONENTS,
    FUELS,
    FUNCTION_NAMES_CN,
    HEAT_FLUIDS,
    NTYPE_NAMES_CN,
    STEAM_TYPES,
    Behavior,
    ComponentType,
    ControlGroup,
    behavior_of,
)
from rbmk.model.reactor import CONTROL_TYPES, FUEL_TYPES, ReactorModel
from rbmk.sim.engine import SimulationEngine
from rbmk.sim.risk import assess, format_duration

SPEEDS = [(0, "⏸"), (1, "1x"), (10, "10x"), (100, "100x"), (1000, "1000x")]
TOOLS = [("select", "选择"), ("erase", "擦除")]


SELF_IGNITE_SUFFIX = "（可自燃）"


def fuel_label(ft) -> str:
    """燃料类型显示名：自燃燃料（selfRate > 0）在名字后加（可自燃）。"""
    return f"{ft.name_cn}{SELF_IGNITE_SUFFIX}" if getattr(ft, "is_self_igniting", False) else ft.name_cn


def _btn(parent, text, cmd, kind="normal"):
    """原版风格按钮：灰石底、2px 凸起边框、白字，悬停变亮并转黄字。"""
    if kind == "primary":
        bg, hover = theme.BUTTON_PRIMARY, theme.BUTTON_PRIMARY_HOVER
    elif kind == "danger":
        bg, hover = theme.DANGER, "#c9433a"
    else:
        bg, hover = theme.BUTTON_BG, theme.BUTTON_BG_HOVER
    return tk.Button(parent, text=text, command=cmd, bg=bg, fg=theme.BUTTON_FG,
                     activebackground=hover, activeforeground=theme.BUTTON_FG_HOVER,
                     relief="raised", bd=2, overrelief="raised",
                     padx=8, pady=3, font=theme.FONT, cursor="hand2")


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title(f"RBMK 反应堆模拟器 — HBM 核科技 1.7.10   v{__version__}.{BUILD}")
        root.geometry("1280x840")
        root.configure(bg=theme.BG)
        root.minsize(1000, 700)

        self.model = ReactorModel(15, 15)
        self.engine = SimulationEngine(self.model)
        self.running = False
        self.speed = 1000
        self.selected_tool = ComponentType.RBMK_ROD.value
        self.default_fuel = "rbmk_fuel_heu235"
        self.selected_cell: tuple[int, int] | None = None
        self.tab = "prop"

        self._build()
        self._refresh_all()
        self._tick()

    # ---------------- UI 构建 ----------------
    def _build(self):
        self._build_toolbar()
        self._build_statusbar()

        bottom = tk.Frame(self.root, bg=theme.SURFACE, height=210, bd=2, relief="raised")
        bottom.pack(side="bottom", fill="x")
        bottom.pack_propagate(False)
        self.chart = ChartPanel(bottom, self)
        self.chart.pack(side="left", fill="both", expand=True)
        self.metrics = tk.Frame(bottom, bg=theme.SURFACE, width=430)
        self.metrics.pack(side="right", fill="y")
        self.metrics.pack_propagate(False)
        self._metric_labels = {}
        cols = 3
        for i, (key, title) in enumerate([
            ("temp", "反应堆平均温度"), ("surf", "燃料平均表面温度"),
            ("ctl", "控制棒平均插入深度"), ("steam", "蒸汽产量（mB/tick）"),
            ("power", "瞬时发电量"), ("total", "累计发电量"),
            ("fuel", "燃料平均寿命"), ("xenon", "氙中毒平均程度"),
            ("flux", "平均中子通量"),
        ]):
            box = tk.Frame(self.metrics, bg=theme.SURFACE2, bd=2, relief="sunken")
            box.grid(row=i // cols, column=i % cols, sticky="nsew", padx=3, pady=3)
            tk.Label(box, text=title, bg=theme.SURFACE2, fg=theme.MUTED,
                     font=theme.FONT_SMALL, anchor="w").pack(fill="x", padx=8, pady=(6, 0))
            val = tk.Label(box, text="—", bg=theme.SURFACE2, fg=theme.INK,
                           font=theme.FONT_BOLD, anchor="w")
            val.pack(fill="x", padx=8, pady=(0, 6))
            self._metric_labels[key] = val
        for _c in range(cols):
            self.metrics.grid_columnconfigure(_c, weight=1)

        body = tk.Frame(self.root, bg=theme.BG)
        body.pack(fill="both", expand=True)
        self._build_palette(body)
        self._build_inspector(body)
        self.grid_editor = GridEditor(body, self)
        self.grid_editor.pack(side="left", fill="both", expand=True)

    def _build_toolbar(self):
        bar = tk.Frame(self.root, bg=theme.SURFACE, height=48, bd=2, relief="raised")
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)
        for text, cmd in [("新建", self.new_model), ("打开", self.open_file),
                          ("保存", self.save_file), ("导出分享", self.export_file)]:
            _btn(bar, text, cmd).pack(side="left", padx=(8 if text == "新建" else 2, 0), pady=7)
        _btn(bar, "使用说明", self.show_guide).pack(side="left", padx=(4, 0), pady=7)
        tk.Frame(bar, bg=theme.BORDER, width=1).pack(side="left", fill="y", padx=8)
        self.run_btn = _btn(bar, "▶ 运行", self.toggle_run, "primary")
        self.run_btn.pack(side="left", pady=7)
        _btn(bar, "重置", self.reset_simulation).pack(side="left", padx=(4, 0), pady=7)
        self.boiler_btn = _btn(bar, "锅炉：普通", self.toggle_boiler_mode)
        self.boiler_btn.pack(side="left", padx=(4, 0), pady=7)
        self.speed_btns = {}
        grp = tk.Frame(bar, bg=theme.SURFACE)
        grp.pack(side="right", padx=10)
        tk.Label(grp, text="模拟速度", bg=theme.SURFACE, fg=theme.MUTED,
                 font=theme.FONT_SMALL).pack(side="left", padx=(0, 6))
        for s, label in SPEEDS:
            b = _btn(grp, label, lambda v=s: self.set_speed(v))
            b.configure(font=theme.FONT_SMALL, padx=6, pady=2)
            b.pack(side="left", padx=2, pady=7)
            self.speed_btns[s] = b
        # 自定义速度：输入任意正整数后回车或点「应用」
        tk.Label(grp, text="自定义", bg=theme.SURFACE, fg=theme.MUTED,
                 font=theme.FONT_SMALL).pack(side="left", padx=(8, 2))
        self.speed_var = tk.StringVar(value="")
        self.speed_entry = tk.Entry(grp, textvariable=self.speed_var, width=7, justify="right",
                                    bg=theme.SURFACE2, fg=theme.INK, relief="sunken", bd=2,
                                    insertbackground=theme.INK, font=theme.FONT_SMALL)
        self.speed_entry.pack(side="left", pady=7)
        self.speed_entry.bind("<Return>", lambda e: self.apply_custom_speed())
        _btn(grp, "应用", self.apply_custom_speed).pack(side="left", padx=(2, 0), pady=7)

    def _build_palette(self, parent):
        left = tk.Frame(parent, bg=theme.SURFACE, width=210, bd=2, relief="raised")
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        canvas = tk.Canvas(left, bg=theme.SURFACE, highlightthickness=0, width=196)
        vsb = tk.Scrollbar(left, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=theme.SURFACE)
        canvas.create_window((0, 0), window=inner, anchor="nw", width=196)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        self._palette_items = {}
        self._tool_items = {}
        self._add_palette_group(inner, "工具", [("select", "选择"), ("erase", "擦除")], is_tool=True)
        self._add_palette_group(inner, "反应堆组件", CORE_COMPONENTS)

    def _add_palette_group(self, parent, title, items, is_tool=False):
        tk.Label(parent, text=title, bg=theme.SURFACE, fg=theme.MUTED,
                 font=theme.FONT_SMALL, anchor="w").pack(fill="x", padx=8, pady=(10, 4))
        for item in items:
            if is_tool:
                key, name = item
                color = theme.ACCENT if key == "select" else theme.DANGER
                onclick = lambda e, k=key: self.select_tool(k)
            else:
                comp = item
                key = comp.value
                name, color = COMPONENT_INFO[comp]
                onclick = lambda e, c=comp: self.select_tool(c.value)
            row = tk.Frame(parent, bg=theme.SURFACE, cursor="hand2")
            row.pack(fill="x", padx=4, pady=1)
            icon = None if is_tool else get_icon(comp.value, 20)
            if icon is not None:
                sw = tk.Label(row, image=icon, bg=theme.SURFACE, bd=0)
            else:
                sw = tk.Frame(row, bg=color, width=12, height=12)
                sw.pack_propagate(False)
            sw.pack(side="left", padx=(4, 6))
            lab = tk.Label(row, text=name, bg=theme.SURFACE, fg=theme.INK,
                           font=(theme.FAMILY, 8), anchor="w")
            lab.pack(side="left", fill="x")
            for w in (row, sw, lab):
                w.bind("<Button-1>", onclick)
            if is_tool:
                self._tool_items[key] = row
            else:
                self._palette_items[key] = row

    def _build_inspector(self, parent):
        right = tk.Frame(parent, bg=theme.SURFACE, width=300, bd=2, relief="raised")
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        tabs = tk.Frame(right, bg=theme.SURFACE)
        tabs.pack(fill="x")
        self._tab_btns = {}
        for key, name in [("prop", "选中属性"), ("overview", "总览"),
                          ("control", "模拟控制"), ("risk", "风险预警")]:
            b = tk.Button(tabs, text=name, command=lambda k=key: self.set_tab(k),
                          bg=theme.BUTTON_BG, fg=theme.BUTTON_FG, relief="raised", bd=2,
                          padx=4, pady=5, font=theme.FONT_SMALL, cursor="hand2",
                          activebackground=theme.BUTTON_BG_HOVER,
                          activeforeground=theme.BUTTON_FG_HOVER)
            b.pack(side="left", expand=True, fill="x")
            self._tab_btns[key] = b
        self.panel = tk.Frame(right, bg=theme.SURFACE)
        self.panel.pack(fill="both", expand=True, padx=10, pady=8)

    def _build_statusbar(self):
        bar = tk.Frame(self.root, bg=theme.SURFACE, height=28, bd=2, relief="raised")
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)
        self.sb_speed = tk.Label(bar, text="速度 1000x", bg=theme.SURFACE, fg=theme.MUTED, font=theme.FONT_SMALL)
        self.sb_speed.pack(side="left", padx=10)
        self.sb_time = tk.Label(bar, text="已运行 00:00:00", bg=theme.SURFACE, fg=theme.MUTED, font=theme.FONT_SMALL)
        self.sb_time.pack(side="left", padx=10)
        self.sb_state = tk.Label(bar, text="正常运行", bg=theme.SURFACE, fg=theme.OK, font=theme.FONT_SMALL)
        self.sb_state.pack(side="left", padx=10)
        self.sb_safety = tk.Label(bar, text="预计安全运行时长 稳定（无熔毁风险）",
                                  bg=theme.SURFACE, fg=theme.MUTED, font=theme.FONT_SMALL)
        self.sb_safety.pack(side="right", padx=10)

    # ---------------- 交互 ----------------
    def select_tool(self, key: str):
        self.selected_tool = key
        self._paint_palette()
        if key != "select":
            self.selected_cell = None
            self.grid_editor.selected = None
        self.grid_editor.redraw()
        self.render_panel()

    def _paint_palette(self):
        for key, row in self._palette_items.items():
            row.configure(bg=theme.SURFACE2 if key == self.selected_tool else theme.SURFACE)
        for key, row in self._tool_items.items():
            row.configure(bg=theme.SURFACE2 if key == self.selected_tool else theme.SURFACE)

    def on_select(self, rc):
        self.selected_cell = rc
        self.tab = "prop"
        self._sync_tab_buttons()
        self.render_panel()

    def on_model_changed(self):
        self.engine.state.melt_temp = self.engine._melt_threshold()
        self.render_panel()

    def set_tab(self, key):
        self.tab = key
        self._sync_tab_buttons()
        self.render_panel()

    def _sync_tab_buttons(self):
        for key, b in self._tab_btns.items():
            b.configure(relief="sunken" if key == self.tab else "raised",
                        bg=theme.SURFACE2 if key == self.tab else theme.BUTTON_BG,
                        fg=theme.INK if key == self.tab else theme.BUTTON_FG)

    def set_speed(self, s):
        self.speed = s
        entry = getattr(self, "speed_entry", None)
        if entry is not None and entry.winfo_exists() and (self.speed_var.get() or "").strip() != str(s):
            self.speed_var.set(str(s))
        for k, b in self.speed_btns.items():
            b.configure(bg=theme.BUTTON_PRIMARY if k == s else theme.BUTTON_BG,
                        fg=theme.BUTTON_FG, relief="sunken" if k == s else "raised")

    def show_guide(self):
        """弹出《快速上手》使用说明。"""
        from rbmk.app.guide import GuideWindow

        win = getattr(self, "_guide_win", None)
        if win is not None and win.winfo_exists():
            win.deiconify()
            win.lift()
            win.focus_force()
            return
        self._guide_win = GuideWindow(self.root)

    def apply_custom_speed(self):
        """应用输入框里的自定义模拟速度（正整数，上限 1,000,000x）。"""
        raw = (self.speed_var.get() or "").strip().lower().rstrip("x").strip()
        try:
            value = int(float(raw))
        except (TypeError, ValueError):
            self._flag_speed_error()
            return
        value = max(1, min(1_000_000, value))
        self.speed_var.set(str(value))
        self.set_speed(value)

    def _flag_speed_error(self):
        """输入非法时把输入框短暂标红。"""
        entry = getattr(self, "speed_entry", None)
        if entry is None:
            return
        entry.configure(bg="#ffd0d0")
        self.root.after(900, lambda: entry.winfo_exists() and entry.configure(bg=theme.SURFACE2))

    def toggle_run(self):
        self.running = not self.running
        self.run_btn.configure(text="⏸ 暂停" if self.running else "▶ 运行",
                               bg=theme.DANGER if self.running else theme.BUTTON_PRIMARY,
                               fg=theme.BUTTON_FG)

    def reset_simulation(self):
        """暂停并重置反应堆状态，保留已摆放的组件。"""
        self.running = False
        self.run_btn.configure(text="▶ 运行", bg=theme.BUTTON_PRIMARY, fg=theme.BUTTON_FG)
        self.engine.reset()
        self.chart.reset()
        self.grid_editor.redraw()
        self._refresh_state()
        self.render_panel()

    def toggle_boiler_mode(self):
        """切换普通锅炉 / ReaSim 锅炉模式。"""
        self.model.reasim_boilers = not self.model.reasim_boilers
        self._sync_boiler_btn()
        self.render_panel()

    def _sync_boiler_btn(self):
        if getattr(self, "boiler_btn", None) is not None:
            self.boiler_btn.configure(
                text="锅炉：ReaSim" if self.model.reasim_boilers else "锅炉：普通")

    # ---------------- 循环 ----------------
    def _tick(self):
        if self.running and self.speed > 0 and not self.engine.state.melted:
            self.engine.advance(0.1 * self.speed)
            self.chart.push(self.engine.state)
            self.grid_editor.redraw()
        self._refresh_state()
        self.grid_editor.refresh_tip()
        if self.tab == "risk":
            self.render_panel()
        elif self.tab == "prop":
            self._refresh_prop_values()
        elif self.tab == "overview":
            self._refresh_turbine_values()
        self.root.after(100, self._tick)

    def _refresh_state(self):
        s = self.engine.state
        self.sb_speed.configure(text=f"速度 {self.speed}x" if self.speed else "速度 暂停")
        self.sb_time.configure(text="已运行 " + _fmt(s.time))
        level_color = {"normal": theme.OK, "warning": theme.ACCENT,
                       "danger": theme.DANGER, "meltdown": theme.DANGER}[s.status]
        level_text = {"normal": "正常运行", "warning": "警告 · 温度偏高",
                      "danger": "危险 · 接近熔毁", "meltdown": "已熔毁"}[s.status]
        self.sb_state.configure(text=level_text, fg=level_color)
        r = assess(self.engine)
        self.sb_safety.configure(text="预计安全运行时长 " + format_duration(r.time_to_meltdown))
        fuels = [c for _, _, c in self.model.iter_cells()
                 if behavior_of(c.comp) == Behavior.FUEL and c.fuel_type is not None]
        surface = sum(c.hull_heat for c in fuels) / len(fuels) if fuels else 0.0
        controls = [c for _, _, c in self.model.iter_cells()
                    if behavior_of(c.comp) == Behavior.CONTROL]
        if controls:
            insertions = []
            for c in controls:
                if c.comp in (ComponentType.RBMK_CONTROL_AUTO, ComponentType.RBMK_CONTROL_REASIM_AUTO):
                    insertions.append(100.0 * (1.0 - c.level))
                else:
                    insertions.append(self.model.effective_insertion(c))
            ctl_avg = sum(insertions) / len(insertions)
        else:
            ctl_avg = 0.0
        self._metric_labels["temp"].configure(text=f"{s.avg_temperature:.0f} °C")
        self._metric_labels["surf"].configure(text=f"{surface:.0f} °C")
        self._metric_labels["ctl"].configure(text=f"{ctl_avg:.0f}%")
        self._metric_labels["steam"].configure(text=f"{s.steam / 20.0:,.0f} mB/tick")
        self._metric_labels["power"].configure(text=f"{s.electricity:,.0f} HE/tick")
        self._metric_labels["total"].configure(text=f"{s.total_energy:,.0f} HE")
        self._metric_labels["fuel"].configure(text=f"{s.fuel_remaining:.1f}%")
        self._metric_labels["xenon"].configure(text=f"{s.xenon:.1f}%")
        self._metric_labels["flux"].configure(text=f"{s.avg_flux:.2f}")

    def _refresh_all(self):
        self._paint_palette()
        self.set_speed(self.speed)
        self._sync_tab_buttons()
        self.render_panel()

    # ---------------- 面板 ----------------
    def render_panel(self):
        for w in self.panel.winfo_children():
            w.destroy()
        if self.tab == "prop":
            self._render_prop()
        elif self.tab == "overview":
            self._render_overview()
        elif self.tab == "control":
            self._render_control()
        else:
            self._render_risk()

    def _render_prop(self):
        p = self.panel
        self._prop_labels = {}
        if not self.selected_cell or self.model.cell_at(*self.selected_cell) is None:
            tk.Label(p, text="未选中任何柱子。\n点击网格里的柱子查看属性。",
                     bg=theme.SURFACE, fg=theme.MUTED, font=theme.FONT_SMALL,
                     justify="left", anchor="w").pack(fill="x", pady=10)
            return
        r, c = self.selected_cell
        cell = self.model.cell_at(r, c)
        name, color = COMPONENT_INFO[cell.comp]
        beh = behavior_of(cell.comp)

        head = tk.Frame(p, bg=theme.SURFACE)
        head.pack(fill="x", pady=(0, 6))
        tk.Frame(head, bg=color, width=12, height=12).pack(side="left", padx=(0, 6))
        tk.Label(head, text=name, bg=theme.SURFACE, fg=theme.INK,
                 font=theme.FONT_BOLD).pack(side="left")
        if beh == Behavior.FUEL and cell.fuel_type and cell.fuel_type.is_self_igniting:
            tk.Label(head, text="自燃", bg=theme.GOLD, fg="#ffffff",
                     font=(theme.FAMILY, 7, "bold"), padx=4).pack(side="left", padx=(6, 0))
        tk.Label(head, text=f"{r+1}行 {c+1}列", bg=theme.SURFACE, fg=theme.MUTED,
                 font=(theme.FAMILY, 8)).pack(side="right")

        if beh == Behavior.FUEL:
            tk.Label(p, text="燃料类型", bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.FONT_SMALL, anchor="w").pack(fill="x", pady=(2, 2))
            var = tk.StringVar(value=fuel_label(FUELS[cell.fuel]) if cell.fuel else "空燃料棒")
            om = tk.OptionMenu(p, var, *[fuel_label(f) for f in FUELS.values()],
                               command=lambda v: self._set_fuel(cell, v))
            om.configure(bg=theme.SURFACE2, fg=theme.INK, activebackground=theme.BORDER,
                         highlightthickness=0, font=theme.FONT_SMALL, anchor="w")
            om.pack(fill="x")
        elif beh == Behavior.CONTROL and cell.comp == ComponentType.RBMK_CONTROL_AUTO:
            self._auto_control_ui(p, cell)
        elif beh == Behavior.CONTROL:
            tk.Label(p, text="控制组", bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.FONT_SMALL, anchor="w").pack(fill="x", pady=(2, 2))
            gname = CONTROL_GROUP_NAMES[cell.group] if cell.group is not None else "空置"
            gvar = tk.StringVar(value=gname)
            om = tk.OptionMenu(p, gvar, *(["空置"] + [CONTROL_GROUP_NAMES[g] for g in ControlGroup]),
                               command=lambda v: self._set_group(cell, v))
            om.configure(bg=theme.SURFACE2, fg=theme.INK, activebackground=theme.BORDER,
                         highlightthickness=0, font=theme.FONT_SMALL, anchor="w")
            om.pack(fill="x")
            tk.Label(p, text="单根插入深度（拖动覆盖）", bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.FONT_SMALL, anchor="w").pack(fill="x", pady=(6, 2))
            sc = tk.Scale(p, from_=0, to=100, orient="horizontal", showvalue=False,
                          bg=theme.SURFACE, fg=theme.INK, troughcolor=theme.BORDER,
                          highlightthickness=0)
            # 先 set 再挂 command：避免建面板时把当前值写成"单根覆盖"
            sc.set(self.model.effective_insertion(cell))
            sc.configure(command=lambda v: self._set_single(cell, v))
            sc.pack(fill="x")
            if cell.insertion is not None:
                _btn(p, "清除单根覆盖（跟随分组/全局）",
                     lambda c=cell: self._clear_single(c)).pack(fill="x", pady=(6, 0))
        elif beh == Behavior.BOILER:
            tk.Label(p, text="蒸汽类型", bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.FONT_SMALL, anchor="w").pack(fill="x", pady=(2, 2))
            svar = tk.StringVar(value=STEAM_TYPES.get(cell.steam_type, STEAM_TYPES["STEAM"]).name_cn)
            om = tk.OptionMenu(p, svar, *[st.name_cn for st in STEAM_TYPES.values()],
                               command=lambda v: self._set_steam_type(cell, v))
            om.configure(bg=theme.SURFACE2, fg=theme.INK, activebackground=theme.BORDER,
                         highlightthickness=0, font=theme.FONT_SMALL, anchor="w")
            om.pack(fill="x")
        elif beh == Behavior.HEATER:
            tk.Label(p, text="流体类型", bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.FONT_SMALL, anchor="w").pack(fill="x", pady=(2, 2))
            hvar = tk.StringVar(value=HEAT_FLUIDS.get(cell.heater_fluid, HEAT_FLUIDS["COOLANT"]).name_cn)
            om = tk.OptionMenu(p, hvar, *[hf.name_cn for hf in HEAT_FLUIDS.values()],
                               command=lambda v: self._set_heater_fluid(cell, v))
            om.configure(bg=theme.SURFACE2, fg=theme.INK, activebackground=theme.BORDER,
                         highlightthickness=0, font=theme.FONT_SMALL, anchor="w")
            om.pack(fill="x")

        self._prop_row("柱温", "temp")
        if beh == Behavior.FUEL:
            self._prop_row("芯温", "core")
            self._prop_row("壳温", "hull")
        self._prop_row("被动冷却", "cooling")
        if beh == Behavior.FUEL:
            self._prop_row("接收通量", "flux")
            self._prop_row("快中子计数", "fast")
            self._prop_row("慢中子计数", "slow")
            self._prop_row("快中子占比", "ratio")
            self._prop_row("本柱输出通量", "outflux")
            self._prop_row("氙毒", "xenon")
            self._prop_row("剩余寿命", "life")
            self._prop_row("燃料熔点", "melt")
            self._prop_row("燃烧函数", "function")
            self._prop_row("自发射率", "selfrate")
            self._prop_row("裂变所需中子类型", "ntype_in")
            self._prop_row("裂变产生中子类型", "ntype_out")
        if beh == Behavior.CONTROL:
            auto = cell.comp in (ComponentType.RBMK_CONTROL_AUTO, ComponentType.RBMK_CONTROL_REASIM_AUTO)
            self._prop_row("当前插入度" if auto else "插入深度", "level")
            if cell.comp in REASIM_CONTROL_COMPONENTS:
                self._prop_row("供电需求（移动时）", "power_need")
                self._prop_row("能量缓冲", "power_buffer")
        if beh == Behavior.BOILER:
            self._prop_row("每刻蒸汽产生量", "steam")
        if self.model.reasim_boilers:
            self._prop_row("每刻 ReaSim 蒸汽产量（超热蒸汽）", "reasim_steam")
        if beh == Behavior.COOLER:
            self._prop_row("每刻消耗冷四氟甲烷", "cooler_use")
            self._prop_row("作用柱数（5×5）", "cooler_cells")
        if beh == Behavior.HEATER:
            self._prop_row("每刻加热流体产量", "heater")
            self._prop_row("每刻热量产出", "heater_heat")
        self._refresh_prop_values()

    def _prop_row(self, label, key):
        row = tk.Frame(self.panel, bg=theme.SURFACE)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=label, bg=theme.SURFACE, fg=theme.MUTED,
                 font=(theme.FAMILY, 8), anchor="w").pack(side="left")
        val = tk.Label(row, text="—", bg=theme.SURFACE, fg=theme.INK,
                       font=(theme.FAMILY, 8, "bold"), anchor="e")
        val.pack(side="right")
        self._prop_labels[key] = val

    def _refresh_prop_values(self):
        labels = getattr(self, "_prop_labels", None)
        if not labels or not self.selected_cell:
            return
        cell = self.model.cell_at(*self.selected_cell)
        if cell is None:
            return
        r, c = self.selected_cell
        fq = cell.flux_q
        fast = fq * cell.flux_ratio
        slow = fq * (1.0 - cell.flux_ratio)
        n = sum(1 for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0))
                if self.model.cell_at(r + dr, c + dc) is not None)
        cooling = 0.1 + (2.5 - 0.1) * ((4 - min(max(n, 0), 4)) / 4.0)
        vals = {
            "temp": f"{cell.shown_temp:.1f} °C",
            "core": f"{cell.core_heat:.1f} °C",
            "hull": f"{cell.hull_heat:.1f} °C",
            "cooling": f"{cooling:.2f}/tick",
            "flux": f"{fq:.2f}",
            "fast": f"{fast:.2f}",
            "slow": f"{slow:.2f}",
            "ratio": f"{cell.flux_ratio * 100:.1f}%",
            "outflux": f"{cell.flux:.2f}",
        }
        ft = cell.fuel_type
        if ft:
            vals.update({
                "burnup": f"{cell.burnup * 100:.3f}%",
                "xenon": f"{cell.xenon:.2f}",
                "life": f"{(1 - cell.burnup) * 100:.3f}%",
                "melt": f"{ft.melting_point:.0f} °C",
                "function": FUNCTION_NAMES_CN.get(ft.function, ft.function),
                "selfrate": f"{ft.self_rate:g}/tick",
                "ntype_in": NTYPE_NAMES_CN.get(ft.n_type.value, ft.n_type.value),
                "ntype_out": NTYPE_NAMES_CN.get(ft.r_type.value, ft.r_type.value),
            })
        if behavior_of(cell.comp) == Behavior.CONTROL:
            if cell.comp in (ComponentType.RBMK_CONTROL_AUTO, ComponentType.RBMK_CONTROL_REASIM_AUTO):
                cur = (1.0 - cell.level) * 100.0
                tgt = (1.0 - cell.target_level) * 100.0
                vals["level"] = f"{cur:.0f}%（目标 {tgt:.0f}%）"
            else:
                vals["level"] = f"{self.model.effective_insertion(cell):.0f}%"
        if cell.comp in REASIM_CONTROL_COMPONENTS:
            vals["power_need"] = f"{CONTROL_POWER_CONSUMPTION:,} HE/tick"
            vals["power_buffer"] = f"{CONTROL_POWER_BUFFER:,} HE"
        if behavior_of(cell.comp) == Behavior.BOILER:
            vals["steam"] = f"{cell.steam_rate:.0f} mB/tick"
        if self.model.reasim_boilers:
            vals["reasim_steam"] = f"{cell.reasim_steam_rate:.0f} mB/tick"
        if behavior_of(cell.comp) == Behavior.COOLER:
            vals["cooler_use"] = f"{cell.cooler_rate:.0f} mB/tick"
            vals["cooler_cells"] = str(cell.cooler_cells)
        if self.model.reasim_boilers:
            vals["reasim_steam"] = f"{cell.reasim_steam_rate:.0f} mB/tick"
        if behavior_of(cell.comp) == Behavior.COOLER:
            vals["cooler_use"] = f"{cell.cooler_rate:.0f} mB/tick"
            vals["cooler_cells"] = str(cell.cooler_cells)
        if behavior_of(cell.comp) == Behavior.HEATER:
            vals["heater"] = f"{cell.heater_rate:.0f} mB/tick"
            vals["heater_heat"] = f"{cell.heater_heat:.0f} TU/tick"
        for k, v in vals.items():
            if k in labels:
                labels[k].configure(text=v)

    def _render_overview(self):
        p = self.panel
        counts = self.model.counts()
        tk.Label(p, text=f"网格 {self.model.cols}×{self.model.rows}", bg=theme.SURFACE,
                 fg=theme.MUTED, font=theme.FONT_SMALL, anchor="w").pack(fill="x", pady=(0, 6))
        grid = tk.Frame(p, bg=theme.SURFACE)
        grid.pack(fill="x")
        items = [(comp, n) for comp, n in counts.items() if n > 0]
        for i, (comp, n) in enumerate(items):
            name, color = COMPONENT_INFO[comp]
            box = tk.Frame(grid, bg=theme.SURFACE2)
            box.grid(row=i // 2, column=i % 2, sticky="nsew", padx=3, pady=3)
            tk.Frame(box, bg=color, width=8, height=8).pack(side="left", padx=(6, 4))
            tk.Label(box, text=name, bg=theme.SURFACE2, fg=theme.MUTED,
                     font=theme.FONT_SMALL).pack(side="left")
            tk.Label(box, text=str(n), bg=theme.SURFACE2, fg=theme.INK,
                     font=theme.FONT_BOLD).pack(side="right", padx=6)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        tk.Label(p, text=f"燃料棒 {self.model.fuel_count()} 根", bg=theme.SURFACE,
                 fg=theme.INK, font=theme.FONT_SMALL, anchor="w").pack(fill="x", pady=(10, 0))

        # 一键统一所有蒸汽管道的蒸汽类型
        tk.Label(p, text="全部蒸汽管道蒸汽类型", bg=theme.SURFACE, fg=theme.MUTED,
                 font=theme.FONT_SMALL, anchor="w").pack(fill="x", pady=(10, 2))
        types = {cell.steam_type for _, _, cell in self.model.iter_cells()
                 if behavior_of(cell.comp) == Behavior.BOILER}
        if len(types) == 1:
            cur = STEAM_TYPES.get(next(iter(types)), STEAM_TYPES["STEAM"]).name_cn
        elif types:
            cur = "多种（选择以统一）"
        else:
            cur = STEAM_TYPES["STEAM"].name_cn
        svar = tk.StringVar(value=cur)
        om = tk.OptionMenu(p, svar, *[st.name_cn for st in STEAM_TYPES.values()],
                           command=self._set_all_steam_types)
        om.configure(bg=theme.SURFACE2, fg=theme.INK, activebackground=theme.BORDER,
                     highlightthickness=0, font=theme.FONT_SMALL, anchor="w")
        om.pack(fill="x")

        # 一键统一所有流体加热器的流体类型
        tk.Label(p, text="全部流体加热器流体类型", bg=theme.SURFACE, fg=theme.MUTED,
                 font=theme.FONT_SMALL, anchor="w").pack(fill="x", pady=(10, 2))
        htypes = {cell.heater_fluid for _, _, cell in self.model.iter_cells()
                  if behavior_of(cell.comp) == Behavior.HEATER}
        if len(htypes) == 1:
            hcur = HEAT_FLUIDS.get(next(iter(htypes)), HEAT_FLUIDS["COOLANT"]).name_cn
        elif htypes:
            hcur = "多种（选择以统一）"
        else:
            hcur = HEAT_FLUIDS["COOLANT"].name_cn
        hvar = tk.StringVar(value=hcur)
        hom = tk.OptionMenu(p, hvar, *[hf.name_cn for hf in HEAT_FLUIDS.values()],
                            command=self._set_all_heater_fluids)
        hom.configure(bg=theme.SURFACE2, fg=theme.INK, activebackground=theme.BORDER,
                      highlightthickness=0, font=theme.FONT_SMALL, anchor="w")
        hom.pack(fill="x")

        # 汽轮机配置：按蒸汽降温阶段分别选择汽轮机，并给出所需台数
        tk.Label(p, text="汽轮机配置（按蒸汽降温阶段）", bg=theme.SURFACE, fg=theme.INK,
                 font=theme.FONT_BOLD, anchor="w").pack(fill="x", pady=(14, 2))
        self._turbine_labels = {}
        for key, stype in STEAM_TYPES.items():
            row = tk.Frame(p, bg=theme.SURFACE)
            row.pack(fill="x", pady=(4, 0))
            tk.Label(row, text=stype.name_cn, bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.FONT_SMALL, width=10, anchor="w").pack(side="left", padx=(0, 4))
            var = tk.StringVar(value=TURBINE_NAMES_CN[self.model.turbine_of(key)])
            om = tk.OptionMenu(row, var, *[TURBINE_NAMES_CN[k] for k in TURBINE_KINDS],
                               command=lambda v, k=key: self._set_turbine(k, v))
            om.configure(bg=theme.SURFACE2, fg=theme.INK, activebackground=theme.BORDER,
                         highlightthickness=0, font=theme.FONT_SMALL, anchor="w")
            om.pack(side="left", fill="x", expand=True)
            lab = tk.Label(p, text="—", bg=theme.SURFACE, fg=theme.INK,
                           font=theme.FONT_SMALL, anchor="w")
            lab.pack(fill="x", padx=(2, 0))
            self._turbine_labels[key] = lab
        self._refresh_turbine_values()

    def _set_turbine(self, steam_key: str, name: str):
        """切换某蒸汽阶段使用的汽轮机（影响瞬时发电量）。"""
        for kind, cn in TURBINE_NAMES_CN.items():
            if cn == name:
                self.model.set_turbine(steam_key, kind)
                break
        self._refresh_turbine_values()
        self._refresh_state()

    def _refresh_turbine_values(self):
        labels = getattr(self, "_turbine_labels", {})
        if not labels:
            return
        st = self.engine.state
        for key, lab in labels.items():
            stype = STEAM_TYPES[key]
            mb = st.steam_by_type.get(key, 0.0)
            he = mb * stype.he_per_mb
            kind = self.model.turbine_of(key)
            cap = turbine_capacity_he(kind, stype.he_per_mb)
            need = turbines_needed(kind, he, stype.he_per_mb)
            lab.configure(text=(f"{mb:,.0f} mB/tick → {he:,.0f} HE/tick" + "\n"
                                f"需要 {need} 台（单台上限 {cap:,.0f} HE/tick）"))

    def _render_control(self):
        p = self.panel
        self._lbl_global = tk.Label(p, text=f"全局插入深度 {self.model.global_insertion:.0f}%",
                 bg=theme.SURFACE, fg=theme.MUTED, font=theme.FONT_SMALL, anchor="w")
        self._lbl_global.pack(fill="x")
        sc = tk.Scale(p, from_=0, to=100, orient="horizontal", showvalue=False,
                      bg=theme.SURFACE, fg=theme.INK, troughcolor=theme.BORDER,
                      highlightthickness=0)
        sc.set(self.model.global_insertion)
        sc.configure(command=self._set_global)   # set() 会触发 command，必须放到 set 之后
        sc.pack(fill="x", pady=(0, 10))
        tk.Label(p, text="分组插入深度（拖动即覆盖该组）", bg=theme.SURFACE,
                 fg=theme.MUTED, font=theme.FONT_SMALL, anchor="w").pack(fill="x")
        for g in ControlGroup:
            row = tk.Frame(p, bg=theme.SURFACE)
            row.pack(fill="x", pady=1)
            tk.Frame(row, bg=CONTROL_GROUP_COLORS[g], width=10, height=10).pack(side="left")
            tk.Label(row, text=CONTROL_GROUP_NAMES[g], bg=theme.SURFACE, fg=theme.INK,
                     font=theme.FONT_SMALL).pack(side="left", padx=6)
            cur = self.model.group_insertion.get(g.value)
            scg = tk.Scale(row, from_=0, to=100, orient="horizontal", showvalue=False,
                           bg=theme.SURFACE, fg=theme.INK, troughcolor=theme.BORDER,
                           highlightthickness=0)
            scg.set(cur if cur is not None else self.model.global_insertion)
            scg.configure(command=lambda v, gg=g: self._set_group_val(gg, v))
            scg.pack(side="left", fill="x", expand=True)
        _btn(p, "重置分组覆盖", self._reset_groups).pack(fill="x", pady=(8, 0))

    def _render_risk(self):
        p = self.panel
        s = self.engine.state
        r = assess(self.engine)
        colors = {"normal": theme.OK, "warning": theme.ACCENT,
                  "danger": theme.DANGER, "meltdown": theme.DANGER}
        texts = {"normal": "正常", "warning": "警告", "danger": "危险", "meltdown": "熔毁"}
        tk.Label(p, text=texts[r.level], bg=theme.SURFACE, fg=colors[r.level],
                 font=theme.FONT_TITLE, anchor="w").pack(fill="x", pady=(0, 4))
        tk.Label(p, text=r.message, bg=theme.SURFACE, fg=theme.MUTED,
                 font=theme.FONT_SMALL, wraplength=260, justify="left", anchor="w").pack(fill="x")
        for label, val in [
            ("堆芯温度", f"{s.temperature:.0f} °C"),
            ("柱温上限", f"{r.melt_temp:.0f} °C"),
            ("温度占比", f"{r.ratio*100:.0f}%"),
            ("预计安全运行时长", format_duration(r.time_to_meltdown)),
        ]:
            row = tk.Frame(p, bg=theme.SURFACE)
            row.pack(fill="x", pady=5)
            tk.Label(row, text=label, bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.FONT_SMALL).pack(side="left")
            tk.Label(row, text=val, bg=theme.SURFACE, fg=theme.INK,
                     font=theme.FONT_BOLD).pack(side="right")

    # ---------------- 设置回调 ----------------
    def _set_fuel(self, cell, name):
        for ft in FUELS.values():
            # 兼容带「（可自燃）」后缀的显示名与不带后缀的原始译名
            if name in (fuel_label(ft), ft.name_cn):
                cell.fuel = ft.key
                break
        cell.has_rod = cell.fuel_type is not None and cell.fuel != "rbmk_fuel_empty"
        self.engine.state.melt_temp = self.engine._melt_threshold()
        self._refresh_prop_values()
        self.grid_editor.redraw()

    AUTO_FUNC_NAMES = {"LINEAR": "线性", "QUAD_UP": "上凸平方", "QUAD_DOWN": "下凹平方"}

    def _auto_control_ui(self, p, cell):
        """自动控制棒参数（TileEntityRBMKControlAuto）：温度区间 -> 插入度区间。"""
        tk.Label(p, text="控制函数", bg=theme.SURFACE, fg=theme.MUTED,
                 font=theme.FONT_SMALL, anchor="w").pack(fill="x", pady=(2, 2))
        var = tk.StringVar(value=self.AUTO_FUNC_NAMES.get(cell.auto_func, "线性"))
        om = tk.OptionMenu(p, var, *self.AUTO_FUNC_NAMES.values(),
                           command=lambda v: self._set_auto_func(cell, v))
        om.configure(bg=theme.SURFACE2, fg=theme.INK, activebackground=theme.BORDER,
                     highlightthickness=0, font=theme.FONT_SMALL, anchor="w")
        om.pack(fill="x")
        for label, attr, lo, hi in (
            ("温度下限（°C）", "heat_lower", 0, 1500),
            ("温度上限（°C）", "heat_upper", 0, 1500),
            ("温度下限对应插入度（%）", "level_lower", 0, 100),
            ("温度上限对应插入度（%）", "level_upper", 0, 100),
        ):
            tk.Label(p, text=label, bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.FONT_SMALL, anchor="w").pack(fill="x", pady=(6, 0))
            row = tk.Frame(p, bg=theme.SURFACE)
            row.pack(fill="x")
            ent = tk.Entry(row, width=7, bg=theme.SURFACE2, fg=theme.INK, bd=0,
                           insertbackground=theme.INK, font=theme.FONT_SMALL,
                           justify="right", highlightthickness=1,
                           highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT)
            ent.pack(side="right", padx=(6, 0), ipady=2)
            ent.insert(0, self._fmt_num(getattr(cell, attr)))
            sc = tk.Scale(row, from_=lo, to=hi, orient="horizontal", showvalue=False, resolution=1,
                          bg=theme.SURFACE, fg=theme.INK, troughcolor=theme.BORDER,
                          highlightthickness=0, font=theme.FONT_SMALL,
                          command=lambda v, a=attr, e=ent: self._auto_slider_moved(cell, a, v, e))
            sc.set(getattr(cell, attr))
            sc.pack(side="left", fill="x", expand=True)
            ent.bind("<Return>", lambda ev, a=attr, e=ent, sc=sc: self._auto_entry_applied(cell, a, e, sc))
            ent.bind("<FocusOut>", lambda ev, a=attr, e=ent, sc=sc: self._auto_entry_applied(cell, a, e, sc))
            ent._auto_scale = sc

    AUTO_PARAM_RANGES = {
        "heat_lower": (0.0, 1500.0),
        "heat_upper": (0.0, 1500.0),
        "level_lower": (0.0, 100.0),
        "level_upper": (0.0, 100.0),
    }

    @staticmethod
    def _fmt_num(v) -> str:
        return f"{float(v):g}"

    def _auto_slider_moved(self, cell, attr, value, entry=None):
        setattr(cell, attr, float(value))
        if entry is not None:
            entry.delete(0, "end")
            entry.insert(0, self._fmt_num(value))
        self._refresh_prop_values()
        self.grid_editor.redraw()

    def _auto_entry_applied(self, cell, attr, entry, scale):
        """手动输入数值：回车或失焦时生效，超范围会夹到区间内，非法输入恢复原值。"""
        text = entry.get().strip()
        lo, hi = self.AUTO_PARAM_RANGES.get(attr, (0.0, 1500.0))
        try:
            v = float(text)
        except ValueError:
            v = float(getattr(cell, attr))
        v = max(lo, min(hi, v))
        setattr(cell, attr, v)
        entry.delete(0, "end")
        entry.insert(0, self._fmt_num(v))
        scale.set(v)
        self._refresh_prop_values()
        self.grid_editor.redraw()

    def _set_auto_param(self, cell, attr, value):
        self._auto_slider_moved(cell, attr, value)

    def _set_auto_func(self, cell, name):
        rev = {v: k for k, v in self.AUTO_FUNC_NAMES.items()}
        cell.auto_func = rev.get(name, "LINEAR")
        self._refresh_prop_values()
        self.grid_editor.redraw()

    def _set_group(self, cell, name):
        if name == "空置":
            cell.group = None
        else:
            for g in ControlGroup:
                if CONTROL_GROUP_NAMES[g] == name:
                    cell.group = g
                    break
        self._refresh_prop_values()
        self.grid_editor.redraw()

    def _set_steam_type(self, cell, name):
        for st in STEAM_TYPES.values():
            if st.name_cn == name:
                cell.steam_type = st.key
                break
        self._refresh_prop_values()
        self.grid_editor.redraw()

    def _set_heater_fluid(self, cell, name):
        for hf in HEAT_FLUIDS.values():
            if hf.name_cn == name:
                cell.heater_fluid = hf.key
                break
        self._refresh_prop_values()

    def _set_single(self, cell, v):
        self.model.touch_single(cell, float(v))
        self.grid_editor.redraw()

    def _clear_single(self, cell):
        """取消单根覆盖，重新跟随分组/全局设定。"""
        self.model.clear_single(cell)
        self.render_panel()
        self.grid_editor.redraw()

    def _set_global(self, v):
        self.model.touch_global(float(v))
        if getattr(self, "_lbl_global", None) is not None:
            self._lbl_global.configure(text=f"全局插入深度 {self.model.global_insertion:.0f}%")
        self.grid_editor.redraw()

    def _set_all_steam_types(self, name):
        for st in STEAM_TYPES.values():
            if st.name_cn == name:
                for _, _, cell in self.model.iter_cells():
                    if behavior_of(cell.comp) == Behavior.BOILER:
                        cell.steam_type = st.key
                break
        self.render_panel()

    def _set_all_heater_fluids(self, name):
        for hf in HEAT_FLUIDS.values():
            if hf.name_cn == name:
                for _, _, cell in self.model.iter_cells():
                    if behavior_of(cell.comp) == Behavior.HEATER:
                        cell.heater_fluid = hf.key
                break
        self.render_panel()

    def _set_group_val(self, group, v):
        self.model.touch_group(group, float(v))
        self.grid_editor.redraw()

    def _reset_groups(self):
        self.model.group_insertion.clear()
        self.render_panel()

    # ---------------- 文件 ----------------
    def new_model(self):
        self.model = ReactorModel(15, 15)
        self.engine = SimulationEngine(self.model)
        self.chart.reset()
        self.selected_cell = None
        self.grid_editor.selected = None
        self.grid_editor.redraw()
        self._refresh_all()

    def open_file(self):
        path = filedialog.askopenfilename(
            title="打开设计", filetypes=[("RBMK 设计", "*.json"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            self.model = save_load.load(path)
        except Exception as e:
            messagebox.showerror("打开失败", str(e))
            return
        self.engine = SimulationEngine(self.model)
        self.chart.reset()
        self.selected_cell = None
        self.grid_editor.selected = None
        self.grid_editor.redraw()
        self._refresh_all()
        self._sync_boiler_btn()

    def save_file(self):
        path = filedialog.asksaveasfilename(
            title="保存设计", defaultextension=".json",
            filetypes=[("RBMK 设计", "*.json")])
        if not path:
            return
        try:
            save_load.save(self.model, path)
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def export_file(self):
        path = filedialog.asksaveasfilename(
            title="导出分享文件", defaultextension=".rbmk.json",
            filetypes=[("RBMK 分享文件", "*.rbmk.json"), ("JSON", "*.json")])
        if not path:
            return
        try:
            save_load.export(self.model, path)
            messagebox.showinfo("导出成功", "已导出，可发给其他玩家用本软件导入。")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))


def _fmt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def create_app():
    root = tk.Tk()
    # PhotoImage 绑定到具体的 Tk 解释器，换窗口（含测试里反复建/销毁）必须先清缓存
    icon_store.clear_cache()
    return MainWindow(root), root
