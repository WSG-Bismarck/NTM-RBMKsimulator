"""阶段 0 冒烟测试：包可导入、最小窗口可构建。"""
import tkinter as tk
import rbmk
from rbmk.app.main_window import create_app


def test_version():
    assert rbmk.__version__


def test_window_constructs_and_titled():
    win, root = create_app()
    try:
        root.update()
        assert root.title().startswith("RBMK 反应堆模拟器")
        # 至少有一个子控件
        assert len(root.winfo_children()) >= 1
    finally:
        root.destroy()
