# -*- coding: utf-8 -*-
"""fin-decision-matrix · 计算核心

基于「二维决策图例法」的可持续年限计算引擎。
模型：固定年化实际收益率下的年金耗尽公式（4% 规则升级版）。
"""
import math
from dataclasses import dataclass


@dataclass
class MatrixResult:
    """矩阵单元格数据"""
    row_label: str          # 行标签（年花费）
    col_label: str          # 列标签（本金）
    years: float            # 可持续年数（inf 表示永续）
    display: str            # 展示文本（"花不完" / "X年"）
    level: str              # 风险档位：safe / ok / warn / danger
    color: str              # 单元格背景色


@dataclass
class ScenarioConfig:
    """场景配置（对应 scenarios/*.json）"""
    title: str
    subtitle: str
    x_name: str                     # 横轴名称（本金）
    x_unit: str
    x_values: list                  # 本金序列（万元）
    y_name: str                     # 纵轴名称（年花费）
    y_unit: str
    y_values: list                  # 年花费序列（万元）
    annual_return: float            # 年化实际收益率（已扣通胀）
    perpetual_threshold: float      # 超过该年数视为"花不完"
    disclaimer: str
    watermark: str
    # —— 陈锦初营销层（可选）——
    hook_title: str = ''            # 情绪钩子标题
    hook_line: str = ''             # 一句话副标题（10 秒可读完）
    emotion: str = ''               # 主情绪标签（后悔/幻想/焦虑/爽感/掌控感...）
    convert: dict = None            # 换算句配置 {label, unit, extra}
    share_copy: str = ''            # 可晒分享文案（含 {principal}/{spend}/{result} 占位）
    # —— 场景 2.1 信用卡最低还款专用（可选）——
    min_payment_ratio: float = 0.02   # 最低还款 = 余额 × 比例
    min_payment_floor: float = 50.0   # 最低还款下限（元）
    scenario_type: str = 'retire'     # 'retire'=躺平 / 'debt'=最低还款陷阱 / 'savings_cut'=消费降级
    savings_years: float = 20.0       # 消费降级场景：复利时间跨度（年）


CELL_COLORS = {
    'safe':   '#15803d',   # 花不完 / 永续（深绿）
    'ok':     '#22c55e',   # >=30年（绿）
    'warn':   '#f59e0b',   # 10-30年（琥珀）
    'danger': '#dc2626',   # <10年（红）
}


def sustainable_years(principal: float, annual_spend: float, rate: float) -> float:
    """资金可持续年限（年金公式）。

    principal: 初始本金（万元）
    annual_spend: 年度花费（万元）
    rate: 年化实际收益率（如 0.04）

    若年花费 <= 本金×收益率（收益覆盖花费）→ 永续（inf）。
    否则 n = log(1 + r·P/E) / log(1 + r)。
    """
    if annual_spend <= 0:
        return float('inf')
    if principal <= 0:
        return 0.0
    if annual_spend <= principal * rate:
        return float('inf')
    n = math.log(1 + rate * principal / annual_spend) / math.log(1 + rate)
    return n


def risk_level(years: float, threshold: float) -> str:
    """按可持续年限划分风险档位"""
    if math.isinf(years) or years >= threshold:
        return 'safe'
    if years >= 30:
        return 'ok'
    if years >= 10:
        return 'warn'
    return 'danger'


def format_years(years: float, threshold: float) -> str:
    """展示文本：花不完 / X年"""
    if math.isinf(years) or years >= threshold:
        return '花不完'
    if years >= 20:
        return f'{int(round(years))}年'
    return f'{years:.1f}年'


def build_matrix(cfg: ScenarioConfig) -> list:
    """构建矩阵数据：rows[年花费][本金] = MatrixResult"""
    rows = []
    for spend in cfg.y_values:
        row = []
        for principal in cfg.x_values:
            years = sustainable_years(principal, spend, cfg.annual_return)
            level = risk_level(years, cfg.perpetual_threshold)
            row.append(MatrixResult(
                row_label=f'{spend}{cfg.y_unit}',
                col_label=f'{principal}{cfg.x_unit}',
                years=years,
                display=format_years(years, cfg.perpetual_threshold),
                level=level,
                color=CELL_COLORS[level],
            ))
        rows.append(row)
    return rows


def single_result(cfg: ScenarioConfig, principal: float, spend: float) -> MatrixResult:
    """单点查询（用户自选端）：输入自己的两个变量直接出结论"""
    years = sustainable_years(principal, spend, cfg.annual_return)
    level = risk_level(years, cfg.perpetual_threshold)
    return MatrixResult(
        row_label=f'{spend}{cfg.y_unit}',
        col_label=f'{principal}{cfg.x_unit}',
        years=years,
        display=format_years(years, cfg.perpetual_threshold),
        level=level,
        color=CELL_COLORS[level],
    )


# ==================== 场景 2.1：信用卡最低还款陷阱 ====================

DEBT_COLORS = {
    'never': '#7f1d1d',   # 永不还清（深黑红，视觉冲击最强）
    'danger': '#dc2626',  # 还清需 >=30 年
    'warn':   '#f59e0b',  # 还清需 10-30 年
    'ok':     '#15803d',  # 还清需 <10 年
}


def debt_payoff_years(balance_wan: float, rate_pct: float,
                      min_ratio: float = 0.02, min_floor: float = 50.0,
                      max_years: float = 100.0):
    """信用卡只还最低还款：还清所需年数与累计利息。

    balance_wan: 债务余额（万元）
    rate_pct: 年利率（%）
    min_ratio: 最低还款 = 余额 × 比例（文档规范 1%-3%，默认 2%）
    min_floor: 最低还款下限（元，默认 50）
    max_years: 模拟上限年数（防止低利率无穷拖尾）

    返回 (years, total_interest_wan, never)：
      years: 还清所需年数；never=True 时无意义（inf）
      total_interest_wan: 累计支付利息（万元）
      never: 是否永不还清（最低还款 <= 当月利息，本金永远还不完）
    """
    B = balance_wan * 10000          # 元
    m = rate_pct / 100 / 12          # 月利率
    months = 0
    total_interest = 0.0
    max_months = int(max_years * 12)
    while B > 0.01 and months < max_months:
        interest = B * m
        pay = max(B * min_ratio, min_floor)
        if pay <= interest:
            return float('inf'), float('inf'), True
        B -= (pay - interest)
        total_interest += interest
        months += 1
    years = months / 12
    return years, total_interest / 10000, False


def debt_level(years: float, never: bool) -> str:
    """债务场景风险档位"""
    if never:
        return 'never'
    if years >= 30:
        return 'danger'
    if years >= 10:
        return 'warn'
    return 'ok'


def debt_display(years: float, never: bool) -> str:
    """债务场景单元格展示：永不还清 / X年"""
    if never:
        return '永不还清'
    if years >= 30:
        return f'{int(round(years))}年'
    return f'{years:.1f}年'


def build_debt_matrix(cfg: ScenarioConfig) -> list:
    """构建债务矩阵：行=债务余额，列=年利率"""
    rows = []
    for balance in cfg.y_values:
        row = []
        for rate in cfg.x_values:
            years, interest, never = debt_payoff_years(
                balance, rate, cfg.min_payment_ratio, cfg.min_payment_floor)
            level = debt_level(years, never)
            row.append(MatrixResult(
                row_label=f'{balance}{cfg.y_unit}',
                col_label=f'{rate}{cfg.x_unit}',
                years=years,
                display=debt_display(years, never),
                level=level,
                color=DEBT_COLORS[level],
            ))
        rows.append(row)
    return rows


def single_debt_result(cfg: ScenarioConfig, balance: float, rate: float) -> MatrixResult:
    """债务单点查询：输入自己的余额与利率直接出结论"""
    years, interest, never = debt_payoff_years(
        balance, rate, cfg.min_payment_ratio, cfg.min_payment_floor)
    level = debt_level(years, never)
    return MatrixResult(
        row_label=f'{balance}{cfg.y_unit}',
        col_label=f'{rate}{cfg.x_unit}',
        years=years,
        display=debt_display(years, never),
        level=level,
        color=DEBT_COLORS[level],
    )


# ==================== 场景 7.1：消费降级（降多少才划算） ====================

SAV_CUT_COLORS = {
    'comfort': '#065f46',   # 降幅 <=10%（深绿）无痛省
    'easy':    '#15803d',   # 降幅 <=20%（绿）轻松省
    'hard':    '#f59e0b',   # 降幅 <=30%（琥珀）明显省，开始伤生活
    'extreme': '#dc2626',   # 降幅 >30%（红）极限省
}


def savings_fv(monthly_save: float, years: float, rate: float = 0.05) -> float:
    """每月节省 → 年化复利年金终值（万元）。

    FV = 年投入 × ((1+r)^N - 1) / r，年投入 = 每月节省 × 12（年末计息）。
    """
    if monthly_save <= 0 or years <= 0:
        return 0.0
    annual_contrib = monthly_save * 12
    fv = annual_contrib * ((1 + rate) ** years - 1) / rate
    return fv / 10000


def monthly_saved(monthly_spend: float, cut_ratio: float) -> float:
    """消费降级：每月省下金额（元）= 当前月消费 × 降级幅度"""
    return monthly_spend * cut_ratio


def cut_level(cut_ratio: float) -> str:
    """按降级幅度划分决策档位（核心断点：20% 为舒适区上限）"""
    if cut_ratio <= 0.10:
        return 'comfort'
    if cut_ratio <= 0.20:
        return 'easy'
    if cut_ratio <= 0.30:
        return 'hard'
    return 'extreme'


def cut_judgment(level: str) -> str:
    """决策判词：该不该降、降到哪档的行动建议"""
    return {
        'comfort': '无痛省：不改变生活品质，直接照做',
        'easy':    '轻松省：稍微克制，推荐执行',
        'hard':    '明显省：开始影响生活，需明确目标（首付/教育金）',
        'extreme': '极限省：牺牲生活品质，不建议硬扛',
    }[level]


def savings_display(amount_wan: float) -> str:
    """金额展示：X万 / X.X万 / 元"""
    if amount_wan >= 10:
        return f'{int(round(amount_wan))}万'
    if amount_wan >= 1:
        return f'{amount_wan:.1f}万'
    return f'{int(round(amount_wan * 10000 / 100)) * 100}元'


def build_cut_matrix(cfg: ScenarioConfig) -> list:
    """构建消费降级决策矩阵：行=当前月消费，列=降级幅度

    每个单元格 = 每月省 X 元 → 固定年限后复利终值（万元），
    颜色按降级幅度断点分级（comfort/easy/hard/extreme）。
    """
    rows = []
    for spend in cfg.y_values:
        row = []
        for cut in cfg.x_values:
            save = monthly_saved(spend, cut)
            amount = savings_fv(save, cfg.savings_years, cfg.annual_return)
            level = cut_level(cut)
            row.append(MatrixResult(
                row_label=f'{spend}{cfg.y_unit}',
                col_label=f'{int(cut * 100)}%',
                years=amount,
                display=f'省{save:.0f}元 → {savings_display(amount)}',
                level=level,
                color=SAV_CUT_COLORS[level],
            ))
        rows.append(row)
    return rows


def single_cut_result(cfg: ScenarioConfig, monthly_spend: float, cut_ratio: float) -> MatrixResult:
    """消费降级单点决策：输入自己的月消费与想降的幅度，直接出结论与判词"""
    save = monthly_saved(monthly_spend, cut_ratio)
    amount = savings_fv(save, cfg.savings_years, cfg.annual_return)
    level = cut_level(cut_ratio)
    return MatrixResult(
        row_label=f'{monthly_spend}{cfg.y_unit}',
        col_label=f'{int(cut_ratio * 100)}%',
        years=amount,
        display=f'省{save:.0f}元 → {savings_display(amount)}',
        level=level,
        color=SAV_CUT_COLORS[level],
    )
