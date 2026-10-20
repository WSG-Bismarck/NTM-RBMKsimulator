"""俯视网格编辑器（Canvas）。"""
import tkinter as tk

from rbmk.app import theme
from rbmk.app.icons import get_icon
from rbmk.app.console_view import column_overlays
from rbmk.model.components import (
    COMPONENT_INFO,
    COMPONENT_SHORT,
    CONTROL_GROUP_COLORS,
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

        self.canvas = tk.Canvas(self, bg=theme.BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._on_down)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_up)
        self.canvas.bind("<Button-3>", self._on_right)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-2>", self._pan_start)
        self.canvas.bind("<B2-Motion>", self._pan_move)
        self.canvas.bind("<Configure>", lambda e: self.redraw())

    @property
    def cell(self) -> int:
        return max(12, int(26 * self.zoom))

    def _origin(self):
        m = self.app.model
        w = max(self.canvas.winfo_width(), 1)
        h = max(self.canvas.winfo_height(), 1)
        gw = m.cols * (self.cell + 2) + 2
        gh = m.rows * (self.cell + 2) + 2
        return (w - gw) // 2 + self.pan_x, (h - gh) // 2 + self.pan_y

    def _cell_from_event(self, x, y):
        ox, oy = self._origin()
        cs = self.cell + 2
        c = (x - ox - 2) // cs
        r = (y - oy - 2) // cs
        m = self.app.model
        if 0 <= r < m.rows and 0 <= c < m.cols:
            return int(r), int(c)
        return None

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
        self._painting = True
        self._paint(self._cell_from_event(e.x, e.y))

    def _on_drag(self, e):
        if self._painting:
            self._paint(self._cell_from_event(e.x, e.y))

    def _on_up(self, e):
        self._painting = False

    def _on_right(self, e):
        rc = self._cell_from_event(e.x, e.y)
        if rc:
            self.app.model.erase(*rc)
            self.app.on_model_changed()
            self.redraw()

    def _on_wheel(self, e):
        self.zoom = max(0.55, min(1.9, self.zoom + (0.1 if e.delta > 0 else -0.1)))
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
                x = ox + 2 + c * (cs + 2)
                y = oy + 2 + r * (cs + 2)
                cell = m.grid[r][c]
                if cell is None:
                    fill, outline = "#151a20", "#1f262e"
                else:
                    fill, outline = COMPONENT_INFO[cell.comp][1], "#0b0e11"
                if cell is not None and behavior_of(cell.comp) == Behavior.CONTROL:
                    outline = CONTROL_GROUP_COLORS.get(cell.group, "#0b0e11")
                if cell is not None and behavior_of(cell.comp) == Behavior.FUEL:
                    ft = cell.fuel_type
                    if ft and ft.melting_point > 0 and cell.temp > 0.85 * ft.melting_point:
                        outline = theme.DANGER
                cv.create_rectangle(x, y, x + cs, y + cs, fill=fill, outline=outline,
                                    width=3 if (cell is not None and behavior_of(cell.comp) == Behavior.CONTROL) else 1)
                if cell is not None:
                    # 用模组方块贴图作为图标（缺失时退回字母缩写）
                    icon = get_icon(cell.comp.value, max(10, cs - 2))
                    if icon is not None:
                        cv.create_image(x + cs / 2, y + cs / 2, image=icon)
                    elif cs >= 18:
                        cv.create_text(x + cs / 2, y + cs / 2 + 1,
                                       text=COMPONENT_SHORT[cell.comp],
                                       fill="#0b0e11", font=(theme.FAMILY, max(6, cs // 4)))
                    # 控制台叠加层：热量红线 / 燃料三色条 / 水条与蒸汽类型点 / 分组色与插入条
                    scale = cs / 10.0
                    for lx, ly, lw, lh, color in column_overlays(cell, self.app.model):
                        cv.create_rectangle(x + lx * scale, y + ly * scale,
                                            x + (lx + lw) * scale - 1, y + (ly + lh) * scale - 1,
                                            fill="#%02x%02x%02x" % color, outline="", width=0)
        if self.selected:
            sr, sc = self.selected
            x = ox + 2 + sc * (cs + 2)
            y = oy + 2 + sr * (cs + 2)
            cv.create_rectangle(x - 2, y - 2, x + cs + 2, y + cs + 2, outline=theme.ACCENT, width=2)

        cv.create_text(ox, max(8, oy - 6), anchor="sw", text="俯视堆芯",
                       fill=theme.MUTED, font=theme.FONT_SMALL)
        cv.create_text(ox + m.cols * (cs + 2), max(8, oy - 6), anchor="se",
                       text=f"{m.cols}×{m.rows}   缩放 {int(self.zoom * 100)}%",
                       fill=theme.MUTED, font=theme.FONT_SMALL)
