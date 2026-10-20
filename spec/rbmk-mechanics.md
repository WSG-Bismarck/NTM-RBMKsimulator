# RBMK 机制与数值规格（从 jar 提取）

> 来源：`HBM-NTM-.1.0.27_X5846.jar`
> 内部版本：`1.0.27_X5846`（mcmod.info 确认）；MC 1.7.10
> 提取方式：解析 `.class` 常量池 + CFR 0.152 反编译（Java 8 JRE）
> 用途：模拟引擎与界面组件的唯一数据依据

## 1. 组件清单（可放入反应堆的 33 种 rbmk_* 方块）

来源：`com/hbm/blocks/ModBlocks`（全部 `rbmk_*` 方块）+ `assets/hbm/lang/zh_CN.lang`（标准中文名）

### 1.1 反应堆核心柱子（22）

| 方块 ID | 标准中文名 |
|---|---|
| rbmk_rod | RBMK反应堆燃料通道 |
| rbmk_rod_mod | RBMK反应堆慢化燃料通道 |
| rbmk_rod_reasim | RBMK反应堆燃料通道(ReaSim) |
| rbmk_rod_reasim_mod | RBMK反应堆慢化燃料通道(ReaSim) |
| rbmk_control | RBMK反应堆控制棒 |
| rbmk_control_auto | RBMK反应堆自动控制棒 |
| rbmk_control_mod | RBMK反应堆慢化控制棒 |
| rbmk_control_reasim | RBMK反应堆控制棒 (ReaSim) |
| rbmk_control_reasim_auto | RBMK反应堆自动控制棒 (ReaSim) |
| rbmk_boiler | RBMK反应堆蒸汽管道 |
| rbmk_moderator | RBMK反应堆石墨慢化剂 |
| rbmk_absorber | RBMK反应堆硼中子吸收器 |
| rbmk_reflector | RBMK反应堆碳化钨中子反射器 |
| rbmk_outgasser | RBMK反应堆辐照通道 |
| rbmk_storage | RBMK燃料棒存储棒 |
| rbmk_cooler | RBMK冷却器 |
| rbmk_blank | RBMK反应堆结构柱 |
| rbmk_heater | RBMK流体加热器 |
| rbmk_autoloader | RBMK燃料自动装填机 |
| rbmk_steam_inlet | RBMK ReaSim进水口 |
| rbmk_steam_outlet | RBMK ReaSim蒸汽出口 |
| rbmk_loader | RBMK反应堆蒸汽导出器 |

### 1.2 控制 / 显示设备（11）

| 方块 ID | 标准中文名 |
|---|---|
| rbmk_console | RBMK石墨式反应堆控制台 |
| rbmk_crane_console | RBMK起重机控制台 |
| rbmk_display | RBMK显示面板 |
| rbmk_display_blank | 无线红石信号空白面板 |
| rbmk_gauge | 无线红石信号流量控制器面板 |
| rbmk_graph | 无线红石信号图表面板 |
| rbmk_indicator | 无线红石信号指示灯 |
| rbmk_key_pad | 无线红石信号按钮面板 |
| rbmk_lever | 无线红石信号拉杆 |
| rbmk_numitron | 无线红石信号数字显示器 |
| rbmk_terminal | 无线红石信号发信终端 |

> 说明：
> - 其余 `rbmk_*` 方块（`rbmk_top` / `rbmk_blank_top` / `rbmk_element*` / `rbmk_smooth` / `rbmk_debris*`）是柱顶、内部元素、装饰或残骸，不作为独立组件。
> - 旧版 `TileEntityRBMKConsole$ColumnType`（14 种）是控制台内部用于分类的枚举，与实际可放置方块不是一一对应；本清单已按 ModBlocks 替换。

## 2. 控制棒分组（RBMKColor，5 组）

来源：`com/hbm/tileentity/machine/rbmk/TileEntityRBMKControlManual$RBMKColor`

`RED`、`YELLOW`、`GREEN`、`BLUE`、`PURPLE` —— 共 5 个颜色组。
软件需支持：**全局统一调节** + **按颜色分组调节** + **单根调节**。

## 3. 燃料棒清单（ModItems 中的 rbmk_fuel_*，共 34 项）

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
- 组件清单（33 种：22 核心 + 11 控制/显示）
- 控制棒分组（5 色）
- 燃料棒清单（34 项）
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

### 6.3 保真度声明（v2 已更新）
- **清单类数据 100% 来自 jar**（组件/燃料/分组/参数键）。
- **燃料逐项数值已精确还原（v2）**：已用 CFR 0.152 反编译 `ModItems`，把 34 种燃料的 `setStats/setHeat/setMeltingPoint/setYield/setDiffusion/setXenon/setHeatCoeff/setNeutronTypes` 实参逐条提取，写入 `rbmk/model/fuel_data.py`（由 `tools/parse_fuels.py` 生成）。
- **反应性/燃烧/氙毒公式已精确还原**：`reactivity_function` 逐函数实现 `ItemRBMKRod.reactivityFunc` 的 9 种燃烧函数（PASSIVE/LOG_TEN/PLATEU/ARCH/SIGMOID/SQUARE_ROOT/LINEAR/QUADRATIC/EXPERIMENTAL）；氙毒按 `xenonGenFunc/xenonBurnFunc` 实现。
- **仍为模型层的部分**：全局通量标度 `base_flux`、热工系数 `heat_coeff/cooling_coeff`、慢化/反射/吸收/控制棒效率——这些是反应堆级的聚合参数，尚未逐项对齐 `RBMKDials` 默认值（需进一步解析 GameRules 默认值）。
- 中文显示名部分仍为按命名推断，可从模组语言文件对齐。
