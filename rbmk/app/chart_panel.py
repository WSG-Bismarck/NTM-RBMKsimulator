"""实时曲线图（Canvas）。"""
import tkinter as tk

from rbmk.app import theme

MAX_POINTS = 150


class ChartPanel(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=theme.SURFACE)
        self.app = app
        self.hist = {"temp": [], "power": [], "flux": []}

        head = tk.Frame(self, bg=theme.SURFACE)
        head.pack(fill="x", padx=8, pady=(6, 0))
        tk.Label(head, text="实时曲线", bg=theme.SURFACE, fg=theme.MUTED,
                 font=theme.FONT_SMALL).pack(side="left")
        for name, color in (("温度", "#ff6b35"), ("功率", "#f0a13a"), ("中子通量", "#4fc3e8")):
            tk.Label(head, text="■ " + name, bg=theme.SURFACE, fg=color,
                     font=theme.FONT_SMALL).pack(side="right", padx=4)

        self.canvas = tk.Canvas(self, bg=theme.SURFACE, highlightthickness=0, height=140)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=6)
        self.canvas.bind("<Configure>", lambda e: self.redraw())

    def reset(self):
        self.hist = {"temp": [], "power": [], "flux": []}
        self.redraw()

    def push(self, state):
        self.hist["temp"].append(min(1.0, state.temperature / 3000.0))
        self.hist["power"].append(min(1.0, state.power / 4000.0))
        self.hist["flux"].append(min(1.0, state.flux / 10.0))
        for k in self.hist:
            if len(self.hist[k]) > MAX_POINTS:
                self.hist[k] = self.hist[k][-MAX_POINTS:]
        self.redraw()

    def redraw(self):
        cv = self.canvas
        cv.delete("all")
        w = max(cv.winfo_width(), 10)
        h = max(cv.winfo_height(), 10)
        for i in range(1, 5):
            y = h * i / 5
            cv.create_line(0, y, w, y, fill="#20272f")
        for key, color in (("temp", "#ff6b35"), ("power", "#f0a13a"), ("flux", "#4fc3e8")):
            arr = self.hist[key]
            if len(arr) < 2:
                continue
            pts = []
            for i, v in enumerate(arr):
                x = i / (MAX_POINTS - 1) * w
                y = h - v * h
                pts.extend([x, y])
            cv.create_line(*pts, fill=color, width=2)
