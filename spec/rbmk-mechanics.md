# RBMK 机制与数值规格（从 jar 提取）

> 来源：`HBM-NTM-.1.0.27_X5846.jar`
> 内部版本：`1.0.27_X5846`（mcmod.info 确认）；MC 1.7.10
> 提取方式：解析 `.class` 常量池 + CFR 0.152 反编译（Java 8 JRE）
> 用途：模拟引擎与界面组件的唯一数据依据

## 1. 组件清单（软件中保留的 18 种 rbmk_* 方块）

来源：`com/hbm/blocks/ModBlocks`（全部 `rbmk_*` 方块）+ `assets/hbm/lang/zh_CN.lang`（标准中文名）
说明：jar 内共有 33 个 `rbmk_*` 方块；按需求排除自动装填机、ReaSim 进出水口、蒸汽导出器，以及全部控制/显示设备后，保留 18 种核心组件。

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
- 组件清单（软件保留 18 种核心组件；jar 内共 33 个 rbmk_* 方块）
- 控制棒分组（5 色）
- 燃料棒清单（34 项）
- RBMK 参数键清单（25 项）
- 中子类型（FAST/SLOW/ANY）、RBMK 类型分类

### 6.2 v1 模型实现（MODELED，待 v2 用反编译精确对齐）
- **中子学**：按“燃料反应性 × 慢化加成 ÷ (1 + 吸收 + 控制棒吸收)”计算全局反应性；局部通量 = 全局通量 × 邻域修正。
- **热**：燃料按通量产热；冷却剂带走热量；锅炉把热转为蒸汽；蒸汽驱动涡轮发电；冷凝回水。
- **燃料消耗**：燃耗随功率累积；剩余寿命 = 1 − 燃耗。
- **氙毒**：氙生成/燃耗双过程（对应 xGen / xBurn）。
- **熔毁**：燃料柱柱温 `columnHeat > maxHeat() = 1500` 触发（与燃料熔点无关）；非燃料柱不参与每 tick 熔毁判定。
- **控制棒**：全局 / 分组（5 色）/ 单根 三种调节方式。
- **数值常量**：取 `ItemRBMKRod` 字段语义（reactivity/heat/yield/meltingPoint/xGen/xBurn 等）构造各燃料参数；具体默认值见 `rbmk/model/components.py`。

### 6.3 保真度声明（v2 已更新）
- **清单类数据 100% 来自 jar**（组件/燃料/分组/参数键）。
- **燃料逐项数值已精确还原（v2）**：已用 CFR 0.152 反编译 `ModItems`，把 34 种燃料的 `setStats/setHeat/setMeltingPoint/setYield/setDiffusion/setXenon/setHeatCoeff/setNeutronTypes` 实参逐条提取，写入 `rbmk/model/fuel_data.py`（由 `tools/parse_fuels.py` 生成）。
- **反应性/燃烧/氙毒公式已精确还原**：`reactivity_function` 逐函数实现 `ItemRBMKRod.reactivityFunc` 的 9 种燃烧函数（PASSIVE/LOG_TEN/PLATEU/ARCH/SIGMOID/SQUARE_ROOT/LINEAR/QUADRATIC/EXPERIMENTAL）；氙毒按 `xenonGenFunc/xenonBurnFunc` 实现。
- **富集度衰减函数 `reactivityModByEnrichment`**（`ItemRBMKRod$1` 的 switch 映射）：
  | 函数 | 公式 |
  |---|---|
  | LINEAR | `e` |
  | STATIC | `1.0` |
  | BOOSTED_SLOPE | `e + sin((e−1)²·π)` |
  | RAISING_SLOPE | `e + sin(e·π)/2` |
  | GENTLE_SLOPE | `e + sin(e·π)/3` |
  其中 `e = yield / maxYield`，且已乘热系数 `mult`。
- **燃料中文名**取自 `assets/hbm/lang/zh_CN.lang` 的 `item.rbmk_fuel_*.name`（去掉 § 颜色码）；物品 `rbmk_fuel_hep239` 的语言键为 `rbmk_fuel_hep`；`rbmk_fuel_test` 在语言文件中无条目，显示为「测试燃料（THE VOICES）」。
- **v3 已对齐 RBMKDials 默认值**：`columnHeatFlow=0.2`、`passiveCooling=2.5`、`passiveCoolingInner=0.1`、`heatProvision=0.2`、`diffusionMod=1.0`、慢化/吸收/反射效率均为 `1.0`、`absorberHeatConversion=0.05`、`boilerHeatConsumption=0.1`、`fluxRange=5`、`columnHeight=4`。仍为模型层的只剩「锅炉供水能力」与「涡轮效率」两个聚合参数。
- 中文显示名部分仍为按命名推断，可从模组语言文件对齐。

---

## 7. 组件交互函数（v3 已还原进引擎）

来源：`RBMKNeutronHandler`、`TileEntityRBMKBase`、`TileEntityRBMKRod`、`ItemRBMKRod`、`RBMKDials$RBMKKeys`

### 7.1 中子传播（RBMKNeutronStream.runStreamInteraction）
- 燃料棒向 **4 个正方向**（东/南/西/北）各发射一条中子流，射程 `fluxRange = 5`。
- 沿射线逐格处理：
  - **空气**：穿透，不阻挡。
  - **慢化剂**：`fluxRatio *= 1 - moderatorEfficiency`（默认 1.0 → 快中子全部转为慢中子）。
  - **控制棒**：`level = 1 - 插入度`；`level > 0` → `flux *= level` 继续；`level = 0` → 全部吸收并终止。
  - **反射体**：**不产生中子热**（`TileEntityRBMKReflector` 没有任何吸热逻辑），只把中子流反射回源燃料棒；`reflectorEfficiency = 1.0`（默认）→ 全额反射，否则 `flux *= efficiency` 后继续。反射体柱温只靠四邻热传导上升。
  - **吸收体**：`columnHeat += absorberHeatConversion(0.05) * flux`（直接加在柱温上）；`absorberEfficiency = 1.0`（默认）→ 全部吸收并终止。
  - **燃料棒**：接收通量并终止射线。
- **自带慢化的组件**：`rbmk_rod_mod`、`rbmk_rod_reasim_mod`、`rbmk_control_mod` 在模组里方块属性 `moderated = true`。中子流经过/命中它们时，先执行 `ratio *= 1 - moderatorEfficiency`，再按组件类型处理（燃料接收 / 控制棒衰减）。反射体分支中，若源燃料棒自身带慢化，反射回源棒的流再慢化一次（对应 `runStreamInteraction` 里的 `moderatedCount`）。
- **ReaSim 模式**（`TileEntityRBMKRodReaSim.spreadFlux`）：
  - 普通模式：4 条正方向射线，每条 `1.0 ×` 通量，射程 `fluxRange = 5`。
  - ReaSim 模式：**8 条 45° 射线，每条 `0.75 ×` 通量**，射程同为 5；位置按 `floor(0.5 + v × i)` 步进（对角线会出现重复格，与模组一致）。
  - ReaSim 的节点扫描用半径 5 的圆形区域（`getReaSimNodes`：`x² + z² ≤ 25`），不是方形。
  - 软件里没有全局开关：与模组一致，只有 `rbmk_rod_reasim`、`rbmk_rod_reasim_mod` 这两种方块会 8 向扩散，普通燃料通道始终 4 向。
- 燃料对快/慢中子的加权（`fluxFromType`）：
  - `SLOW`：`slow + fast × 0.5`
  - `FAST`：`fast + slow × 0.3`
  - `ANY`：`fast + slow`

### 7.2 热量（TileEntityRBMKBase.moveHeat / coolPassively）
- **逐柱执行**：每根柱按**放置顺序**（模组里同一区块的 TE 在 HashMap 同桶内按加入顺序 tick）跑完自己的流程——锅炉/加热器自身逻辑 → `moveHeat` → `coolPassively` → ReaSim `boilWater`，而不是「所有柱先烧、再统一扩散」。
- 每 tick 四邻扩散：每个柱 tick 时取「自身 + 存在的四邻」的平均值 `d`，然后把 `d - 自身` 的 `columnHeatFlow(0.2)` **加到自身和每个邻柱上**（模组 `for (rbmk : rec)` 包含邻柱），因此每对相邻柱每 tick 会被互相调整两次。
- 只调整自身、或把扩散放到所有柱处理完之后，都会让燃料柱与邻柱的温度分配偏离模组。
- 被动冷却：`heat -= passiveCoolingInner(0.1) + (passiveCooling(2.5) - 0.1) × ((4 - 邻接数) / 4)`，下限 20。
- **显示口径**：每根柱在自己的 `func_145845_h` 末尾 `networkPackNT` 同步 `heat`，所以游戏里控制台/物品提示看到的是「自己 tick 结束」的快照，之后还会被后 tick 的邻柱再改一次。软件用 `Cell.shown_temp` 保存该快照供界面显示；熔毁/风险判定仍用真实的 `Cell.temp`。
- 燃料棒热链（`ItemRBMKRod.burn / updateHeat / provideHeat`，**每 tick 都执行**，与是否产热无关），且**在燃料棒自己那一根柱的 tick 内**执行（burn → updateHeat → provideHeat → moveHeat → cool → 发射中子），所以 `provideHeat` 用到的柱温可能已被先 tick 的邻柱更新过：
  - `core = rectify(core + outFlux × heat)`，`rectify` 夹在 20..1e6
  - **仅当** `core > hull`：`mid = (core - hull) / 2`；`core -= mid × diffusion × diffusionMod`；`hull += mid × diffusion × diffusionMod`（模组不做逆向传热）
  - 若 `hull > meltingPoint`：`avg = (columnHeat + hull + core) / 3`；`core = hull = columnHeat = avg`
  - 否则若 `hull > columnHeat`：`ret = (hull - columnHeat) / 2 × heatProvision(0.2)`；`hull -= ret`；`columnHeat += ret`
  - 热系数 `mult` 用**芯温**：`core >= heatCoeffStart` 时 `prog = min(1, (core - start) / length)`，`enrichment *= sin((progπ + π)/2)`
- 熔毁（本软件采用的两条并行判定，满足任一即熔毁）：
  - **任一组件柱温 > `maxHeat()` = 1500**（模组 `TileEntityRBMKRod.updateEntity` 的 `heat > maxHeat()`，`maxHeat()` 未重写、固定 1500）；
  - **燃料棒壳温 `hull_heat` > 该燃料 `meltingPoint`**（对应模组 `func_145843_s` 的壳温兜底判定，阈值改为各燃料自己的熔点）。
  - 燃料的 `meltingPoint` 不再作为柱温熔毁线；非燃料柱只走第一条。

### 7.3 锅炉（TileEntityRBMKBoiler）
- 可产 **4 种蒸汽**（中文名取自 `zh_CN.lang`）：`STEAM` 蒸汽、`HOTSTEAM` 热蒸汽、`SUPERHOTSTEAM` 超热蒸汽、`ULTRAHOTSTEAM` 超浓密蒸汽。
- `getHeatFromSteam(type)`（产汽所需最低柱温）：100 / 300 / 450 / 600。
- `getFactorFromSteam(type)`（水→蒸汽倍率）：1 / 10 / 100 / 1000。
- 每 tick：
  - `heatProvided = heat - getHeatFromSteam(type)`；≤ 0 不产汽。
  - 非超浓密：`waterUsed = min(heatProvided / 0.1, feed)`；`steamProduced = waterUsed * 100 / factor`。
  - 超浓密：`steamProduced = heatProvided / 0.1 * 100 / factor`；`waterUsed = steamProduced / 100 * factor`；供水不足时按 `feed` 反算。
  - `heat -= waterUsed * 0.1`。
- **执行顺序（与模组一致）**：锅炉 / 流体加热器先跑自身逻辑 → `moveHeat`（四邻扩散 + 被动冷却）→ ReaSim `boilWater`。因此水充足时锅炉柱温 = 蒸汽阈值 + 本 tick 从邻柱扩散进来的热量，显示上会略高于 100°C（例如 112°C），而不是恒定 100。
- 软件按**无限供水**处理（每 tick 都按满 10,000 mB 计算）；`waterUsed` 与 `steamProduced` 均按模组 `floor` 取整；每 tick 最多按 10,000 mB 水带走 1,000 热量。属性面板显示单位为 **mB/tick**。
- 每 tick 产汽上限 = 模组蒸汽罐容量 **1,000,000 mB**。
- 发电量按 `steam / 100` 折算，保持旧版标定（100 mB 蒸汽 ≈ 1 单位水）。
- 蒸汽驱动涡轮发电。

### 7.3.1 流体加热器（TileEntityRBMKHeater）
- 只处理带 `FT_Heatable` 且 `HEATEXCHANGER` 效率 > 0 的流体，取 `getFirstStep()`。
- 可用流体（9 种，中文名取自 `zh_CN.lang`）：

| 输入 | 产出 | 每次消耗 mB | 每次产出 mB | heatReq | 产出温度 | 效率 |
|---|---|---|---|---|---|---|
| 水 WATER | 蒸汽 STEAM | 1 | 100 | 200 | 100 | 0.25 |
| 原油 OIL | 热原油 HOTOIL | 1 | 1 | 10 | 350 | 1.0 |
| 脱硫原油 OIL_DS | 热的脱硫原油 HOTOIL_DS | 1 | 1 | 10 | 350 | 1.0 |
| 裂化油 CRACKOIL | 热裂化油 HOTCRACKOIL | 1 | 1 | 10 | 350 | 1.0 |
| 脱硫裂化油 CRACKOIL_DS | 热的脱硫裂化油 HOTCRACKOIL_DS | 1 | 1 | 10 | 350 | 1.0 |
| 冷却液 COOLANT | 热冷却液 COOLANT_HOT | 1 | 1 | 300 | 600 | 1.0 |
| 四氟甲烷 PERFLUOROMETHYL | 热四氟甲烷 PERFLUOROMETHYL_HOT | 1 | 1 | 300 | 250 | 1.0 |
| Mug牌树根饮料 MUG | 热的Mug牌树根饮料 MUG_HOT | 1 | 1 | 400 | 500 | 1.0 |
| 血 BLOOD | 热的血 BLOOD_HOT | 1 | 1 | 500 | 666 | 1.0 |

- 每 tick：`tempRange = heat - 产出温度`；`TU_PER_DEGREE = 2000 × eff`；
  `ops = tempRange × TU_PER_DEGREE / heatReq`；
  `heat -= heatReq × ops / TU_PER_DEGREE × eff`（化简为 `heatReq × ops / 2000`）。
- 软件把进/出罐视为无限直连，产量完全由柱温与公式决定；属性面板只显示「每刻加热流体产量」，不再提供手动上限。
- 每 tick 加热上限 = 模组输出罐容量 **16,000 mB**。
- **每刻热量产出**（属性面板显示）= `产量 × 产出流体单位热容量 × 可被冷却效率`，数据取自产出流体的 `FT_Coolable`：

| 产出流体 | heatEnergy | amountReq | HEATEXCHANGER 效率 | 单位热容量 (TU/mB) |
|---|---|---|---|---|
| 蒸汽 | 200 | 100 | 0.5 | 2 |
| 热原油 / 热的脱硫原油 | 10 | 1 | 1.0 | 10 |
| 热裂化油 / 热的脱硫裂化油 | 10 | 1 | 1.0 | 10 |
| 热冷却液 | 300 | 1 | 1.0 | 300 |
| 热四氟甲烷 | 300 | 1 | 1.0 | 300 |
| 热的Mug牌树根饮料 | 400 | 1 | 1.0 | 400 |
| 热的血 | 500 | 1 | 1.0 | 500 |

### 7.3.2 ReaSim 锅炉模式（TileEntityRBMKBase.boilWater）
- 模组开关 `dialReasimBoilers` 默认 **关闭**；开启后**每根 RBMK 柱**都按锅炉公式产汽，不再局限于蒸汽管道。
- 每 tick：`heat < 100` 不产汽；否则
  `availableHeat = (heat - 100) / 0.1`；
  `availableWater = reasimWater`（≤16000）；
  `availableSpace = 16000 - reasimSteam`；
  `processed = floor(min(availableHeat, availableWater, availableSpace) × clamp(dialReasimBoilerSpeed, 0, 1))`；
  `reasimWater -= processed`；`reasimSteam += processed`；`heat -= processed × 0.1`。
- `dialReasimBoilerSpeed` 默认 **0.05**（每 tick 只处理上限的 5%）；水→蒸汽 **1:1**（普通蒸汽管道是 1:100）；单柱上限 16,000 mB → 每 tick 最多 800 mB。
- 软件采用方案 B：不实现 ReaSim 进水口/蒸汽出口，水与蒸汽视为持续供应/排出，只保留单柱 16,000 mB 上限；顶部「锅炉：普通 / 锅炉：ReaSim」按钮切换。

### 7.4 各组件的模拟作用（v3）
| 组件 | 作用 |
|---|---|
| 燃料通道（4 种） | 接收中子 → 燃烧 → 发热 → 向 4 向发射中子 |
| 控制棒（5 种） | 按插入深度衰减/阻断中子 |
| 蒸汽管道 | 吸收热量产蒸汽 |
| 石墨慢化剂 | 快中子 → 慢中子 |
| 硼中子吸收器 | 吸收中子并自身发热 |
| 碳化钨中子反射器 | 把中子反射回源燃料棒 |
| 辐照通道 | 接收中子（用于辐照产物） |
| 冷却器 | 参与被动冷却（模型层） |
| 流体加热器 | 热源/工质加热（模型层） |
| 结构柱 / 存储棒 | 无中子作用，仅传热 |
