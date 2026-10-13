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
    scenario_type: str = 'retire'     # 'retire'=躺平 / 'debt'=最低还款陷阱 / 'savings_cut'=消费降级 / 'prepay'=房贷提前还款
    savings_years: float = 20.0       # 消费降级场景：复利时间跨度（年）
    # —— 场景 2.2 房贷提前还款专用（可选）——
    loan_rate_pct: float = 3.9        # 房贷年利率（LPR 假设，%）
    loan_years: float = 30.0          # 原始贷款年限（年）


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


# ==================== 场景 2.2：房贷提前还款（每月多还一点，省多少利息） ====================

PREPAY_COLORS = {
    'big_save':   '#065f46',   # 节省利息 >=50%（深绿）强烈建议
    'save':       '#15803d',   # 节省利息 30-50%（绿）划算
    'moderate':   '#f59e0b',   # 节省利息 10-30%（琥珀）一般
    'minor':      '#dc2626',   # 节省利息 <10%（红）不值得
}


def annuity_monthly_payment(principal_wan: float, rate_pct: float, years: float) -> float:
    """等额本息月供（元）：
    M = P × r × (1+r)^n / ((1+r)^n - 1)，P=本金（元），r=月利率，n=还款月数。
    """
    if years <= 0:
        return 0.0
    P = principal_wan * 10000
    r = rate_pct / 100 / 12
    n = int(round(years * 12))
    if r == 0:
        return P / n
    return P * r * (1 + r) ** n / ((1 + r) ** n - 1)


def prepay_sim(principal_wan: float, rate_pct: float, years: float, extra_monthly: float):
    """提前还款模拟：每月按等额本息月供 + 额外还款，计算还清年限与总利息（万元）。

    返回 (months, total_interest_wan, monthly_payment)：
      months: 还清所需月数（0 表示参数非法）
      total_interest_wan: 累计支付利息（万元）
      monthly_payment: 原始月供（元，不含额外还款）
    """
    P = principal_wan * 10000
    r = rate_pct / 100 / 12
    n = int(round(years * 12))
    if P <= 0 or n <= 0:
        return 0, 0.0, 0.0
    if r == 0:
        monthly_payment = P / n
        # 无利息，额外还款只是缩短期限
        months = n
        while months > 1 and P - monthly_payment * months - extra_monthly * (n - months) > 0:
            months -= 1
        total_interest = 0.0
        return months, total_interest, monthly_payment
    monthly_payment = annuity_monthly_payment(principal_wan, rate_pct, years)
    balance = P
    months = 0
    total_interest = 0.0
    while balance > 0.01 and months < n:
        interest = balance * r
        principal_part = monthly_payment - interest
        if principal_part <= 0:
            # 极端情况：月供不足以覆盖利息（不会发生在等额本息正常贷款中）
            break
        balance -= (principal_part + extra_monthly)
        total_interest += interest
        months += 1
        if balance < 0:
            balance = 0
    return months, total_interest / 10000, monthly_payment


def prepay_base_interest(principal_wan: float, rate_pct: float, years: float) -> float:
    """不提前还款时的总利息（万元）"""
    months, interest, _ = prepay_sim(principal_wan, rate_pct, years, 0.0)
    return interest


def prepay_save_ratio(principal_wan: float, rate_pct: float, years: float, extra_monthly: float) -> float:
    """提前还款节省利息比例：0-1，0 表示不省"""
    base = prepay_base_interest(principal_wan, rate_pct, years)
    if base <= 0:
        return 0.0
    _, interest, _ = prepay_sim(principal_wan, rate_pct, years, extra_monthly)
    return max(0.0, min(1.0, (base - interest) / base))


def prepay_level(save_ratio: float) -> str:
    """提前还款决策档位"""
    if save_ratio >= 0.5:
        return 'big_save'
    if save_ratio >= 0.3:
        return 'save'
    if save_ratio >= 0.1:
        return 'moderate'
    return 'minor'


def prepay_judgment(level: str) -> str:
    """提前还款决策判词"""
    return {
        'big_save': '强烈建议：利息砍半以上，越早还越赚',
        'save':     '划算：明显省钱，可优先安排',
        'moderate': '一般：省钱有限，可结合现金流决定',
        'minor':    '不值得：省不了多少，不如拿去理财',
    }[level]


def build_prepay_matrix(cfg: ScenarioConfig) -> list:
    """构建提前还款决策矩阵：行=贷款余额，列=每月额外还款

    单元格 = 还清年限（年）+ 节省利息（万元），颜色按节省利息比例分级。
    """
    rows = []
    for principal in cfg.y_values:
        row = []
        base_interest = prepay_base_interest(principal, cfg.loan_rate_pct, cfg.loan_years)
        for extra in cfg.x_values:
            months, interest, _ = prepay_sim(principal, cfg.loan_rate_pct, cfg.loan_years, extra)
            years = months / 12
            saved = max(0.0, base_interest - interest)
            ratio = prepay_save_ratio(principal, cfg.loan_rate_pct, cfg.loan_years, extra)
            level = prepay_level(ratio)
            if extra == 0:
                display = f'{int(round(years))}年 · 利息{base_interest:.0f}万'
            else:
                display = f'{years:.0f}年 · 省{saved:.0f}万'
            row.append(MatrixResult(
                row_label=f'{principal}{cfg.y_unit}',
                col_label=f'{extra:.0f}元/月',
                years=years,
                display=display,
                level=level,
                color=PREPAY_COLORS[level],
            ))
        rows.append(row)
    return rows


def single_prepay_result(cfg: ScenarioConfig, principal_wan: float, extra_monthly: float) -> MatrixResult:
    """提前还款单点决策：输入贷款余额与每月额外还款，直接出结论"""
    base_interest = prepay_base_interest(principal_wan, cfg.loan_rate_pct, cfg.loan_years)
    months, interest, monthly_payment = prepay_sim(
        principal_wan, cfg.loan_rate_pct, cfg.loan_years, extra_monthly)
    years = months / 12
    saved = max(0.0, base_interest - interest)
    ratio = prepay_save_ratio(principal_wan, cfg.loan_rate_pct, cfg.loan_years, extra_monthly)
    level = prepay_level(ratio)
    if extra_monthly == 0:
        display = f'{int(round(years))}年 · 利息{base_interest:.0f}万'
    else:
        display = f'{years:.0f}年 · 省{saved:.0f}万'
    return MatrixResult(
        row_label=f'{principal_wan}{cfg.y_unit}',
        col_label=f'{extra_monthly:.0f}元/月',
        years=years,
        display=display,
        level=level,
        color=PREPAY_COLORS[level],
    )


# ==================== 场景 6.2：技能投资回收期（这笔学费，值不值？） ====================

TUITION_COLORS = {
    'fast':  '#065f46',   # 回本 <=12 个月（深绿）闭眼投
    'good':  '#15803d',   # 回本 12-24 个月（绿）划算
    'okay':  '#f59e0b',   # 回本 24-36 个月（琥珀）一般
    'slow':  '#dc2626',   # 回本 >36 个月（红）不值得
}


def tuition_payback_months(tuition_wan: float, salary_rise: float) -> float:
    """技能投资回收期（月）= 学费(元) / 月薪涨幅(元/月)

    tuition_wan: 学费/投入（万元）
    salary_rise: 预期月薪涨幅（元/月）
    """
    if tuition_wan <= 0 or salary_rise <= 0:
        return float('inf')
    return tuition_wan * 10000 / salary_rise


def tuition_level(payback_months: float) -> str:
    """学费决策档位（核心断点：12 个月血赚、24 个月划算、36 个月需谨慎）"""
    if payback_months <= 12:
        return 'fast'
    if payback_months <= 24:
        return 'good'
    if payback_months <= 36:
        return 'okay'
    return 'slow'


def tuition_judgment(level: str) -> str:
    """学费决策判词"""
    return {
        'fast':  '闭眼投：一年内回本，剩下的全是赚的',
        'good':  '划算：两年内回本，值得认真考虑',
        'okay':  '一般：两三年才回本，谨慎对比机会成本',
        'slow':  '不值得：回本太慢，不如先存钱再学',
    }[level]


def tuition_display(payback_months: float) -> str:
    """回本周期展示：X 个月 / X.X 年"""
    if math.isinf(payback_months):
        return '回不了本'
    if payback_months < 24:
        return f'{int(round(payback_months))}个月回本'
    return f'{payback_months / 12:.1f}年回本'


def tuition_extra_gain(tuition_wan: float, salary_rise: float, horizon_years: float = 5.0) -> float:
    """回本后 X 年累计多赚（万元）= 月薪涨幅 × 12 × 年限"""
    if salary_rise <= 0:
        return 0.0
    return salary_rise * 12 * horizon_years / 10000


def build_tuition_matrix(cfg: ScenarioConfig) -> list:
    """构建学费回收期决策矩阵：行=学费投入，列=预期月薪涨幅

    单元格 = 回本周期 + 回本后 5 年累计多赚，颜色按回本周期分级。
    """
    rows = []
    for tuition in cfg.y_values:
        row = []
        for rise in cfg.x_values:
            months = tuition_payback_months(tuition, rise)
            gain = tuition_extra_gain(tuition, rise)
            level = tuition_level(months)
            display = f'{tuition_display(months)} · 后5年多赚{gain:.0f}万'
            row.append(MatrixResult(
                row_label=f'{tuition}{cfg.y_unit}',
                col_label=f'+{rise:.0f}元/月',
                years=months,
                display=display,
                level=level,
                color=TUITION_COLORS[level],
            ))
        rows.append(row)
    return rows


def single_tuition_result(cfg: ScenarioConfig, tuition_wan: float, salary_rise: float) -> MatrixResult:
    """学费单点决策：输入学费与预期月薪涨幅，直接出结论"""
    months = tuition_payback_months(tuition_wan, salary_rise)
    gain = tuition_extra_gain(tuition_wan, salary_rise)
    level = tuition_level(months)
    return MatrixResult(
        row_label=f'{tuition_wan}{cfg.y_unit}',
        col_label=f'+{salary_rise:.0f}元/月',
        years=months,
        display=f'{tuition_display(months)} · 后5年多赚{gain:.0f}万',
        level=level,
        color=TUITION_COLORS[level],
    )


# ==================== 场景 7.2：应急金（我该留多少救命钱？） ====================

EMERGENCY_COLORS = {
    'bare': '#dc2626',      # 不足 3 个月：赤贫级
    'minimal': '#f59e0b',   # 3-6 个月：底线
    'standard': '#22c55e',  # 6-9 个月：标准
    'solid': '#15803d',     # 9-12 个月：稳健
    'plenty': '#065f46',    # 12 个月以上：充裕
}


def emergency_fund_need(monthly_expense_wan: float, months: float) -> float:
    """建议应急金（万元）= 月固定支出 × 安全月数"""
    return monthly_expense_wan * months


def emergency_level(months: float) -> str:
    """应急金安全月数档位"""
    if months < 3:
        return 'bare'
    if months < 6:
        return 'minimal'
    if months < 9:
        return 'standard'
    if months <= 12:
        return 'solid'
    return 'plenty'


def emergency_judgment(level: str) -> str:
    """应急金决策判词"""
    return {
        'bare': '不够 3 个月——突发开支一来就崩，先停掉非必要消费补坑。',
        'minimal': '3-6 个月——勉强够底，但失业 3 个月就要吃土，建议提到 6 个月。',
        'standard': '6-9 个月——安全感及格线，单收入家庭可以稳。',
        'solid': '9-12 个月——很稳，双收入或想从容跳槽都够用。',
        'plenty': '12 个月以上——现金过多会跑输通胀，超出部分可转低波理财。',
    }[level]


def emergency_display(need_wan: float, months: float) -> str:
    """应急金展示文本"""
    if months < 3:
        return f'留{need_wan:.0f}万（不足3个月）'
    return f'留{need_wan:.0f}万（{months:.0f}个月支出）'


def build_emergency_matrix(cfg: ScenarioConfig) -> list:
    """构建应急金决策矩阵：行=月固定支出，列=目标安全月数

    单元格 = 建议应急金 + 安全月数，颜色按安全月数档位分级。
    """
    rows = []
    for expense in cfg.y_values:
        row = []
        for months in cfg.x_values:
            need = emergency_fund_need(expense, months)
            level = emergency_level(months)
            display = f'{need:.0f}万 · {months:.0f}个月'
            row.append(MatrixResult(
                row_label=f'{expense}{cfg.y_unit}/月',
                col_label=f'{months:.0f}个月',
                years=months,
                display=display,
                level=level,
                color=EMERGENCY_COLORS[level],
            ))
        rows.append(row)
    return rows


def single_emergency_result(cfg: ScenarioConfig, monthly_expense_wan: float, safety_months: float) -> MatrixResult:
    """应急金单点决策：输入月固定支出与目标安全月数，直接出结论"""
    need = emergency_fund_need(monthly_expense_wan, safety_months)
    level = emergency_level(safety_months)
    return MatrixResult(
        row_label=f'{monthly_expense_wan}{cfg.y_unit}/月',
        col_label=f'{safety_months:.0f}个月',
        years=safety_months,
        display=f'{need:.0f}万 · {safety_months:.0f}个月',
        level=level,
        color=EMERGENCY_COLORS[level],
    )
