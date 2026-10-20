import sys

from rbmk.app.main_window import create_app

if __name__ == "__main__":
    win, root = create_app()
    # 启动参数 --console：直接打开反应堆控制台窗口（也便于自动化验证）
    if "--console" in sys.argv:
        root.after(300, win.open_console)
    root.mainloop()
