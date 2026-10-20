"""实时曲线图（Canvas）：平均温度 / 中子通量 / 瞬时发电量。"""
import tkinter as tk

from rbmk.app import theme

MAX_POINTS = 150

# key, 图例名, 颜色, 自动缩放下限（避免小数值被放大成满屏）
SERIES = (
    ("temp", "平均温度", "#ff6b35", 100.0),
    ("elec", "瞬时发电量", "#f0a13a", 100.0),
    ("flux", "中子通量", "#4fc3e8", 1.0),
)


class ChartPanel(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=theme.SURFACE)
        self.app = app
        self.hist = {key: [] for key, _, _, _ in SERIES}

        head = tk.Frame(self, bg=theme.SURFACE)
        head.pack(fill="x", padx=8, pady=(6, 0))
        tk.Label(head, text="实时曲线", bg=theme.SURFACE, fg=theme.MUTED,
                 font=theme.FONT_SMALL).pack(side="left")
        for _, name, color, _ in SERIES:
            tk.Label(head, text="■ " + name, bg=theme.SURFACE, fg=color,
                     font=theme.FONT_SMALL).pack(side="right", padx=4)

        self.canvas = tk.Canvas(self, bg=theme.SURFACE, highlightthickness=0, height=140)
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
            cv.create_line(0, y, w, y, fill="#20272f")
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
