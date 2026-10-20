"""主窗口：装配 6 区域、运行循环、文件操作。"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

from rbmk.app import theme
from rbmk.app.chart_panel import ChartPanel
from rbmk.app.grid_editor import GridEditor
from rbmk.model import save_load
from rbmk.model.components import (
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


def _btn(parent, text, cmd, kind="normal"):
    bg = theme.ACCENT if kind == "primary" else (theme.DANGER if kind == "danger" else theme.SURFACE2)
    fg = "#16120a" if kind == "primary" else ("#ffffff" if kind == "danger" else theme.INK)
    return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                     activebackground=theme.BORDER, activeforeground=theme.INK,
                     relief="flat", bd=0, padx=10, pady=4, font=theme.FONT, cursor="hand2")


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("RBMK 反应堆模拟器 — HBM 核科技 1.7.10")
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

        bottom = tk.Frame(self.root, bg=theme.SURFACE, height=210)
        bottom.pack(side="bottom", fill="x")
        bottom.pack_propagate(False)
        self.chart = ChartPanel(bottom, self)
        self.chart.pack(side="left", fill="both", expand=True)
        self.metrics = tk.Frame(bottom, bg=theme.SURFACE, width=320)
        self.metrics.pack(side="right", fill="y")
        self.metrics.pack_propagate(False)
        self._metric_labels = {}
        for i, (key, title) in enumerate([
            ("temp", "反应堆平均温度"), ("flux", "平均中子通量"),
            ("steam", "蒸汽产量"), ("power", "瞬时发电量"),
            ("total", "累计发电量"), ("fuel", "燃料平均寿命"),
        ]):
            box = tk.Frame(self.metrics, bg=theme.SURFACE2, bd=0)
            box.grid(row=i // 2, column=i % 2, sticky="nsew", padx=4, pady=4)
            tk.Label(box, text=title, bg=theme.SURFACE2, fg=theme.MUTED,
                     font=theme.FONT_SMALL, anchor="w").pack(fill="x", padx=8, pady=(6, 0))
            val = tk.Label(box, text="—", bg=theme.SURFACE2, fg=theme.INK,
                           font=theme.FONT_BOLD, anchor="w")
            val.pack(fill="x", padx=8, pady=(0, 6))
            self._metric_labels[key] = val
        self.metrics.grid_columnconfigure(0, weight=1)
        self.metrics.grid_columnconfigure(1, weight=1)

        body = tk.Frame(self.root, bg=theme.BG)
        body.pack(fill="both", expand=True)
        self._build_palette(body)
        self._build_inspector(body)
        self.grid_editor = GridEditor(body, self)
        self.grid_editor.pack(side="left", fill="both", expand=True)

    def _build_toolbar(self):
        bar = tk.Frame(self.root, bg=theme.SURFACE, height=48)
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)
        for text, cmd in [("新建", self.new_model), ("打开", self.open_file),
                          ("保存", self.save_file), ("导出分享", self.export_file)]:
            _btn(bar, text, cmd).pack(side="left", padx=(8 if text == "新建" else 2, 0), pady=7)
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
            b = tk.Button(grp, text=label, command=lambda v=s: self.set_speed(v),
                          bg=theme.SURFACE2, fg=theme.MUTED, relief="flat", bd=0,
                          padx=8, pady=4, font=theme.FONT_SMALL, cursor="hand2")
            b.pack(side="left", padx=2)
            self.speed_btns[s] = b

    def _build_palette(self, parent):
        left = tk.Frame(parent, bg=theme.SURFACE, width=210)
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
            sw = tk.Frame(row, bg=color, width=12, height=12)
            sw.pack(side="left", padx=(4, 6))
            sw.pack_propagate(False)
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
        right = tk.Frame(parent, bg=theme.SURFACE, width=300)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        tabs = tk.Frame(right, bg=theme.SURFACE)
        tabs.pack(fill="x")
        self._tab_btns = {}
        for key, name in [("prop", "选中属性"), ("overview", "总览"),
                          ("control", "模拟控制"), ("risk", "风险预警")]:
            b = tk.Button(tabs, text=name, command=lambda k=key: self.set_tab(k),
                          bg=theme.SURFACE, fg=theme.MUTED, relief="flat", bd=0,
                          padx=4, pady=8, font=theme.FONT_SMALL, cursor="hand2")
            b.pack(side="left", expand=True, fill="x")
            self._tab_btns[key] = b
        self.panel = tk.Frame(right, bg=theme.SURFACE)
        self.panel.pack(fill="both", expand=True, padx=10, pady=8)

    def _build_statusbar(self):
        bar = tk.Frame(self.root, bg=theme.SURFACE, height=28)
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
            b.configure(fg=theme.INK if key == self.tab else theme.MUTED)

    def set_speed(self, s):
        self.speed = s
        for k, b in self.speed_btns.items():
            b.configure(bg=theme.ACCENT if k == s else theme.SURFACE2,
                        fg="#16120a" if k == s else theme.MUTED)

    def toggle_run(self):
        self.running = not self.running
        self.run_btn.configure(text="⏸ 暂停" if self.running else "▶ 运行",
                               bg=theme.DANGER if self.running else theme.ACCENT,
                               fg="#ffffff" if self.running else "#16120a")

    def reset_simulation(self):
        """暂停并重置反应堆状态，保留已摆放的组件。"""
        self.running = False
        self.run_btn.configure(text="▶ 运行", bg=theme.ACCENT, fg="#16120a")
        self.engine.reset()
        self.chart.reset()
        self.grid_editor.redraw()
        self._refresh_state()
        self.render_panel()

    def toggle_boiler_mode(self):
        """切换普通锅炉 / ReaSim 锅炉模式。"""
        self.model.reasim_boilers = not self.model.reasim_boilers
        self._sync_boiler_btn()

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
        if self.tab == "risk":
            self.render_panel()
        elif self.tab == "prop":
            self._refresh_prop_values()
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
        self._metric_labels["temp"].configure(text=f"{s.avg_temperature:.0f} °C")
        self._metric_labels["flux"].configure(text=f"{s.avg_flux:.2f}")
        self._metric_labels["steam"].configure(text=f"{s.steam:.0f} mB/s")
        self._metric_labels["power"].configure(text=f"{s.electricity:,.0f} HE/tick")
        self._metric_labels["total"].configure(text=f"{s.total_energy:,.0f} HE")
        self._metric_labels["fuel"].configure(text=f"{s.fuel_remaining:.1f}%")

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
            tk.Label(head, text="自燃", bg=theme.ACCENT, fg="#16120a",
                     font=(theme.FAMILY, 7, "bold"), padx=4).pack(side="left", padx=(6, 0))
        tk.Label(head, text=f"{r+1}行 {c+1}列", bg=theme.SURFACE, fg=theme.MUTED,
                 font=(theme.FAMILY, 8)).pack(side="right")

        if beh == Behavior.FUEL:
            tk.Label(p, text="燃料类型", bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.FONT_SMALL, anchor="w").pack(fill="x", pady=(2, 2))
            var = tk.StringVar(value=FUELS[cell.fuel].name_cn if cell.fuel else "空燃料棒")
            om = tk.OptionMenu(p, var, *[f.name_cn for f in FUELS.values()],
                               command=lambda v: self._set_fuel(cell, v))
            om.configure(bg=theme.SURFACE2, fg=theme.INK, activebackground=theme.BORDER,
                         highlightthickness=0, font=theme.FONT_SMALL, anchor="w")
            om.pack(fill="x")
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
                          highlightthickness=0, command=lambda v: self._set_single(cell, v))
            sc.set(self.model.effective_insertion(cell))
            sc.pack(fill="x")
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
            self._prop_row("有效 level", "level")
        if beh == Behavior.BOILER:
            self._prop_row("每刻蒸汽产生量", "steam")
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
            vals["level"] = f"{1.0 - self.model.effective_insertion(cell) / 100.0:.2f}"
        if behavior_of(cell.comp) == Behavior.BOILER:
            vals["steam"] = f"{cell.steam_rate:.0f} mB/tick"
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

    def _render_control(self):
        p = self.panel
        self._lbl_global = tk.Label(p, text=f"全局插入深度 {self.model.global_insertion:.0f}%",
                 bg=theme.SURFACE, fg=theme.MUTED, font=theme.FONT_SMALL, anchor="w")
        self._lbl_global.pack(fill="x")
        sc = tk.Scale(p, from_=0, to=100, orient="horizontal", showvalue=False,
                      bg=theme.SURFACE, fg=theme.INK, troughcolor=theme.BORDER,
                      highlightthickness=0, command=self._set_global)
        sc.set(self.model.global_insertion)
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
                           highlightthickness=0, command=lambda v, gg=g: self._set_group_val(gg, v))
            scg.set(cur if cur is not None else self.model.global_insertion)
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
            if ft.name_cn == name:
                cell.fuel = ft.key
                break
        cell.has_rod = cell.fuel_type is not None and cell.fuel != "rbmk_fuel_empty"
        self.engine.state.melt_temp = self.engine._melt_threshold()
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

    def _set_heater_fluid(self, cell, name):
        for hf in HEAT_FLUIDS.values():
            if hf.name_cn == name:
                cell.heater_fluid = hf.key
                break
        self._refresh_prop_values()

    def _set_single(self, cell, v):
        cell.insertion = float(v)

    def _set_global(self, v):
        self.model.global_insertion = float(v)
        if getattr(self, "_lbl_global", None) is not None:
            self._lbl_global.configure(text=f"全局插入深度 {self.model.global_insertion:.0f}%")

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
        self.model.group_insertion[group.value] = float(v)

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
    return MainWindow(root), root
