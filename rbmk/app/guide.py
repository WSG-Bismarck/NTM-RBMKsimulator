"""「使用说明」弹窗：展示仓库里的《快速上手》文本。"""
from __future__ import annotations

import os
import sys
import tkinter as tk

from rbmk.app import theme

GUIDE_FILENAME = "快速上手.md"


def guide_path() -> str:
    """定位快速上手.md：打包后取 _MEIPASS，源码运行时取项目根目录。"""
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS", ""), GUIDE_FILENAME)
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    return os.path.join(root, GUIDE_FILENAME)


def guide_text() -> str:
    try:
        with open(guide_path(), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return "未找到《快速上手》文件。"


class GuideWindow(tk.Toplevel):
    """只读文本窗，按标题行做了轻量排版。"""

    def __init__(self, master):
        super().__init__(master)
        self.title("使用说明 — 快速上手")
        self.configure(bg=theme.BG)
        self.geometry("720x620")
        self.minsize(520, 420)

        head = tk.Frame(self, bg=theme.SURFACE, bd=2, relief="raised")
        head.pack(fill="x")
        tk.Label(head, text="使用说明", bg=theme.SURFACE, fg=theme.INK,
                 font=theme.FONT_BOLD).pack(side="left", padx=10, pady=6)
        _btn_close = tk.Button(head, text="关闭", command=self.destroy,
                               bg=theme.BUTTON_BG, fg=theme.BUTTON_FG, relief="raised", bd=2,
                               activebackground=theme.BUTTON_BG_HOVER,
                               activeforeground=theme.BUTTON_FG_HOVER,
                               font=theme.FONT_SMALL, cursor="hand2")
        _btn_close.pack(side="right", padx=8, pady=4)

        body = tk.Frame(self, bg=theme.SURFACE, bd=2, relief="sunken")
        body.pack(fill="both", expand=True, padx=8, pady=8)
        self.text = tk.Text(body, wrap="word", bg="#f4f4f4", fg=theme.INK, bd=0,
                            padx=14, pady=12, font=theme.FONT, spacing1=2, spacing3=4,
                            highlightthickness=0, cursor="arrow")
        bar = tk.Scrollbar(body, command=self.text.yview)
        self.text.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

        self.text.tag_configure("h1", font=(theme.FAMILY, 14, "bold"), spacing1=6, spacing3=8)
        self.text.tag_configure("h2", font=(theme.FAMILY, 11, "bold"), spacing1=10, spacing3=4,
                                foreground=theme.ACCENT)
        self.text.tag_configure("body", font=theme.FONT)

        self._fill(guide_text())
        self.text.configure(state="disabled")
        self.bind("<Escape>", lambda e: self.destroy())
        self.transient(master)
        self.lift()

    def _fill(self, content: str) -> None:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                self.text.insert("end", stripped[2:].strip() + "\n", "h1")
            elif stripped.startswith("## "):
                self.text.insert("end", stripped[3:].strip() + "\n", "h2")
            else:
                self.text.insert("end", line + "\n", "body")
