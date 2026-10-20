"""RBMK 反应堆控制台视图。

复刻 com.hbm.inventory.gui.GUIRBMKConsole 的柱阵列绘制逻辑：
  15×15 格，每格 10×10（本窗口按 2 倍绘制）：
  1. 按 ColumnType.offset 画图标（贴图 v=172）
  2. 热量条：h = min(ceil((heat-20)*10/maxHeat), 10)，左右两侧红色边线自底向上
  3. FUEL/FUEL_SIM：壳温条(x+1,w2)、浓缩度条(x+4,w2)、氙毒条(x+7,w2)，高 8
  4. BOILER：水条(x+1,w3)、蒸汽条(x+6,w3)，高 8；蒸汽类型点(x+4,y+1/3/5/7,2×2)
  5. CONTROL：分组色两条竖线(x+3,x+6)，高 8；随后**穿透**到 CONTROL_AUTO 的插入条
  6. CONTROL_AUTO：插入条 (x+4,y+1,w2)，高 8-ceil(level*8)
  7. HEATEX：进口流体条(x+1,w3)、出口流体条(x+6,w3)
  8. 选中格：白色描边
  另外顶部复刻控制台的中子通量折线（绿色，带最大/最小值）。
"""
from __future__ import annotations

import math
import tkinter as tk
from collections import deque

from PIL import Image, ImageDraw, ImageTk

from rbmk.app import theme
from rbmk.app.icons import icons_dir  # noqa: F401  (确保资源目录被引用)
from rbmk.model.components import ComponentType as C

# ---- 贴图坐标（game 像素）----
ICON_V = 172
TYPE_OFFSET = {
    "BLANK": 0, "FUEL": 10, "CONTROL": 20, "CONTROL_AUTO": 30, "BOILER": 40,
    "MODERATOR": 50, "ABSORBER": 60, "REFLECTOR": 70, "OUTGASSER": 80,
    "FUEL_SIM": 90, "STORAGE": 110, "COOLER": 120, "HEATEX": 130,
}
KIND_OF = {
    C.RBMK_ROD: "FUEL", C.RBMK_ROD_MOD: "FUEL",
    C.RBMK_ROD_REASIM: "FUEL_SIM", C.RBMK_ROD_REASIM_MOD: "FUEL_SIM",
    C.RBMK_CONTROL: "CONTROL", C.RBMK_CONTROL_MOD: "CONTROL", C.RBMK_CONTROL_REASIM: "CONTROL",
    C.RBMK_CONTROL_AUTO: "CONTROL_AUTO", C.RBMK_CONTROL_REASIM_AUTO: "CONTROL_AUTO",
    C.RBMK_BOILER: "BOILER", C.RBMK_MODERATOR: "MODERATOR", C.RBMK_ABSORBER: "ABSORBER",
    C.RBMK_REFLECTOR: "REFLECTOR", C.RBMK_OUTGASSER: "OUTGASSER", C.RBMK_STORAGE: "STORAGE",
    C.RBMK_COOLER: "COOLER", C.RBMK_BLANK: "BLANK", C.RBMK_HEATER: "HEATEX",
}
AUTO_KINDS = ("CONTROL_AUTO",)
GROUP_INDEX = {"RED": 0, "YELLOW": 1, "GREEN": 2, "BLUE": 3, "PURPLE": 4}

# ---- 颜色（取样自 gui_rbmk_console.png）----
C_HEAT = (169, 0, 0)
C_SKIN = (255, 135, 0)
C_ENRICH = (59, 200, 0)
C_XENON = (139, 0, 200)
C_WATER = (72, 99, 255)
C_STEAM = (231, 231, 231)
C_HEATEX_IN = (23, 183, 196)
C_HEATEX_OUT = (175, 31, 84)
C_AUTO = (100, 111, 120)
C_SELECT = (255, 255, 255)
CTRL_COLORS = [(255, 0, 0), (255, 216, 0), (76, 255, 0), (0, 38, 255), (178, 0, 255)]
STEAM_DOT = {
    "STEAM": (255, 255, 255),
    "HOTSTEAM": (255, 235, 235),
    "SUPERHOTSTEAM": (255, 195, 195),
    "ULTRAHOTSTEAM": (255, 139, 139),
}

CELL = 20          # 2× 放大
MAX_HEAT = 1500.0
BOILER_WATER_MAX = 10000.0
BOILER_STEAM_MAX = 1000000.0
GRAPH_H = 46


def _asset_path(name: str) -> str:
    import os
    import sys

    if getattr(sys, "frozen", False):
        base = os.path.join(getattr(sys, "_MEIPASS", ""), "rbmk", "assets", "gui")
    else:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "gui")
    return os.path.join(base, name)


def column_overlays(cell, model, max_heat: float = MAX_HEAT):
    """返回该柱在 10×10 单元格内的叠加矩形：[(x, y, w, h, rgb), ...]（game 像素坐标）。

    与 GUIRBMKConsole.drawScreen 的绘制顺序/坐标一致，供控制台窗口和主网格共用。
    """
    out: list[tuple[float, float, float, float, tuple[int, int, int]]] = []
    kind = KIND_OF.get(cell.comp, "BLANK")

    heat = cell.shown_temp if cell.shown_temp else cell.temp
    hh = int(min(max(math.ceil((heat - 20.0) * 10.0 / max_heat), 0), 10))
    if hh > 0:
        out.append((0, 10 - hh, 1, hh, C_HEAT))
        out.append((9, 10 - hh, 1, hh, C_HEAT))

    if kind in ("FUEL", "FUEL_SIM"):
        ft = cell.fuel_type
        if ft is not None:
            melt = float(getattr(ft, "melting_point", 0.0) or 0.0)
            fh = 0 if melt <= 0 else int(min(max(math.ceil((cell.hull_heat - 20.0) * 8.0 / melt), 0), 8))
            fe = int(min(max(math.ceil((1.0 - cell.burnup) * 8.0), 0), 8))
            fx = int(min(max(math.ceil(cell.xenon * 8.0 / 100.0), 0), 8))
            out.append((1, 9 - fh, 2, fh, C_SKIN))
            out.append((4, 9 - fe, 2, fe, C_ENRICH))
            out.append((7, 9 - fx, 2, fx, C_XENON))

    elif kind == "BOILER":
        fw = int(min(max(math.ceil(cell.water * 8.0 / BOILER_WATER_MAX), 0), 8))
        out.append((1, 9 - fw, 3, fw, C_WATER))
        # 模型不设蒸汽缓冲（蒸汽直接外送），蒸汽条高度为 0
        dot = STEAM_DOT.get(cell.steam_type)
        if dot:
            dy = {"STEAM": 1, "HOTSTEAM": 3, "SUPERHOTSTEAM": 5, "ULTRAHOTSTEAM": 7}[cell.steam_type]
            out.append((4, dy, 2, 2, dot))

    elif kind == "HEATEX":
        fw = int(min(max(math.ceil(cell.water * 8.0 / 16000.0), 0), 8))
        out.append((1, 9 - fw, 3, fw, C_HEATEX_IN))

    # CONTROL 在模组里没有 break，会穿透到 CONTROL_AUTO 的插入条
    if kind == "CONTROL":
        idx = GROUP_INDEX.get(getattr(cell.group, "value", None))
        if idx is not None:
            color = CTRL_COLORS[idx]
            out.append((3, 1, 1, 8, color))
            out.append((6, 1, 1, 8, color))

    if kind in ("CONTROL", "CONTROL_AUTO"):
        if kind == "CONTROL_AUTO":
            frac = max(0.0, min(1.0, 1.0 - cell.level))
        else:
            frac = max(0.0, min(1.0, model.effective_insertion(cell) / 100.0))
        fr = 8 - int(math.ceil(frac * 8.0))
        out.append((4, 1, 2, fr, C_AUTO))

    return [r for r in out if r[3] > 0 and r[2] > 0]


class ConsoleWindow(tk.Toplevel):
    """控制台窗口（非模态，运行中自动刷新）。"""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("RBMK 反应堆控制台")
        self.configure(bg=theme.BG)
        self.resizable(False, False)
        self._sheet = Image.open(_asset_path("console.png")).convert("RGBA")
        self._flux_hist: deque[float] = deque(maxlen=225)
        self._photo = None
        rows, cols = app.model.rows, app.model.cols
        w, h = cols * CELL, rows * CELL
        self.canvas = tk.Canvas(self, width=w, height=h + GRAPH_H + 8, bg=theme.BG,
                                highlightthickness=0, bd=0)
        self.canvas.pack(padx=10, pady=(10, 2))
        self._item = self.canvas.create_image(0, 0, anchor="nw")
        self.status = tk.Label(self, text="", bg=theme.BG, fg=theme.MUTED,
                               font=theme.FONT_SMALL, justify="left", anchor="w")
        self.status.pack(fill="x", padx=10, pady=(0, 8))
        self.protocol("WM_DELETE_WINDOW", self._close)
        try:
            rx, ry = app.root.winfo_rootx(), app.root.winfo_rooty()
            self.geometry(f"+{rx + 60}+{ry + 96}")
        except Exception:
            pass
        self.refresh()
        self._loop()

    # ---------- 数据 ----------
    def _heat(self, cell) -> float:
        return cell.shown_temp if cell.shown_temp else cell.temp

    def _insertion_frac(self, cell) -> float:
        kind = KIND_OF.get(cell.comp, "BLANK")
        if kind == "CONTROL_AUTO":
            return max(0.0, min(1.0, 1.0 - cell.level))
        return max(0.0, min(1.0, self.app.model.effective_insertion(cell) / 100.0))

    # ---------- 绘制 ----------
    def _rect(self, dr, x, y, w, h, color):
        """game 像素坐标 → 画布像素。"""
        s = CELL / 10.0
        if h <= 0 or w <= 0:
            return
        dr.rectangle([x * s, y * s, (x + w) * s - 1, (y + h) * s - 1], fill=color)

    def _icon(self, kind: str) -> Image.Image:
        off = TYPE_OFFSET.get(kind, 0)
        tile = self._sheet.crop((off, ICON_V, off + 10, ICON_V + 10))
        return tile.resize((CELL, CELL), Image.NEAREST)

    def _draw_column(self, img, dr, cell, x, y):
        kind = KIND_OF.get(cell.comp, "BLANK")
        img.paste(self._icon(kind), (int(x * CELL / 10), int(y * CELL / 10)))
        for ox, oy, w, h, color in column_overlays(cell, self.app.model):
            self._rect(dr, x + ox, y + oy, w, h, color)

    def _draw_graph(self, dr, flux_vals, top):
        w = self.app.model.cols * CELL
        dr.rectangle([0, top, w, top + GRAPH_H - 1], fill=(18, 22, 26))
        if len(flux_vals) < 2:
            return
        hi, lo = max(flux_vals), min(flux_vals)
        rng = max(hi - lo, 1.0)
        pts = []
        for i, v in enumerate(flux_vals):
            gx = i * (w - 2) / max(len(flux_vals) - 1, 1) + 1
            gy = top + GRAPH_H - 4 - (v - lo) * (GRAPH_H - 10) / rng
            pts.append((gx, gy))
        dr.line(pts, fill=(101, 255, 0), width=1)
        dr.text((3, top + 2), f"{hi:.0f}", fill=(101, 255, 0))
        dr.text((3, top + GRAPH_H - 10), f"{lo:.0f}", fill=(101, 255, 0))

    def _render(self) -> Image.Image:
        model = self.app.model
        w, h = model.cols * CELL, model.rows * CELL
        img = Image.new("RGBA", (w, h + GRAPH_H + 8), (20, 24, 28, 255))
        dr = ImageDraw.Draw(img)

        flux = getattr(self.app.engine.state, "flux", 0.0)
        self._flux_hist.append(float(flux))
        self._draw_graph(dr, list(self._flux_hist), 0)

        oy = GRAPH_H + 8
        grid = Image.new("RGBA", (w, h), (20, 24, 28, 255))
        gdr = ImageDraw.Draw(grid)
        for r in range(model.rows):
            for c in range(model.cols):
                gdr.rectangle([c * CELL, r * CELL, (c + 1) * CELL - 1, (r + 1) * CELL - 1],
                              outline=(38, 44, 50))
        for r, c, cell in model.iter_cells():
            self._draw_column(grid, gdr, cell, c * 10, r * 10)
            if self.app.selected_cell == (r, c):
                gdr.rectangle([c * CELL, r * CELL, (c + 1) * CELL - 1, (r + 1) * CELL - 1],
                              outline=C_SELECT)

        img.paste(grid, (0, oy))
        return img

    def refresh(self):
        if not self.winfo_exists():
            return
        model = self.app.model
        want_w, want_h = model.cols * CELL, model.rows * CELL + GRAPH_H + 8
        if int(self.canvas["width"]) != want_w or int(self.canvas["height"]) != want_h:
            self.canvas.configure(width=want_w, height=want_h)
        img = self._render()
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.itemconfigure(self._item, image=self._photo)
        st = self.app.engine.state
        self.status.configure(
            text=(f"中子通量 {st.flux:.0f}　平均温度 {st.avg_temperature:.1f}°C　"
                  f"瞬时发电量 {st.electricity:.0f} HE/tick"),
        )

    # ---------- 循环 ----------
    def _loop(self):
        if not self.winfo_exists():
            return
        if self.app.running:
            self.refresh()
        self.after(200, self._loop)

    def _close(self):
        self.app.console_window = None
        self.destroy()
