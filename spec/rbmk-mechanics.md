# RBMK 机制与数值规格（从 jar 提取）

> 来源：`HBM-NTM-.1.0.27_X5846.jar`
> 内部版本：`1.0.27_X5846`（mcmod.info 确认）；MC 1.7.10
> 提取方式：解析 `.class` 常量池（无 Java 环境，未做完整反编译）
> 用途：模拟引擎与界面组件的唯一数据依据

## 1. 组件清单（ColumnType 枚举，14 种）

来源：`com/hbm/tileentity/machine/rbmk/TileEntityRBMKConsole$ColumnType`

| 枚举 | 中文名 | 说明 |
|---|---|---|
| BLANK | 空柱 | 占位 |
| FUEL | 燃料棒 | 装燃料、产热与中子 |
| FUEL_SIM | 模拟燃料棒 | 用于测试的燃料柱 |
| CONTROL | 控制棒（手动） | 可调插入深度 |
| CONTROL_AUTO | 自动控制棒 | 自动调节 |
| BOILER | 锅炉/蒸汽通道 | 热→蒸汽 |
| MODERATOR | 慢化剂（石墨） | 慢化中子 |
| ABSORBER | 中子吸收体 | 吸收中子 |
| REFLECTOR | 中子反射体 | 反射中子 |
| OUTGASSER | 除气器 | 处理气体 |
| BREEDER | 增殖柱 | 增殖燃料 |
| STORAGE | 储存柱 | 存放燃料 |
| COOLER | 冷却器 | 冷却 |
| HEATEX | 热交换器 | 换热 |

> 注：另有 `offset` 字段（列偏移），非组件类型。

## 2. 控制棒分组（RBMKColor，5 组）

来源：`com/hbm/tileentity/machine/rbmk/TileEntityRBMKControlManual$RBMKColor`

`RED`、`YELLOW`、`GREEN`、`BLUE`、`PURPLE` —— 共 5 个颜色组。
软件需支持：**全局统一调节** + **按颜色分组调节** + **单根调节**。

## 3. 燃料棒清单（ModItems 中的 rbmk_fuel_*，共 35 项）

来源：`com/hbm/items/ModItems`、`com/hbm/items/machine/ItemRBMKRod`

| 物品名 | 中文（推断） |
|---|---|
| rbmk_fuel_empty | 空燃料棒 |
| rbmk_fuel_ueu | 低浓缩铀 |
| rbmk_fuel_meu | 中浓缩铀 |
| rbmk_fuel_heu233 | 高浓缩铀-233 |
| rbmk_fuel_heu235 | 高浓缩铀-235 |
| rbmk_fuel_uzh | 铀锆燃料 |
| rbmk_fuel_thmeu | 钍-中浓缩铀 |
| rbmk_fuel_lep | 低浓缩钚 |
| rbmk_fuel_mep | 中浓缩钚 |
| rbmk_fuel_hep239 | 高浓缩钚-239 |
| rbmk_fuel_hep241 | 高浓缩钚-241 |
| rbmk_fuel_lea | 低浓缩镅 |
| rbmk_fuel_mea | 中浓缩镅 |
| rbmk_fuel_hea241 | 高浓缩镅-241 |
| rbmk_fuel_hea242 | 高浓缩镅-242 |
| rbmk_fuel_heaus | 高浓缩镅（混合） |
| rbmk_fuel_hen | 高浓缩镎 |
| rbmk_fuel_hep | 高浓缩钚（混合） |
| rbmk_fuel_hes | 高浓缩锶 |
| rbmk_fuel_men | 中浓缩镎 |
| rbmk_fuel_mes | 中浓缩锶 |
| rbmk_fuel_mox | MOX 燃料 |
| rbmk_fuel_po210be | 钋-210/铍 |
| rbmk_fuel_pu238be | 钚-238/铍 |
| rbmk_fuel_ra226be | 镭-226/铍 |
| rbmk_fuel_leaus | 低浓缩镅（混合） |
| rbmk_fuel_les | 低浓缩锶 |
| rbmk_fuel_zfb_am_mix | ZFB 镅混合 |
| rbmk_fuel_zfb_bismuth | ZFB 铋 |
| rbmk_fuel_zfb_pu241 | ZFB 钚-241 |
| rbmk_fuel_balefire | 妖火燃料 |
| rbmk_fuel_balefire_gold | 妖火-金 |
| rbmk_fuel_drx | DRX 燃料 |
| rbmk_fuel_flashlead | 闪光铅 |
| rbmk_fuel_test | 测试燃料 |

> 注：中文名为根据命名推断，精确显示名以模组语言文件为准（后续可补）。

## 4. RBMK 可调参数键（RBMKKeys，25 项）

来源：`com/hbm/tileentity/machine/rbmk/RBMKDials$RBMKKeys`

`KEY_PASSIVE_COOLING`、`KEY_PASSIVE_COOLING_INNER`、`KEY_COLUMN_HEAT_FLOW`、
`KEY_FUEL_DIFFUSION_MOD`、`KEY_HEAT_PROVISION`、`KEY_COLUMN_HEIGHT`、
`KEY_PERMANENT_SCRAP`、`KEY_BOILER_HEAT_CONSUMPTION`、`KEY_CONTROL_SPEED_MOD`、
`KEY_REACTIVITY_MOD`、`KEY_OUTGASSER_MOD`、`KEY_SURGE_MOD`、`KEY_FLUX_RANGE`、
`KEY_REASIM_RANGE`、`KEY_REASIM_BOILERS`、`KEY_REASIM_BOILER_SPEED`、
`KEY_DISABLE_MELTDOWNS`、`KEY_ENABLE_MELTDOWN_OVERPRESSURE`、`KEY_MODERATOR_EFFICIENCY`、
`KEY_ABSORBER_EFFICIENCY`、`KEY_REFLECTOR_EFFICIENCY`、`KEY_DISABLE_DEPLETION`、
`KEY_DISABLE_XENON`、`KEY_ABSORBER_HEAT_CONVERSION`

这些是游戏内的“调节旋钮”，软件中对应“反应堆设置/模拟参数”页面。

## 5. 中子/燃料相关枚举

- `IRBMKFluxReceiver$NType`：`FAST`（快中子）、`SLOW`（慢中子）、`ANY`
- `RBMKNeutronHandler$RBMKType`：`ROD`、`MODERATOR`、`CONTROL_ROD`、`REFLECTOR`、`ABSORBER`、`OUTGASSER`、`OTHER`
- `ItemRBMKRod` 字段（决定燃料特性）：`reactivity`、`selfRate`、`xGen`、`xBurn`、`heat`、`yield`、`meltingPoint`、`diffusion`、`nType`、`rType`、`colorTint`、`heatCoeffStart`、`heatCoeffLength`、`specialFluxCurve`

---

## 6. 模拟机制（v1 模型说明与保真度）

### 6.1 已从 jar 精确得到（EXACT）
- 组件类型清单（14 种）
- 控制棒分组（5 色）
- 燃料棒清单（35 项）
- RBMK 参数键清单（25 项）
- 中子类型（FAST/SLOW/ANY）、RBMK 类型分类

### 6.2 v1 模型实现（MODELED，待 v2 用反编译精确对齐）
- **中子学**：按“燃料反应性 × 慢化加成 ÷ (1 + 吸收 + 控制棒吸收)”计算全局反应性；局部通量 = 全局通量 × 邻域修正。
- **热**：燃料按通量产热；冷却剂带走热量；锅炉把热转为蒸汽；蒸汽驱动涡轮发电；冷凝回水。
- **燃料消耗**：燃耗随功率累积；剩余寿命 = 1 − 燃耗。
- **氙毒**：氙生成/燃耗双过程（对应 xGen / xBurn）。
- **熔毁**：单柱温度超过燃料熔点触发；可配置“超压熔毁”。
- **控制棒**：全局 / 分组（5 色）/ 单根 三种调节方式。
- **数值常量**：取 `ItemRBMKRod` 字段语义（reactivity/heat/yield/meltingPoint/xGen/xBurn 等）构造各燃料参数；具体默认值见 `rbmk/model/components.py`。

### 6.3 保真度声明（重要）
- **清单类数据 100% 来自 jar**（组件/燃料/分组/参数键）。
- **数值常量为 v1 建模值**：受限于当前无 Java 环境、未做完整字节码反编译，燃料的逐项精确数值（reactivity/heat/meltingPoint 等）尚未从 `ModItems` 的 `setStats/setHeat/setMeltingPoint` 调用中逐一还原。v1 以“命名层级 + 语义字段”构造合理参数，**并在验收中如实标注**，不声称已 100% 还原数值。
- v2 补全路径：引入 Vineflower/CFR 反编译 → 还原 `ModItems` 中每种燃料的 `setStats/setHeat/setYield/setMeltingPoint/setXenon` 实参 → 替换 `components.py` 中的参数表。
