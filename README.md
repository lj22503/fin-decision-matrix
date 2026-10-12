---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 1c835e55ba3b06878e6538b2edadf703_a85dd567c5e811f1a08152540064ee0f
    ReservedCode1: FIoOCQeOQ87aGTPy09xM+EffcpjcVNCtVIbuTpafskvaoOoGwZD47lTbo0saCTHTaynG8jqnGiOACPkGfGuaj78aUaQl27Vs0DzJnwfTNyDRKl1MgFgbQbnoYbQDGRQRi1Y6K2MCZ42jy+0/97+L+KWQGcfi4qGNEKihHtSrC3v1E6o+5G73HjXINZ8=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 1c835e55ba3b06878e6538b2edadf703_a85dd567c5e811f1a08152540064ee0f
    ReservedCode2: FIoOCQeOQ87aGTPy09xM+EffcpjcVNCtVIbuTpafskvaoOoGwZD47lTbo0saCTHTaynG8jqnGiOACPkGfGuaj78aUaQl27Vs0DzJnwfTNyDRKl1MgFgbQbnoYbQDGRQRi1Y6K2MCZ42jy+0/97+L+KWQGcfi4qGNEKihHtSrC3v1E6o+5G73HjXINZ8=
---

# fin-decision-matrix · 普通人财务决策计算器

> 投资平权项目 · 基于「二维决策图例法」的普通人财务决策计算器模型
> 定位：让任何普通人，用两个变量就能看清一个财务决策的好坏。

## 一、项目缘起

传统理财建议要么是"道理正确但无法执行"，要么是"数据复杂看不懂"。而「二维决策图例法」（源自 D:\ObsidianVault\03-Resources\deepseek\二维决策图例法.txt 的探索）证明：

**把决策压缩为「变量 A × 变量 B → 一个清晰结论」，用户看一眼就知道该怎么选。**

典型范例就是"躺平需要多少钱"表：横轴本金、纵轴年花费，交叉格直接给出"可持续 26 年 / 花不完"——利用了人对数字不敏感、尤其是复利与乘法效应的认知弱点，把复杂计算变成"对号入座"。

本项目把这个框架产品化，聚焦**普通人的财务类决策**，打造一系列二维决策计算器。

## 二、产品双场景

| 场景 | 使用者 | 形态 | 价值 |
|---|---|---|---|
| 投顾生图端 | 投顾/理财师/内容创作者 | 输入参数一键生成决策矩阵图 | 快速给客户/读者呈现"哪里好、哪里坏"，替代口头说教 |
| 用户自选端 | 普通用户 | 输入自己的两个变量 → 直接得到结论 | 不需要懂金融公式，对号入座就知道怎么选 |

## 三、核心机制（为什么有效）

1. **两个输入变量**：用户在决策时真正权衡的两个维度（如：我有多少钱 × 我每年花多少）。
2. **明确可量化的输出**：年限、金额、等级、是/否行动建议。
3. **利用非线性认知差**：复利、杠杆、概率复合——人对指数增长不敏感，矩阵图把它变成可见、可查、可行动。
4. **结论必须可截图**：数字大字 + 对比条 + 一句扎心/安慰文案（陈锦初传播方法论，见 docs/03）。

## 四、场景覆盖路线（第一步成果）

已完成普通人财务决策全景盘点（见 [docs/01-普通人财务决策场景全景.md](docs/01-普通人财务决策场景全景.md)），按用户场景分为八大域：

1. 资产与投资（定投复利、躺平、资产配置、目标储蓄）
2. 负债与债务（最低还款陷阱、提前还款、债务策略、贷款对比）
3. 养老规划（养老储蓄、退休提取、延迟退休）
4. 买房置业（租房vs买房、首付月供、利率选择）
5. 保险配置（保额测算、产品匹配）
6. 教育与自我投资（教育金、技能回收期）
7. 日常现金流（消费降级、应急金）
8. 生命周期衔接（就业期→家庭期→退休期连续决策）

## 五、项目推进路线

| 阶段 | 内容 | 状态 |
|---|---|---|
| 第一步 | 普通人财务决策场景全景整理（按用户场景） | ✅ 已完成 |
| 第二步 | 选 2-3 个最高频场景做 MVP 计算器（含生图能力） | ⏳ 待启动 |
| 第三步 | 投顾生图端工具化（模板库 + 参数配置 + 导出分享） | ⏳ 待启动 |
| 第四步 | 用户自选端产品化（Web/小程序，营销钩子+分享卡） | ⏳ 待启动 |

## 六、关联资产

- 方法论源头：`D:\ObsidianVault\03-Resources\deepseek\二维决策图例法.txt`
- 营销方法论：`D:\ObsidianVault\03-Resources\IMA\research\`（陈锦初传播方法论系列，本项目应用篇见 docs/03 与 IMA\research）
- 投资平权生态：FinTools（fintools.mangofolio.com）、MangoForge、投资词典、RanBing 工具箱
*（内容由AI生成，仅供参考）*
