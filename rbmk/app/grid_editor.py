"""俯视网格编辑器（Canvas）。"""
import tkinter as tk

from rbmk.app import theme
from rbmk.app.icons import get_icon
from rbmk.app.overlays import column_overlays
from rbmk.app.tooltip import C_BURN, C_DEFAULT, C_TEMP, C_XENON, HoverTip
from rbmk.model.components import (
    COMPONENT_INFO,
    COMPONENT_SHORT,
    Behavior,
    ComponentType,
    behavior_of,
)


class GridEditor(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=theme.BG)
        self.app = app
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self._pan_last = None
        self.selected: tuple[int, int] | None = None
        self._painting = False

        self.canvas = tk.Canvas(self, bg=theme.GRID_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._on_down)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_up)
        self.canvas.bind("<Button-3>", self._on_right)
        self.tip = HoverTip(self)
        self._tip_rc = None
        self._tip_pos = (0, 0)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", lambda e: self._hide_tip())
        self.bind("<Destroy>", self._on_destroy)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-2>", self._pan_start)
        self.canvas.bind("<B2-Motion>", self._pan_move)
        self.canvas.bind("<Configure>", lambda e: self.redraw())

    @property
    def zoom(self) -> float:
        """缩放系数；内部按「图标整数倍率」离散化（3 = 100%，格子 30px）。"""
        return getattr(self, "_icon_scale", 3) / 3.0

    @zoom.setter
    def zoom(self, value: float) -> None:
        self._icon_scale = max(1, min(6, int(round(float(value) * 3.0))))

    @property
    def cell(self) -> int:
        """格子边长 = 10 × 图标整数倍率。

        组件图标是模组 10×10 贴图，只有整数倍缩放才能让图标像素、格子边缘与叠加层
        （按 cs/10 缩放）严格对齐；非整数倍会让图标内部条纹粗细不一、看起来"错位"。
        """
        return 10 * getattr(self, "_icon_scale", 3)

    def _origin(self):
        m = self.app.model
        w = max(self.canvas.winfo_width(), 1)
        h = max(self.canvas.winfo_height(), 1)
        gw = m.cols * self.cell
        gh = m.rows * self.cell
        return (w - gw) // 2 + self.pan_x, (h - gh) // 2 + self.pan_y

    def _cell_from_event(self, x, y):
        ox, oy = self._origin()
        cs = self.cell
        c = int((x - ox) // cs)
        r = int((y - oy) // cs)
        m = self.app.model
        if 0 <= r < m.rows and 0 <= c < m.cols:
            return int(r), int(c)
        return None

    # ---------------- 悬停提示 ----------------
    def _on_destroy(self, e):
        if e.widget is self:
            self.tip.destroy()

    def _hide_tip(self):
        self._tip_rc = None
        self._tip_pos = (0, 0)
        if getattr(self, "tip", None) is not None:
            self.tip.hide()

    def tooltip_lines(self, cell, rc):
        """组件悬停信息：[(文本, 颜色), ...]，纯函数便于测试。"""
        from rbmk.model.components import HEAT_FLUIDS, STEAM_TYPES

        name = COMPONENT_INFO[cell.comp][0]
        beh = behavior_of(cell.comp)
        temp = cell.shown_temp if cell.shown_temp else cell.temp
        lines = [(f"{name}    {rc[0] + 1}行 {rc[1] + 1}列", C_DEFAULT),
                 (f"柱温 {temp:.1f} °C", C_TEMP)]
        if beh == Behavior.FUEL:
            ft = cell.fuel_type
            if ft is None:
                lines.append(("无燃料棒", C_DEFAULT))
            else:
                lines.append((f"燃料 {ft.name_cn}", C_DEFAULT))
                lines.append((f"表面温度 {cell.hull_heat:.1f} °C / {cell.core_heat:.1f} °C", C_DEFAULT))
                lines.append((f"燃耗 {cell.burnup * 100:.2f}%", C_BURN))
                lines.append((f"氙毒 {cell.xenon:.1f}%", C_XENON))
                if cell.flux > 0:
                    lines.append((f"中子通量 {cell.flux:,.0f}", C_DEFAULT))
        elif beh == Behavior.CONTROL:
            group = cell.group.value if cell.group is not None else "空置"
            if cell.comp in (ComponentType.RBMK_CONTROL_AUTO, ComponentType.RBMK_CONTROL_REASIM_AUTO):
                lines.append((f"控制组 {group}   透过率 {cell.level:.2f}", C_DEFAULT))
                lines.append((f"目标透过率 {cell.target_level:.2f}", C_DEFAULT))
            else:
                ins = self.app.model.effective_insertion(cell)
                lines.append((f"控制组 {group}   插入深度 {ins:.0f}%", C_DEFAULT))
        elif beh == Behavior.BOILER:
            stype = STEAM_TYPES.get(cell.steam_type)
            lines.append((f"蒸汽类型 {stype.name_cn if stype else cell.steam_type}", C_DEFAULT))
            lines.append((f"每刻产汽 {cell.steam_rate:,.0f} mB/tick", C_DEFAULT))
            if getattr(cell, "reasim_steam_rate", 0):
                lines.append((f"其中 ReaSim {cell.reasim_steam_rate:,.0f} mB/tick", C_DEFAULT))
        elif beh == Behavior.COOLER:
            lines.append((f"每刻消耗 {cell.cooler_rate:,.0f} mB/tick", C_DEFAULT))
            lines.append((f"作用柱数 {cell.cooler_cells}", C_DEFAULT))
        elif beh == Behavior.HEATER:
            fluid = HEAT_FLUIDS.get(cell.heater_fluid)
            lines.append((f"流体 {fluid.name_cn if fluid else cell.heater_fluid}", C_DEFAULT))
            lines.append((f"产量 {cell.heater_rate:,.0f} mB/tick", C_DEFAULT))
            lines.append((f"热量 {cell.heater_heat:,.0f} TU/tick", C_DEFAULT))
        elif cell.fuel is not None:
            ft = cell.fuel_type
            if ft is not None:
                lines.append((f"燃料 {ft.name_cn}", C_DEFAULT))
        return lines

    def refresh_tip(self):
        """每 100ms 由主循环调用：鼠标仍停在柱子上时刷新数值。"""
        if self._tip_rc is None:
            return
        cell = self.app.model.cell_at(*self._tip_rc)
        if cell is None:
            self._hide_tip()
            return
        self.tip.show(self.tooltip_lines(cell, self._tip_rc), *self._tip_pos)

    def _on_motion(self, e):
        rc = self._cell_from_event(e.x, e.y)
        if not rc:
            self._hide_tip()
            return
        cell = self.app.model.cell_at(*rc)
        if cell is None:
            self._hide_tip()
            return
        self._tip_rc = rc
        self._tip_pos = (e.x_root, e.y_root)
        self.tip.show(self.tooltip_lines(cell, rc), e.x_root, e.y_root)

    def _paint(self, rc):
        if rc is None:
            return
        r, c = rc
        tool = self.app.selected_tool
        if tool == "select":
            self.selected = rc
            self.app.on_select(rc)
            return
        if tool == "erase":
            self.app.model.erase(r, c)
        else:
            comp = ComponentType(tool)
            kw = {}
            if behavior_of(comp) == Behavior.FUEL:
                kw["fuel"] = self.app.default_fuel
            self.app.model.place(r, c, comp, **kw)
        self.app.on_model_changed()
        self.redraw()

    def _on_down(self, e):
        self._hide_tip()
        self._painting = True
        self._paint(self._cell_from_event(e.x, e.y))

    def _on_drag(self, e):
        if self._painting:
            self._paint(self._cell_from_event(e.x, e.y))

    def _on_up(self, e):
        self._painting = False

    def _on_right(self, e):
        self._hide_tip()
        rc = self._cell_from_event(e.x, e.y)
        if rc:
            self.app.model.erase(*rc)
            self.app.on_model_changed()
            self.redraw()

    def _on_wheel(self, e):
        self._hide_tip()
        # 每次滚轮切换一档图标倍率（格子 ±10px），保证始终是整数倍缩放
        self.zoom = self.zoom + (1 / 3 if e.delta > 0 else -1 / 3)
        self.redraw()

    def _pan_start(self, e):
        self._pan_last = (e.x, e.y)

    def _pan_move(self, e):
        if self._pan_last is None:
            return
        dx = e.x - self._pan_last[0]
        dy = e.y - self._pan_last[1]
        self._pan_last = (e.x, e.y)
        self.pan_x += dx
        self.pan_y += dy
        self.redraw()

    def redraw(self):
        cv = self.canvas
        cv.delete("all")
        m = self.app.model
        cs = self.cell
        ox, oy = self._origin()
        for r in range(m.rows):
            for c in range(m.cols):
                x = ox + c * cs
                y = oy + r * cs
                cell = m.grid[r][c]
                if cell is None:
                    fill, outline = theme.GRID_BG, theme.GRID_LINE
                else:
                    # 已放置组件不画描边，图标之间紧密拼接、无缝隙（过热时才加红框）
                    fill, outline = COMPONENT_INFO[cell.comp][1], ""
                if cell is not None and behavior_of(cell.comp) == Behavior.FUEL:
                    ft = cell.fuel_type
                    if ft and ft.melting_point > 0 and cell.temp > 0.85 * ft.melting_point:
                        outline = theme.DANGER
                # 格子严格取 cs×cs 像素（x..x+cs-1），与图标、叠加层同一像素网格
                cv.create_rectangle(x, y, x + cs - 1, y + cs - 1, fill=fill, outline=outline, width=1)
                if cell is not None:
                    # 图标铺满整格，锚点左上角，保证与格子像素完全重合
                    icon = get_icon(cell.comp.value, max(10, cs))
                    if icon is not None:
                        cv.create_image(x, y, anchor="nw", image=icon)
                    elif cs >= 18:
                        cv.create_text(x + cs / 2, y + cs / 2 + 1,
                                       text=COMPONENT_SHORT[cell.comp],
                                       fill="#000000", font=(theme.FAMILY, max(6, cs // 4)))
                    # 控制台叠加层：热量红线 / 燃料三色条 / 水条与蒸汽类型点 / 分组色与插入条
                    # 坐标一律取整到像素，避免每个格子的半像素舍入不同导致粗细/位置抖动
                    scale = cs / 10.0
                    for lx, ly, lw, lh, color in column_overlays(cell, self.app.model):
                        x1 = int(round(x + lx * scale))
                        y1 = int(round(y + ly * scale))
                        x2 = int(round(x + (lx + lw) * scale)) - 1
                        y2 = int(round(y + (ly + lh) * scale)) - 1
                        if x2 < x1:
                            x2 = x1
                        if y2 < y1:
                            y2 = y1
                        cv.create_rectangle(x1, y1, x2, y2,
                                            fill="#%02x%02x%02x" % color, outline="", width=0)
        if self.selected:
            sr, sc = self.selected
            x = ox + sc * cs
            y = oy + sr * cs
            cv.create_rectangle(x - 2, y - 2, x + cs + 1, y + cs + 1, outline=theme.ACCENT, width=2)

        cv.create_text(ox, max(8, oy - 6), anchor="sw", text="俯视堆芯",
                       fill=theme.MUTED, font=theme.FONT_SMALL)
        cv.create_text(ox + m.cols * cs, max(8, oy - 6), anchor="se",
                       text=f"{m.cols}×{m.rows}   格子 {self.cell}px",
                       fill=theme.MUTED, font=theme.FONT_SMALL)
