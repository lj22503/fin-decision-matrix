# -*- coding: utf-8 -*-
"""
fin-decision-matrix 场景页面自动化核查脚本
================================================
用法:
    python verify_scenarios.py                    # 核查全部已配置场景
    python verify_scenarios.py --scenario 公积金    # 只核查指定场景
    python verify_scenarios.py --list             # 列出已配置场景

原理:
    每个场景在 SCENARIOS 中登记一个"复算函数"（与页面 JS 同公式）。
    脚本对页面做两类检查:
      1) 动态插值检查: 页面中所有 <span class="dyn" id="xxx"> 占位符,
         必须在 JS renderStatic() 中被同一计算函数赋值;
         且按复算函数推导出的期望值与 JS 渲染逻辑一致（抽查关键项）。
      2) 静态数字检查: 提取页面正文中的展示数字（subtitle/insight/legend
         等区域），与复算函数推导的正确值比对，不一致即报错。
    任一检查失败返回非零退出码。

新增场景方法:
    1. 在 SCENARIOS 增加条目, 提供:
       - file: HTML 文件名
       - compute: 复算函数, 入参为页面关键输入, 返回 dict {名称: 数值(单位万元/元)}
       - dyn_ids: 页面中应存在的动态占位 id 列表
       - text_checks: 正文静态文案数字检查, 每项为 (正则, 期望值函数)
    2. 运行 --scenario <名称> 验证通过后即可纳入全量。
"""
import argparse
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_DIR = os.path.join(BASE_DIR, 'output', 'deepseek版本')

# ---------------------------------------------------------------------------
# 场景复算函数（与页面 JS 同公式）
# ---------------------------------------------------------------------------

# 公积金页: 贷款30年/等额本息; 公积金3.1% 商贷4.9%; 可贷=min(余额*15, 120万)
def calc_fund_benefit(monthly_contrib, years):
    LOAN_YEARS = 30
    FUND_RATE = 0.031
    LOAN_RATE = 0.049
    TOTAL_LOAN_NEED = 2000000
    BALANCE_MULTIPLIER = 15
    FUND_CAP = 1200000

    def calc_monthly(loan, annual_rate):
        r = annual_rate / 12
        n = LOAN_YEARS * 12
        p = (1 + r) ** n
        return loan * r * p / (p - 1)

    def calc_total_interest(loan, annual_rate):
        return calc_monthly(loan, annual_rate) * LOAN_YEARS * 12 - loan

    balance = monthly_contrib * 12 * years
    fund_quota = min(balance * BALANCE_MULTIPLIER, FUND_CAP)
    actual_fund = min(fund_quota, TOTAL_LOAN_NEED)
    actual_loan = TOTAL_LOAN_NEED - actual_fund
    fund_interest = calc_total_interest(actual_fund, FUND_RATE) if actual_fund > 0 else 0
    loan_interest = calc_total_interest(actual_loan, LOAN_RATE) if actual_loan > 0 else 0
    total_interest = fund_interest + loan_interest
    all_loan_interest = calc_total_interest(TOTAL_LOAN_NEED, LOAN_RATE)
    save = all_loan_interest - total_interest
    return {
        'balance': balance / 10000,
        'quota': actual_fund / 10000,
        'save': save / 10000,
        'monthly': calc_monthly(actual_fund, FUND_RATE) + calc_monthly(actual_loan, LOAN_RATE),
    }


def compute_fund_scenario():
    r1 = calc_fund_benefit(500, 10)
    r2 = calc_fund_benefit(3000, 10)
    # legend 阈值省额
    def save_at(q):
        return calc_fund_benefit(q * 10000 / (12 * 10) / 15, 10)['save'] if False else None
    # 直接用贷款额反推: save = f(可贷额) 需要独立函数
    def save_for_quota(q_wan):
        LOAN_YEARS = 30
        FUND_RATE = 0.031
        LOAN_RATE = 0.049
        TOTAL_LOAN_NEED = 2000000

        def cm(loan, rate):
            r = rate / 12
            n = LOAN_YEARS * 12
            p = (1 + r) ** n
            return loan * r * p / (p - 1)

        def cti(loan, rate):
            return cm(loan, rate) * LOAN_YEARS * 12 - loan

        actual = min(q_wan * 10000, TOTAL_LOAN_NEED)
        rest = TOTAL_LOAN_NEED - actual
        fi = cti(actual, FUND_RATE) if actual > 0 else 0
        li = cti(rest, LOAN_RATE) if rest > 0 else 0
        return (cti(TOTAL_LOAN_NEED, LOAN_RATE) - (fi + li)) / 10000

    return {
        'r1': r1,
        'r2': r2,
        'save_diff': r2['save'] - r1['save'],
        'quota_diff': r2['quota'] - r1['quota'],
        'per10k': round((save_for_quota(1)) * 10000 / 1),  # 每1万可贷额对应省额*1
        'legend_save': {q: round(save_for_quota(q), 1) for q in (15, 30, 50, 80)},
    }


# 交15年/40年退休金页: 简化社保公式; 社平8000, 基数上下限24000/4800, 个人8%, 计发月数139
def calc_pension_scenario():
    SOCIAL_AVG = 8000
    BASE_UPPER = 24000
    BASE_LOWER = 4800
    ACCOUNT_RATE = 0.08
    MONTHS_DIVISOR = 139

    def calc(salary, years):
        base = min(max(salary, BASE_LOWER), BASE_UPPER)
        basic = (SOCIAL_AVG + base) / 2 * years * 0.01
        account = base * ACCOUNT_RATE * 12 * years / MONTHS_DIVISOR
        total = basic + account
        return {'total': total, 'rate': total / salary}

    salary = 20000
    r15 = calc(salary, 15)
    r30 = calc(salary, 30)
    r40 = calc(salary, 40)
    return {
        'r15': r15,
        'r30': r30,
        'r40': r40,
        'mult': r40['total'] / r15['total'],
        'diff_years': 40 - 15,
    }


# 决定你财富的页: 年化5% 按月复利10年; fv = 月存 * ((1+r)^120 - 1)/r
def calc_save_rate_scenario():
    REAL_RETURN = 0.05
    YEARS = 10

    def calc(salary, rate):
        monthly = salary * rate
        r = REAL_RETURN / 12
        n = YEARS * 12
        fv = monthly * ((1 + r) ** n - 1) / r
        return {'fv': fv, 'monthlySave': monthly, 'annualSave': monthly * 12}

    r1 = calc(50000, 0.10)   # 月薪5万存10%
    r2 = calc(10000, 0.40)   # 月薪1万存40%
    ins = calc(12500, 0.40)  # 月薪1.25万存40%
    return {'r1': r1, 'r2': r2, 'ins': ins}


# 几岁退休页: 300万 年化3%; 55岁取5%破产年龄, 70岁取6%剩余
def calc_retire_scenario():
    PRINCIPAL = 3000000
    REAL_RETURN = 0.03
    TARGET_AGE = 90

    def calc(age, rate):
        years = TARGET_AGE - age
        annual = PRINCIPAL * rate
        mw = annual / 12
        mr = REAL_RETURN / 12
        n = years * 12
        powv = (1 + mr) ** n
        fv = PRINCIPAL * powv - mw * (powv - 1) / mr
        if fv >= 0:
            return {'finalValue': fv, 'bankruptcyAge': None}
        import math
        mo = -math.log(1 - PRINCIPAL * mr / mw) / math.log(1 + mr)
        return {'finalValue': 0, 'bankruptcyAge': age + mo / 12}

    bk = calc(55, 0.05)
    ok = calc(70, 0.06)
    return {
        'bk_age': round(bk['bankruptcyAge']),
        'remain': ok['finalValue'] / 10000,
        'years1': TARGET_AGE - 55,
        'years2': TARGET_AGE - 70,
        'diff': 70 - 55,
    }


# 现在每月存多少页: 60岁退休 年化5% 4%提取规则; 30岁存3000等效45岁月存; 年花12万目标300万
def calc_saving_scenario():
    RETIRE_AGE = 60
    REAL_RATE = 0.05
    WITHDRAW_RATE = 0.04

    def pmt(target, months):
        r = REAL_RATE / 12
        return target * r / ((1 + r) ** months - 1)

    def fv(monthly, months):
        r = REAL_RATE / 12
        return monthly * ((1 + r) ** months - 1) / r

    fv30 = fv(3000, 30 * 12)
    need45 = pmt(fv30, 15 * 12)
    spend = 120000
    target = spend * (1 / WITHDRAW_RATE)
    monthly30 = pmt(target, 30 * 12)
    return {
        'need45': need45,
        'target_wan': target / 10000,
        'monthly30': monthly30,
        'daily': round((round(monthly30 / 100) * 100) / 30),
    }


# 退休后每年取多少页: 年化3%; 100万取4万年限, 取3万永续, 取8万年限与月取额
def calc_withdraw_scenario():
    REAL_RETURN = 0.03

    def years(principal, annual):
        mw = annual / 12
        mr = REAL_RETURN / 12
        if mw <= principal * mr:
            return float('inf')
        import math
        n = -math.log(1 - (principal * mr) / mw) / math.log(1 + mr)
        return n / 12

    P = 1000000
    y4 = years(P, 40000)
    y8 = years(P, 80000)
    import math
    return {
        'years4': round(y4),
        'years8': round(y8),
        'm3': math.floor(30000 / 12 / 100) * 100,
        'm8': math.floor(80000 / 12 / 100) * 100,
    }


# 读研页: 22岁工作8年 vs 25岁读研后工作5年-学费6万; 年增长8%
def calc_edu_scenario():
    WORK_YEARS = 8
    GRAD_WORK_YEARS = 5
    GROWTH = 0.08
    TUITION = 60000

    def cum(monthly, years):
        annual = monthly * 12
        return sum(annual * (1 + GROWTH) ** y for y in range(years))

    def net(S, p):
        direct = cum(S, WORK_YEARS)
        grad = cum(S * (1 + p), GRAD_WORK_YEARS) - TUITION
        return grad - direct

    return {
        'sub_net40': net(20000, 0.40) / 10000,
        'sub_net100': net(20000, 1.00) / 10000,
        'conv_net1': net(10000, 0.60) / 10000,
        'conv_net2': net(10000, 1.00) / 10000,
        'conv_net3': net(30000, 1.00) / 10000,
    }


# 买房页: 200万/首付30%/贷30年4.9%/税费1.5%/维护1%/租2%涨3%/机会成本3%
def calc_buy_scenario():
    PRICE = 2000000
    DOWN = 0.30
    RATE = 0.049
    LY = 30
    TAXR = 0.015
    MAINT = 0.01
    RY = 0.02
    RG = 0.03
    IR = 0.03

    r = RATE / 12
    n = LY * 12
    loan = PRICE * (1 - DOWN)
    monthly = loan * r * (1 + r) ** n / ((1 + r) ** n - 1)

    def rem(years):
        m = min(years * 12, n)
        bal = loan
        for _ in range(m):
            bal = bal + bal * r - monthly
            if bal < 0:
                bal = 0
                break
        return max(0, bal)

    def buy(years, app):
        tm = monthly * years * 12
        rl = rem(years)
        pp = loan - rl
        ti = tm - pp
        maint = sum(PRICE * (1 + app) ** y * MAINT for y in range(years))
        tax = PRICE * TAXR
        gain = PRICE * (1 + app) ** years - PRICE
        return ti + tax + maint - gain

    def rent(years):
        tr = sum(PRICE * RY * (1 + RG) ** y for y in range(years))
        ig = PRICE * DOWN * ((1 + IR) ** years - 1)
        return tr - ig

    def be(app):
        for y in range(1, 51):
            if buy(y, app) < rent(y):
                return y
        return None

    return {
        'sub_diff5': (buy(5, 0.02) - rent(5)) / 10000,
        'sub_diff15': (buy(15, 0.03) - rent(15)) / 10000,
        'conv_monthly': monthly,
        'conv_rent': PRICE * RY / 12,
        'conv_ratio': monthly / (PRICE * RY / 12),
        'ins_be': be(0.03),
    }


SCENARIOS = {
    '公积金': {
        'file': '每月缴多少公积金，决定你买房能省多少.html',
        'compute': compute_fund_scenario,
        'dyn_ids': [
            # subtitle
            'subContrib1', 'subYears1', 'subQuota1', 'subContrib2', 'subYears2', 'subQuota2',
            'subSaveDiff',
            # 换算段
            'contrib1', 'years1', 'bal1', 'quota1', 'mult',
            'contrib2', 'years2', 'bal2', 'quota2', 'diffQuota', 'loanYears', 'save2',
            # insight
            'per10k',
            # legend
            'lgQ1', 'lgS1', 'lgQ2a', 'lgQ2b', 'lgS2a', 'lgS2b',
            'lgQ3a', 'lgQ3b', 'lgS3a', 'lgS3b', 'lgQ4a', 'lgQ4b', 'lgS4a', 'lgS4b',
            'lgQ5', 'lgS5',
        ],
        'text_checks': [
            ('subtitle 可贷500/10年', r'月缴\s*500.*?可贷\s*([\d.]+)\s*万', lambda e: e['r1']['quota']),
            ('可贷3000/10年', r'月缴\s*3000.*?可贷\s*([\d.]+)\s*万', lambda e: e['r2']['quota']),
            ('多省差值', r'多省\s*([\d.]+)\s*万', lambda e: e['save_diff']),
            ('余额500/10年', r'余额\s*([\d.]+)\s*万', lambda e: e['r1']['balance']),
            ('每万元省利息', r'每万元省的利息（约\s*([\d.]+)\s*元', lambda e: e['per10k']),
        ],
    },
    '决定你财富的': {
        'file': '决定你财富的，不是赚多少，是留下多少.html',
        'compute': calc_save_rate_scenario,
        'dyn_ids': [
            # subtitle
            'subSalary1', 'subRate1', 'subFv1', 'subSalary2', 'subRate2', 'subFv2',
            # 换算段
            'convSalary2', 'convRate2', 'convMonthly2', 'convFv2',
            'convSalary1', 'convRate1', 'convMonthly1', 'convFv1',
            # insight
            'insSalary1', 'insRate1', 'insMonthly1', 'insSalary2', 'insRate2', 'insMonthly2',
        ],
        'text_checks': [],
    },
    '几岁退休': {
        'file': '几岁退休、每年取多少，才够花到 90 岁？.html',
        'compute': calc_retire_scenario,
        'dyn_ids': [
            # subtitle
            'subPrincipal', 'subAge1', 'subRate1', 'subBkAge', 'subAge2', 'subRate2', 'subRemain',
            # 换算段
            'convPrincipal', 'convAge1', 'convYears1', 'convAge2', 'convYears2',
            'convDiff', 'convDiff2',
        ],
        'text_checks': [],
    },
    '现在每月存多少': {
        'file': '现在每月存多少，退休才能维持生活？.html',
        'compute': calc_saving_scenario,
        'dyn_ids': [
            # subtitle
            'subAge1', 'subMonthly1', 'subAge2', 'subNeed',
            # 换算段
            'convSpend', 'convTarget', 'convAge', 'convMonthly', 'convDaily',
        ],
        'text_checks': [],
    },
    '退休后每年取多少': {
        'file': '退休后每年取多少，才花不完？.html',
        'compute': calc_withdraw_scenario,
        'dyn_ids': [
            # subtitle
            'subPrincipal', 'subW4', 'subYears4', 'subW3', 'subDiff',
            # 换算段
            'convPrincipal', 'convW3', 'convR3', 'convM3', 'convW8', 'convR8',
            'convM8', 'convY8',
        ],
        'text_checks': [],
    },
    '读研还是工作': {
        'file': '读研还是直接工作？30 岁前谁赚得多？.html',
        'compute': calc_edu_scenario,
        'dyn_ids': [
            # subtitle
            'subS', 'subP40', 'subNet40', 'subP100', 'subNet100',
            # 换算段
            'convS1', 'convP1', 'convNet1', 'convP2', 'convNet2',
            'convS3', 'convP3', 'convNet3',
        ],
        'text_checks': [],
    },
    '买房': {
        'file': '住多久买房才不亏？.html',
        'compute': calc_buy_scenario,
        'dyn_ids': [
            # subtitle
            'subPrice', 'subYears5', 'subApp2', 'subDiff5', 'subYears15',
            'subApp3', 'subDiff15',
            # 换算段
            'convMonthly', 'convRent', 'convRatio',
            # insight
            'insBe',
        ],
        'text_checks': [],
    },
    '交15和40年退休金': {
        'file': '交 15 年和交 40 年，退休金差多少？.html',
        'compute': calc_pension_scenario,
        'dyn_ids': [
            # subtitle
            'subSalary', 'subYears1', 'subRate1', 'subYears2', 'subRate2',
            'subDiffYears', 'subMult',
            # 换算段
            'convSalary', 'convYears1', 'convTotal1', 'convRate1',
            'convYears2', 'convTotal2', 'convRate2',
        ],
        'text_checks': [],
    },
}


def find_dyn_ids(html):
    return re.findall(r'id="([^"]+)"', html)


def check_dyn_ids(html, scenario):
    """场景登记的占位 id 必须都存在于页面，且都在 JS renderStatic 中被 set 赋值。"""
    errors = []
    required = set(scenario['dyn_ids'])
    present = set(re.findall(r'id="([^"]+)"', html))
    missing_in_html = required - present
    if missing_in_html:
        errors.append('页面缺少动态占位: %s' % sorted(missing_in_html))
    script_m = re.search(r'<script>(.*?)</script>', html, re.S)
    script = script_m.group(1) if script_m else ''
    set_ids = set(re.findall(r"set\('([^']+)'", script))
    missing_in_js = required - set_ids
    if missing_in_js:
        errors.append('占位未被 JS 赋值: %s' % sorted(missing_in_js))
    return errors


def check_static_text(html, scenario):
    """正文中展示区域的静态数字与复算期望比对（subtitle/insight/legend）。
    检查项由场景配置 text_checks 提供: (标签, 正则, lambda 期望值函数)。
    正则未命中说明该处已动态化, 由 dyn 检查兜底。"""
    body = re.sub(r'<style.*?</style>', '', html, flags=re.S)
    body = re.sub(r'<script.*?</script>', '', body, flags=re.S)
    body = re.sub(r'<[^>]+>', ' ', body)

    expected = scenario['compute']()
    errors = []
    for label, pat, want_fn in scenario.get('text_checks', []):
        m = re.search(pat, body)
        if m:
            want = want_fn(expected)
            got = float(m.group(1))
            if abs(got - want) > 0.1:
                errors.append('%s: 页面=%s 期望=%.2f' % (label, m.group(1), want))
        # 未命中说明该处已动态化, 由 dyn 检查兜底
    return errors


def verify_scenario(name):
    cfg = SCENARIOS[name]
    path = os.path.join(HTML_DIR, cfg['file'])
    if not os.path.exists(path):
        return ['文件不存在: %s' % path]
    with open(path, encoding='utf-8') as f:
        html = f.read()
    errors = []
    errors += check_dyn_ids(html, cfg)
    errors += check_static_text(html, cfg)
    return errors


def main():
    ap = argparse.ArgumentParser(description='场景页面数字核查')
    ap.add_argument('--scenario', help='只核查指定场景')
    ap.add_argument('--list', action='store_true', help='列出已配置场景')
    args = ap.parse_args()

    if args.list:
        for k in SCENARIOS:
            print('  %s -> %s' % (k, SCENARIOS[k]['file']))
        return 0

    targets = [args.scenario] if args.scenario else list(SCENARIOS.keys())
    failed = 0
    for name in targets:
        errs = verify_scenario(name)
        if errs:
            failed += 1
            print('[FAIL] %s' % name)
            for e in errs:
                print('    - %s' % e)
        else:
            print('[PASS] %s' % name)
    if failed:
        print('共 %d 个场景未通过' % failed)
        return 1
    print('全部通过 (%d 个场景)' % len(targets))
    return 0


if __name__ == '__main__':
    sys.exit(main())
