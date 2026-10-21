"""组件悬停提示框（仿原版物品提示：深色底 + 立体边框，支持逐行着色）。"""
from __future__ import annotations

import tkinter as tk

from rbmk.app import theme

C_DEFAULT = "#ffffff"
C_TEMP = "#ffff55"   # 柱温（黄）
C_BURN = "#55ff55"   # 燃耗（绿）
C_XENON = "#ff55ff"  # 氙毒（紫）
C_SURFACE = "#ff8888"  # 表面温度（浅红）
C_MODERATOR = "#ffff55"  # 慢化剂（黄）
C_POWER = "#ffaa00"      # 供电需求（橙）
C_NAME = "#ffffff"


class HoverTip:
    """光标跟随提示框；内容为 [(文本, 颜色), ...]，每行一个 Label。"""

    BG = "#100010"
    BORDER = "#3a0f4a"

    def __init__(self, master):
        self.win = tk.Toplevel(master)
        self.win.withdraw()
        self.win.overrideredirect(True)
        try:
            self.win.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.frame = tk.Frame(self.win, bg=self.BORDER, bd=0)
        self.frame.pack()
        self.body = tk.Frame(self.frame, bg=self.BG)
        self.body.pack(padx=6, pady=4)
        self.labels: list[tk.Label] = []
        self._signature: tuple | None = None

    def _ensure_rows(self, count: int) -> None:
        if len(self.labels) == count:
            return
        for lab in self.labels:
            lab.destroy()
        self.labels = []
        for _ in range(count):
            lab = tk.Label(self.body, text="", bg=self.BG, fg=C_DEFAULT,
                           font=(theme.FAMILY, 9), justify="left", anchor="w")
            lab.pack(fill="x")
            self.labels.append(lab)

    def show(self, lines: list[tuple[str, str]], x_root: int, y_root: int) -> None:
        self._ensure_rows(len(lines))
        for lab, (text, color) in zip(self.labels, lines):
            if lab.cget("text") != text:
                lab.configure(text=text)
            if lab.cget("fg") != color:
                lab.configure(fg=color)
        self.win.deiconify()
        self.win.update_idletasks()
        w, h = self.win.winfo_width(), self.win.winfo_height()
        sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        x = min(max(0, x_root + 16), max(0, sw - w - 4))
        y = min(max(0, y_root + 14), max(0, sh - h - 4))
        geom = f"+{x}+{y}"
        if self.win.winfo_geometry().split("+", 1)[-1] != geom[1:]:
            self.win.geometry(geom)

    def hide(self) -> None:
        self.win.withdraw()

    def text(self) -> str:
        return "\n".join(lab.cget("text") for lab in self.labels)

    def destroy(self) -> None:
        try:
            self.win.destroy()
        except tk.TclError:
            pass
