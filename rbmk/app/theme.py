"""界面主题：贴近《我的世界》1.7.10 原版 GUI 的灰石风格。

- 面板基色 #c6c6c6（物品栏底色），凹槽 #8b8b8b，凸起/凹陷用 Tk 的 raised/sunken 立体边框；
- 文字深灰 #3f3f3f，按钮灰底白字、悬停变 #ffffa0（对应原版按钮悬停）；
- 图表与堆芯画布保留深色底，配色改用原版聊天栏颜色（§c 红 / §6 金 / §b 青 / §a 绿）。
"""
# ---- 面板 ----
BG = "#b8b8b8"          # 窗口底色（面板之间）
SURFACE = "#c6c6c6"     # 面板
SURFACE2 = "#a8a8a8"    # 凹槽 / 选中行
BORDER = "#8b8b8b"      # 分隔线、凹槽边框
SLOT = "#8b8b8b"        # 槽位底
INK = "#3f3f3f"         # 正文
MUTED = "#5c5c5c"       # 次要文字

# ---- 强调色（原版聊天栏色板）----
ACCENT = "#4a6fd4"      # 主按钮 / 选中框
DANGER = "#b02e26"
OK = "#3f7d20"
CYAN = "#2b7f8f"
GOLD = "#b8860b"

# ---- 按钮（原版 widgets 贴图观感）----
BUTTON_BG = "#8b8b8b"
BUTTON_BG_HOVER = "#a6a6a6"
BUTTON_FG = "#ffffff"
BUTTON_FG_HOVER = "#ffffa0"
BUTTON_PRIMARY = "#4a6fd4"
BUTTON_PRIMARY_HOVER = "#5f80e0"

# ---- 深色画布（堆芯 / 曲线）----
GRID_BG = "#2b2b2b"
GRID_CELL = "#3a3a3a"
GRID_LINE = "#4a4a4a"
PLOT_BG = "#151515"
PLOT_GRID = "#3a3a3a"

# ---- 原版聊天栏配色，用于曲线 ----
MC_RED = "#ff5555"
MC_GOLD = "#ffaa00"
MC_AQUA = "#55ffff"
MC_GREEN = "#55ff55"

FAMILY = "SimSun"
FONT = (FAMILY, 10)
FONT_SMALL = (FAMILY, 9)
FONT_BOLD = (FAMILY, 10, "bold")
FONT_TITLE = (FAMILY, 12, "bold")
FONT_MONO = ("Consolas", 9)
