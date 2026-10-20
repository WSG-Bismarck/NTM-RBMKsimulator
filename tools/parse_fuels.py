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
    "rbmk_fuel_empty": "空燃料棒",
    "rbmk_fuel_ueu": "低浓缩铀",
    "rbmk_fuel_meu": "中浓缩铀",
    "rbmk_fuel_heu233": "高浓缩铀-233",
    "rbmk_fuel_heu235": "高浓缩铀-235",
    "rbmk_fuel_uzh": "铀锆燃料",
    "rbmk_fuel_thmeu": "钍-中浓缩铀",
    "rbmk_fuel_lep": "低浓缩钚",
    "rbmk_fuel_mep": "中浓缩钚",
    "rbmk_fuel_hep239": "高浓缩钚-239",
    "rbmk_fuel_hep241": "高浓缩钚-241",
    "rbmk_fuel_lea": "低浓缩镅",
    "rbmk_fuel_mea": "中浓缩镅",
    "rbmk_fuel_hea241": "高浓缩镅-241",
    "rbmk_fuel_hea242": "高浓缩镅-242",
    "rbmk_fuel_men": "中浓缩镎",
    "rbmk_fuel_hen": "高浓缩镎",
    "rbmk_fuel_mox": "MOX燃料",
    "rbmk_fuel_les": "低浓缩锶",
    "rbmk_fuel_mes": "中浓缩锶",
    "rbmk_fuel_hes": "高浓缩锶",
    "rbmk_fuel_leaus": "低浓缩镅(澳)",
    "rbmk_fuel_heaus": "高浓缩镅(澳)",
    "rbmk_fuel_po210be": "钋-210/铍",
    "rbmk_fuel_ra226be": "镭-226/铍",
    "rbmk_fuel_pu238be": "钚-238/铍",
    "rbmk_fuel_balefire_gold": "妖火-金",
    "rbmk_fuel_flashlead": "闪光铅",
    "rbmk_fuel_balefire": "妖火燃料",
    "rbmk_fuel_zfb_bismuth": "ZFB铋",
    "rbmk_fuel_zfb_pu241": "ZFB钚-241",
    "rbmk_fuel_zfb_am_mix": "ZFB镅混合",
    "rbmk_fuel_drx": "DRX燃料",
    "rbmk_fuel_test": "测试燃料",
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
