@echo off
cd /d "%~dp0"
echo === 运行测试 ===
python -m pytest -q
if errorlevel 1 (
  echo 测试失败，已停止打包。
  pause
  exit /b 1
)
echo === 打包 exe ===
python -m PyInstaller --noconfirm --onefile --windowed --name RBMK-Simulator --add-data "%~dp0rbmkssets;rbmk/assets" --add-data "%~dp0快速上手.md;." --distpath dist --workpath build --specpath build main.py
echo === 完成：dist\RBMK-Simulator.exe ===
pause
