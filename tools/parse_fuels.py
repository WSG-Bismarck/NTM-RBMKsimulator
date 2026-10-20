"""从 CFR 反编译的 ModItems.java 中提取每种 RBMK 燃料的精确参数。

输入：cf_out/ModItems.java
输出：rbmk/model/fuel_data.py（FUEL_DATA 字典）
依据：ItemRBMKRod 字段默认值 + ModItems 中逐条 .setStats/.setHeat/... 调用
"""
import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "cf_out" / "ModItems.java"
OUT = ROOT / "rbmk" / "model" / "fuel_data.py"

# ItemRBMKRod 字段默认值
DEFAULTS = {
    "reactivity": 0.0,
    "self_rate": 0.0,
    "function": "LOG_TEN",
    "dep_func": "GENTLE_SLOPE",
    "x_gen": 0.5,
    "x_burn": 50.0,
    "heat": 1.0,
    "yield": 0.0,
    "melting_point": 1000.0,
    "diffusion": 0.02,
    "n_type": "SLOW",
    "r_type": "FAST",
    "heat_coeff_start": 0.0,
    "heat_coeff_length": 0.0,
}

# 中文显示名（按命名推断；精确名可从语言文件补）
NAMES = {
    "rbmk_fuel_balefire": "RBMK反应堆野火燃料棒",
    "rbmk_fuel_balefire_gold": "RBMK反应堆激活态金-198燃料棒",
    "rbmk_fuel_drx": "RBMK反应堆F迪伽马粒子燃料棒",
    "rbmk_fuel_empty": "空 RBMK反应堆燃料棒",
    "rbmk_fuel_flashlead": "RBMK反应堆闪光铅燃料棒",
    "rbmk_fuel_hea241": "HEA-241 RBMK反应堆高浓缩度镅-241燃料棒",
    "rbmk_fuel_hea242": "HEA-242 RBMK反应堆高浓缩度镅-242燃料棒",
    "rbmk_fuel_heaus": "HEAus RBMK反应堆高浓缩度奥斯燃料棒",
    "rbmk_fuel_hen": "HEN RBMK反应堆高浓缩度镎燃料棒",
    "rbmk_fuel_hep239": "HEP-239 RBMK反应堆高浓缩度钚-239燃料棒",
    "rbmk_fuel_hep241": "HEP-241 RBMK反应堆高浓缩度钚-241燃料棒",
    "rbmk_fuel_hes": "HES RBMK反应堆高浓缩度Sa326燃料棒",
    "rbmk_fuel_heu233": "HEU-233 RBMK反应堆高浓缩度铀-233燃料棒",
    "rbmk_fuel_heu235": "HEU-235 RBMK反应堆高浓缩度铀-235燃料棒",
    "rbmk_fuel_lea": "LEA RBMK反应堆低浓缩度镅-242燃料棒",
    "rbmk_fuel_leaus": "LEAus RBMK反应堆低浓缩度奥斯燃料棒",
    "rbmk_fuel_lep": "LEP RBMK反应堆低浓缩度钚-239燃料棒",
    "rbmk_fuel_les": "LES RBMK反应堆低浓缩度Sa326燃料棒",
    "rbmk_fuel_mea": "MEA RBMK反应堆中浓缩度镅-242燃料棒",
    "rbmk_fuel_men": "MEN RBMK反应堆中浓缩度镎-237燃料棒",
    "rbmk_fuel_mep": "MEP RBMK反应堆中浓缩度钚-239燃料棒",
    "rbmk_fuel_mes": "MES RBMK中浓缩度Sa326燃料棒",
    "rbmk_fuel_meu": "MEU RBMK中浓缩度铀-235燃料棒",
    "rbmk_fuel_mox": "MOX RBMK反应堆燃料棒",
    "rbmk_fuel_po210be": "钋210-铍 RBMK反应堆中子源",
    "rbmk_fuel_pu238be": "钚238-铍 RBMK反应堆中子源",
    "rbmk_fuel_ra226be": "镭226-铍 RBMK反应堆中子源",
    "rbmk_fuel_test": "测试燃料（THE VOICES）",
    "rbmk_fuel_thmeu": "ThMEU RBMK反应堆中浓缩度铀-233导向钍燃料棒",
    "rbmk_fuel_ueu": "NU RBMK反应堆未浓缩铀燃料棒",
    "rbmk_fuel_uzh": "RBMK反应堆铀氢锆燃料棒",
    "rbmk_fuel_zfb_am_mix": "ZFB 燃料级镅RBMK反应堆燃料棒",
    "rbmk_fuel_zfb_bismuth": "ZFB 铋RBMK反应堆燃料棒",
    "rbmk_fuel_zfb_pu241": "ZFB 钚-241RBMK反应堆燃料棒",
}

NUM = r"([0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)"


def grab(pat, text):
    m = re.search(pat, text)
    return m


def parse_line(key, line):
    d = dict(DEFAULTS)
    m = grab(r"\.setYield\(" + NUM + r"\)", line)
    if m:
        d["yield"] = float(m.group(1))
    m = grab(r"\.setStats\(" + NUM + r"(?:\s*,\s*" + NUM + r")?\)", line)
    if m:
        d["reactivity"] = float(m.group(1))
        d["self_rate"] = float(m.group(2)) if m.group(2) else 0.0
    m = grab(r"\.setFunction\(ItemRBMKRod\.EnumBurnFunc\.(\w+)\)", line)
    if m:
        d["function"] = m.group(1)
    m = grab(r"\.setDepletionFunction\(ItemRBMKRod\.EnumDepleteFunc\.(\w+)\)", line)
    if m:
        d["dep_func"] = m.group(1)
    m = grab(r"\.setHeat\(" + NUM + r"\)", line)
    if m:
        d["heat"] = float(m.group(1))
    m = grab(r"\.setMeltingPoint\(" + NUM + r"\)", line)
    if m:
        d["melting_point"] = float(m.group(1))
    m = grab(r"\.setDiffusion\(" + NUM + r"\)", line)
    if m:
        d["diffusion"] = float(m.group(1))
    m = grab(r"\.setXenon\(" + NUM + r"\s*,\s*" + NUM + r"\)", line)
    if m:
        d["x_gen"] = float(m.group(1))
        d["x_burn"] = float(m.group(2))
    m = grab(r"\.setHeatCoeff\(" + NUM + r"\s*,\s*" + NUM + r"\)", line)
    if m:
        d["heat_coeff_start"] = float(m.group(1))
        d["heat_coeff_length"] = float(m.group(2))
    m = grab(r"\.setNeutronTypes\(IRBMKFluxReceiver\.NType\.(\w+)\s*,\s*IRBMKFluxReceiver\.NType\.(\w+)\)", line)
    if m:
        d["n_type"] = m.group(1)
        d["r_type"] = m.group(2)
    d["name"] = NAMES.get(key, key)
    return d


def main():
    text = SRC.read_text(encoding="utf-8")
    data = {}
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"(rbmk_fuel_[a-z0-9_]+)\s*=\s*\(ItemRBMKRod\)new ItemRBMKRod", s)
        if m:
            key = m.group(1)
            if key == "rbmk_fuel_empty":
                continue
            data[key] = parse_line(key, s)
    # 空燃料棒
    data["rbmk_fuel_empty"] = {
        **DEFAULTS, "name": NAMES["rbmk_fuel_empty"],
        "reactivity": 0.0, "self_rate": 0.0, "heat": 0.0,
        "yield": 0.0, "melting_point": 0.0, "diffusion": 0.0,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write('"""自动生成：RBMK 燃料精确参数（来自 HBM-NTM-.1.0.27_X5846.jar 反编译）。\n')
        f.write("请勿手改；改数据请改 tools/parse_fuels.py 再重新生成。\n")
        f.write('"""\n\n')
        f.write("FUEL_DATA = ")
        f.write(json.dumps(data, ensure_ascii=False, indent=2))
        f.write("\n")
    print(f"wrote {OUT} with {len(data)} fuels")


if __name__ == "__main__":
    main()
