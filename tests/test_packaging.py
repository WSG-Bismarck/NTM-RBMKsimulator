"""阶段 6 打包测试：exe 存在且是有效可执行文件。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "RBMK-Simulator.exe"


def test_exe_exists_and_nonempty():
    assert EXE.exists(), "未找到 dist/RBMK-Simulator.exe，请先运行 PyInstaller"
    assert EXE.stat().st_size > 1_000_000


def test_exe_is_pe_binary():
    with open(EXE, "rb") as f:
        head = f.read(2)
    assert head == b"MZ", "不是有效的 Windows 可执行文件"


def test_source_entry_exists():
    assert (ROOT / "main.py").exists()
    assert (ROOT / "rbmk" / "app" / "main_window.py").exists()
