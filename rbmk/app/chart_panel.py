"""实时曲线图（Canvas）：平均温度 / 中子通量 / 瞬时发电量。"""
import tkinter as tk

from rbmk.app import theme

MAX_POINTS = 150

# key, 图例名, 颜色, 自动缩放下限（避免小数值被放大成满屏）
SERIES = (
    ("temp", "平均温度", theme.MC_RED, 100.0),
    ("elec", "瞬时发电量", theme.MC_GOLD, 100.0),
    ("flux", "中子通量", theme.MC_AQUA, 1.0),
)


class ChartPanel(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=theme.SURFACE)
        self.app = app
        self.hist = {key: [] for key, _, _, _ in SERIES}

        head = tk.Frame(self, bg=theme.SURFACE)
        head.pack(fill="x", padx=8, pady=(6, 0))
        tk.Label(head, text="实时曲线", bg=theme.SURFACE, fg=theme.INK,
                 font=theme.FONT_BOLD).pack(side="left")
        legend = tk.Frame(head, bg=theme.PLOT_BG, bd=1, relief="sunken")
        legend.pack(side="right")
        for _, name, color, _ in SERIES:
            tk.Label(legend, text="■ " + name, bg=theme.PLOT_BG, fg=color,
                     font=theme.FONT_SMALL).pack(side="right", padx=4, pady=1)

        self.canvas = tk.Canvas(self, bg=theme.PLOT_BG, highlightthickness=2,
                                highlightbackground=theme.BORDER, height=140)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=6)
        self.canvas.bind("<Configure>", lambda e: self.redraw())

    def reset(self):
        self.hist = {key: [] for key, _, _, _ in SERIES}
        self.redraw()

    def push(self, state):
        self.hist["temp"].append(float(state.avg_temperature))
        self.hist["elec"].append(float(state.electricity))
        self.hist["flux"].append(float(state.flux))
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
            cv.create_line(0, y, w, y, fill=theme.PLOT_GRID)
        for key, _, color, floor in SERIES:
            arr = self.hist[key]
            if len(arr) < 2:
                continue
            # 每条曲线按自己窗口内的最大值缩放，避免单位差异导致某条线贴底
            scale = max(max(abs(v) for v in arr), floor)
            pts = []
            for i, v in enumerate(arr):
                x = i / (MAX_POINTS - 1) * w
                y = h - max(0.0, min(1.0, v / scale)) * h
                pts.extend([x, y])
            cv.create_line(*pts, fill=color, width=2)
