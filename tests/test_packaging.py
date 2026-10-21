"""打包检查：exe 存在且是有效可执行文件（未打包时自动跳过，保证刚克隆的仓库测试全绿）。"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "RBMK-Simulator.exe"

pytestmark = pytest.mark.skipif(
    not EXE.exists(),
    reason="尚未打包：先运行 build.bat 或 PyInstaller 生成 dist/RBMK-Simulator.exe",
)


def test_exe_exists_and_nonempty():
    assert EXE.stat().st_size > 1_000_000


def test_exe_is_pe_binary():
    with open(EXE, "rb") as f:
        head = f.read(2)
    assert head == b"MZ", "不是有效的 Windows 可执行文件"


def test_source_entry_exists():
    assert (ROOT / "main.py").exists()
    assert (ROOT / "rbmk" / "app" / "main_window.py").exists()
