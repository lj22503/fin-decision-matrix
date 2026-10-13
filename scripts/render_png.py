"""生成决策矩阵热力图 PNG（投顾生图端原型）
用法: python scripts/render_png.py --scenario scenarios/retire_lietang.json --out output/躺平需要多少钱_决策矩阵.png
      python scripts/render_png.py --scenario scenarios/credit_minpay.json --out output/信用卡最低还款陷阱_决策矩阵.png
"""
import json, math, os, argparse

def sustainable_years(P, E, r):
    if E <= 0: return float('inf')
    if P <= 0: return 0.0
    if E <= P * r: return float('inf')
    return math.log(1 + r * P / E) / math.log(1 + r)

def debt_payoff_years(B0, rate_pct, min_ratio=0.02, min_floor=50.0, max_years=100.0):
    """只还最低还款：还清年限（年），never=True 表示永不还清"""
    B = B0 * 10000
    m = rate_pct / 100 / 12
    months = 0
    while B > 0.01 and months < int(max_years * 12):
        interest = B * m
        pay = max(B * min_ratio, min_floor)
        if pay <= interest:
            return float('inf'), True
        B -= (pay - interest)
        months += 1
    return months / 12, False

def savings_fv(monthly_save, years, rate=0.05):
    """每月节省 → 年化复利年金终值（万元）"""
    if monthly_save <= 0 or years <= 0:
        return 0.0
    annual = monthly_save * 12
    return annual * ((1 + rate) ** years - 1) / rate / 10000

def monthly_saved(spend, cut_ratio):
    """月消费 × 降级幅度 → 每月省（元）"""
    return spend * cut_ratio

def annuity_monthly_payment(P, rate_pct, years):
    """等额本息月供（元）"""
    if years <= 0:
        return 0.0
    r = rate_pct / 100 / 12
    n = int(round(years * 12))
    if r == 0:
        return P * 10000 / n
    return P * 10000 * r * (1 + r) ** n / ((1 + r) ** n - 1)

def prepay_sim(P, rate_pct, years, extra):
    """提前还款模拟：返回 (还清月数, 总利息万元, 月供元)"""
    bal = P * 10000
    r = rate_pct / 100 / 12
    n = int(round(years * 12))
    if bal <= 0 or n <= 0:
        return 0, 0.0, 0.0
    if r == 0:
        m = bal / n
        months = n
        while months > 1 and bal - m * months - extra * (n - months) > 0:
            months -= 1
        return months, 0.0, m
    m = annuity_monthly_payment(P, rate_pct, years)
    months = 0
    ti = 0.0
    while bal > 0.01 and months < n:
        interest = bal * r
        principal_part = m - interest
        if principal_part <= 0:
            break
        bal -= (principal_part + extra)
        ti += interest
        months += 1
        if bal < 0:
            bal = 0
    return months, ti / 10000, m

def prepay_base_interest(P, rate_pct, years):
    """不提前还款时总利息（万元）"""
    return prepay_sim(P, rate_pct, years, 0.0)[1]

def tuition_payback_months(tuition, rise):
    """学费回收期（月）= 学费(元) / 月薪涨幅(元/月)"""
    if tuition <= 0 or rise <= 0:
        return float('inf')
    return tuition * 10000 / rise

def tuition_extra_gain(tuition, rise, horizon_years=5.0):
    """回本后 horizon 年累计多赚（万元）"""
    if rise <= 0:
        return 0.0
    return rise * 12 * horizon_years / 10000

def emergency_fund_need(monthly_expense_wan, months):
    """建议应急金（万元）= 月固定支出 × 安全月数"""
    return monthly_expense_wan * months

def emergency_level(months):
    """应急金安全月数档位"""
    if months < 3: return 'bare'
    if months < 6: return 'minimal'
    if months < 9: return 'standard'
    if months <= 12: return 'solid'
    return 'plenty'

def dca_fv(monthly, start_age, target_age=60.0, annual_rate=0.08):
    """月度定投年金终值（万元）"""
    if monthly <= 0 or target_age <= start_age:
        return 0.0
    r = annual_rate / 12
    n = (target_age - start_age) * 12
    return monthly * (((1 + r) ** n - 1) / r) / 10000

def dca_level(asset_wan):
    """定投 60 岁资产档位"""
    if asset_wan < 50: return 'small'
    if asset_wan < 150: return 'mid'
    if asset_wan < 300: return 'good'
    if asset_wan < 600: return 'big'
    return 'huge'

# ---------- 场景 4.1：租房 vs 买房 ----------
HOUSE_PRICE = 300.0
DOWN_RATIO = 0.30
MORTGAGE_RATE = 0.035
LOAN_YEARS = 30
RENT_MONTH = 4000.0
RENT_GROWTH = 0.02
BUY_FEE_RATIO = 0.03

def mortgage_monthly(price=HOUSE_PRICE, down_ratio=DOWN_RATIO, rate=MORTGAGE_RATE, years=LOAN_YEARS):
    """等额本息月供（元）"""
    loan = price * (1 - down_ratio) * 10000
    if loan <= 0: return 0.0
    r = rate / 12
    n = years * 12
    return loan * r * (1 + r) ** n / ((1 + r) ** n - 1)

def rent_total_cost(years):
    """租房 N 年总支出（万元），租金年涨 2%"""
    if years <= 0: return 0.0
    total = 0.0
    rent = RENT_MONTH
    for _ in range(int(years)):
        total += rent * 12
        rent *= (1 + RENT_GROWTH)
    return total / 10000

def buy_total_cost(years, growth):
    """买房 N 年净支出（万元）：首付+税费+月供×N - 卖房净回收"""
    if years <= 0: return 0.0
    price = HOUSE_PRICE
    down = price * DOWN_RATIO
    fee = price * BUY_FEE_RATIO
    monthly = mortgage_monthly()
    paid = monthly * 12 * years / 10000
    loan = price * (1 - DOWN_RATIO)
    r = MORTGAGE_RATE / 12
    n = LOAN_YEARS * 12
    paid_months = min(int(years * 12), n)
    if n > 0:
        remain = loan * ((1 + r) ** n - (1 + r) ** paid_months) / ((1 + r) ** n - 1)
    else:
        remain = loan
    sell = price * (1 + growth) ** years - remain
    return down + fee + paid - sell

def house_decision(years, growth):
    """返回 diff（万元）：买房净支出 - 租房净支出，负=买房划算"""
    return buy_total_cost(years, growth) - rent_total_cost(years)

def house_breakeven(growth, max_years=30):
    """盈亏平衡年限：第几年买房开始划算"""
    for y in range(1, max_years + 1):
        if house_decision(y, growth) < -3:
            return y
    return max_years + 1

def build_matrix(cfg):
    xs, ys = cfg['x_values'], cfg['y_values']
    stype = cfg.get('scenario_type', 'retire')
    if stype == 'debt':
        ratio = cfg.get('min_payment_ratio', 0.02)
        floor = cfg.get('min_payment_floor', 50.0)
        data = []
        for y in ys:
            row = []
            for x in xs:
                years, never = debt_payoff_years(y, x, ratio, floor)
                row.append(years if not never else float('inf'))
            data.append(row)
        return data, xs, ys, stype, 30.0
    if stype == 'savings':
        rate = cfg.get('annual_return', 0.05)
        data = []
        for y in ys:
            row = [savings_fv(y, x, rate) for x in xs]
            data.append(row)
        vmax = max(max(row) for row in data)
        return data, xs, ys, stype, vmax
    if stype == 'savings_cut':
        rate = cfg.get('annual_return', 0.05)
        years = cfg.get('savings_years', 20.0)
        data = []
        for y in ys:
            row = [savings_fv(monthly_saved(y, x), years, rate) for x in xs]
            data.append(row)
        vmax = max(max(row) for row in data)
        return data, xs, ys, stype, vmax
    if stype == 'prepay':
        rate = cfg.get('loan_rate_pct', 3.9)
        years = cfg.get('loan_years', 30.0)
        data = []
        for y in ys:
            row = []
            for x in xs:
                months, interest, _ = prepay_sim(y, rate, years, x)
                base = prepay_base_interest(y, rate, years)
                saved = max(0.0, base - interest)
                row.append(saved)
            data.append(row)
        vmax = max(max(row) for row in data)
        return data, xs, ys, stype, vmax
    if stype == 'tuition':
        data = []
        for y in ys:
            row = []
            for x in xs:
                gain = tuition_extra_gain(y, x)
                row.append(gain)
            data.append(row)
        vmax = max(max(row) for row in data)
        return data, xs, ys, stype, vmax
    if stype == 'emergency':
        data = []
        for y in ys:
            row = []
            for x in xs:
                row.append(emergency_fund_need(y, x))
            data.append(row)
        vmax = max(max(row) for row in data)
        return data, xs, ys, stype, vmax
    if stype == 'dca':
        data = []
        for y in ys:
            row = []
            for x in xs:
                row.append(dca_fv(y, x))
            data.append(row)
        vmax = max(max(row) for row in data)
        return data, xs, ys, stype, vmax
    if stype == 'house':
        data = []
        for y in ys:
            row = []
            for x in xs:
                row.append(house_decision(y, x))
            data.append(row)
        vmax = max(abs(v) for row in data for v in row)
        return data, xs, ys, stype, vmax
    r, thr = cfg['annual_return'], cfg['perpetual_threshold']
    data = []
    for y in ys:
        data.append([min(sustainable_years(x, y, r), thr) for x in xs])
    return data, xs, ys, stype, thr

def render_png(cfg, out_path):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties

    zh = FontProperties(fname=r'C:\Windows\Fonts\msyh.ttc')
    data, xs, ys, stype, thr = build_matrix(cfg)
    arr = np.array([[float('inf') if math.isinf(v) else v for v in row] for row in data], dtype=float)
    arr_disp = arr.copy()
    arr_disp[arr >= thr] = thr
    if stype == 'house':
        norm = matplotlib.colors.Normalize(vmin=-thr, vmax=thr)
    else:
        norm = matplotlib.colors.Normalize(vmin=0, vmax=thr)
    if stype == 'debt':
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list('dec', ['#15803d', '#f59e0b', '#dc2626', '#7f1d1d'])
    elif stype == 'house':
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list('dec', ['#065f46', '#22c55e', '#fef08a', '#f59e0b', '#dc2626', '#7f1d1d'])
    elif stype in ('savings', 'savings_cut', 'prepay', 'tuition', 'emergency', 'dca'):
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list('dec', ['#f59e0b', '#22c55e', '#15803d', '#065f46'])
    else:
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list('dec', ['#dc2626', '#f59e0b', '#22c55e', '#15803d'])

    fig, ax = plt.subplots(figsize=(13, 7.5))
    ax.imshow(arr_disp, cmap=cmap, norm=norm, aspect='auto')
    if stype == 'debt':
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels([f'{x}%' for x in xs], fontproperties=zh, fontsize=11)
        ax.set_yticks(range(len(ys)))
        ax.set_yticklabels([f'{y}万' for y in ys], fontproperties=zh, fontsize=11)
        ax.set_xlabel('年利率', fontproperties=zh, fontsize=13)
        ax.set_ylabel('债务余额（万元）', fontproperties=zh, fontsize=13)
        ax.set_title(cfg['title'] + '：债务余额 × 年利率 → 只还最低多久还清', fontproperties=zh, fontsize=18, pad=14)
        for i in range(len(ys)):
            for j in range(len(xs)):
                n = data[i][j]
                txt = '永不还清' if math.isinf(n) else (f'{n:.0f}年' if n >= 20 else f'{n:.1f}年')
                ax.text(j, i, txt, ha='center', va='center', fontsize=12, fontweight='bold', color='#ffffff', fontproperties=zh)
    elif stype == 'savings':
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels([f'{x}年' for x in xs], fontproperties=zh, fontsize=11)
        ax.set_yticks(range(len(ys)))
        ax.set_yticklabels([f'{y}元/月' for y in ys], fontproperties=zh, fontsize=11)
        ax.set_xlabel('坚持年限', fontproperties=zh, fontsize=13)
        ax.set_ylabel('每月节省（元）', fontproperties=zh, fontsize=13)
        ax.set_title(cfg['title'] + '：每月节省 × 坚持年限 → 隐形存款（5% 复利）', fontproperties=zh, fontsize=18, pad=14)
        for i in range(len(ys)):
            for j in range(len(xs)):
                n = data[i][j]
                txt = (f'{n:.0f}万' if n >= 10 else (f'{n:.1f}万' if n >= 1 else f'{int(round(n*10000/100))*100}元'))
                ax.text(j, i, txt, ha='center', va='center', fontsize=12, fontweight='bold', color='#ffffff', fontproperties=zh)
    elif stype == 'savings_cut':
        years = cfg.get('savings_years', 20.0)
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels([f'降{int(x*100)}%' for x in xs], fontproperties=zh, fontsize=11)
        ax.set_yticks(range(len(ys)))
        ax.set_yticklabels([f'{y:.0f}元/月' for y in ys], fontproperties=zh, fontsize=11)
        ax.set_xlabel('降级幅度', fontproperties=zh, fontsize=13)
        ax.set_ylabel('当前月消费（元）', fontproperties=zh, fontsize=13)
        ax.set_title(cfg['title'] + f'：月消费 × 降级幅度 → {int(years)}年隐形存款（{cfg.get("annual_return",0.05)*100:.0f}% 复利）', fontproperties=zh, fontsize=18, pad=14)
        for i in range(len(ys)):
            for j in range(len(xs)):
                n = data[i][j]
                txt = (f'{n:.0f}万' if n >= 10 else (f'{n:.1f}万' if n >= 1 else f'{int(round(n*10000/100))*100}元'))
                ax.text(j, i, txt, ha='center', va='center', fontsize=12, fontweight='bold', color='#ffffff', fontproperties=zh)
    elif stype == 'prepay':
        rate = cfg.get('loan_rate_pct', 3.9)
        years = cfg.get('loan_years', 30.0)
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels([f'{x:.0f}元/月' for x in xs], fontproperties=zh, fontsize=11)
        ax.set_yticks(range(len(ys)))
        ax.set_yticklabels([f'{y:.0f}万' for y in ys], fontproperties=zh, fontsize=11)
        ax.set_xlabel('每月额外还款（元）', fontproperties=zh, fontsize=13)
        ax.set_ylabel('贷款余额（万元）', fontproperties=zh, fontsize=13)
        ax.set_title(cfg['title'] + f'：贷款余额 × 每月额外还款 → 省下利息（{rate:.1f}% 等额本息 {years:.0f}年）', fontproperties=zh, fontsize=18, pad=14)
        for i in range(len(ys)):
            for j in range(len(xs)):
                months, interest, _ = prepay_sim(ys[i], rate, years, xs[j])
                base = prepay_base_interest(ys[i], rate, years)
                saved = max(0.0, base - interest)
                if xs[j] == 0:
                    txt = f'{months/12:.0f}年'
                else:
                    txt = f'省{saved:.0f}万'
                ax.text(j, i, txt, ha='center', va='center', fontsize=12, fontweight='bold', color='#ffffff', fontproperties=zh)
    elif stype == 'tuition':
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels([f'+{x:.0f}元/月' for x in xs], fontproperties=zh, fontsize=11)
        ax.set_yticks(range(len(ys)))
        ax.set_yticklabels([f'{y:.0f}万' for y in ys], fontproperties=zh, fontsize=11)
        ax.set_xlabel('预期月薪涨幅（元/月）', fontproperties=zh, fontsize=13)
        ax.set_ylabel('学费/投入（万元）', fontproperties=zh, fontsize=13)
        ax.set_title(cfg['title'] + '：学费 × 月薪涨幅 → 回本周期 + 后5年多赚', fontproperties=zh, fontsize=18, pad=14)
        for i in range(len(ys)):
            for j in range(len(xs)):
                months = tuition_payback_months(ys[i], xs[j])
                if math.isinf(months):
                    txt = '回不了本'
                elif months < 24:
                    txt = f'{int(round(months))}个月'
                else:
                    txt = f'{months/12:.1f}年'
                ax.text(j, i, txt, ha='center', va='center', fontsize=12, fontweight='bold', color='#ffffff', fontproperties=zh)
    elif stype == 'emergency':
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels([f'{x:.0f}个月' for x in xs], fontproperties=zh, fontsize=11)
        ax.set_yticks(range(len(ys)))
        ax.set_yticklabels([f'{y:.1f}万/月' for y in ys], fontproperties=zh, fontsize=11)
        ax.set_xlabel('目标安全月数', fontproperties=zh, fontsize=13)
        ax.set_ylabel('月固定支出（万元）', fontproperties=zh, fontsize=13)
        ax.set_title(cfg['title'] + '：月支出 × 安全月数 → 建议应急金', fontproperties=zh, fontsize=18, pad=14)
        for i in range(len(ys)):
            for j in range(len(xs)):
                need = emergency_fund_need(ys[i], xs[j])
                txt = f'{need:.1f}万'
                ax.text(j, i, txt, ha='center', va='center', fontsize=12, fontweight='bold', color='#ffffff', fontproperties=zh)
    elif stype == 'dca':
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels([f'{x:.0f}岁' for x in xs], fontproperties=zh, fontsize=11)
        ax.set_yticks(range(len(ys)))
        ax.set_yticklabels([f'{y:.0f}元/月' for y in ys], fontproperties=zh, fontsize=11)
        ax.set_xlabel('开始定投年龄', fontproperties=zh, fontsize=13)
        ax.set_ylabel('每月定投金额（元）', fontproperties=zh, fontsize=13)
        ax.set_title(cfg['title'] + '：月定投 × 开始年龄 → 60 岁总资产', fontproperties=zh, fontsize=18, pad=14)
        for i in range(len(ys)):
            for j in range(len(xs)):
                asset = dca_fv(ys[i], xs[j])
                txt = f'{asset:.0f}万'
                ax.text(j, i, txt, ha='center', va='center', fontsize=12, fontweight='bold', color='#ffffff', fontproperties=zh)
    elif stype == 'house':
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels([f'{x*100:.0f}%' for x in xs], fontproperties=zh, fontsize=11)
        ax.set_yticks(range(len(ys)))
        ax.set_yticklabels([f'住{y:.0f}年' for y in ys], fontproperties=zh, fontsize=11)
        ax.set_xlabel('房价年涨幅', fontproperties=zh, fontsize=13)
        ax.set_ylabel('居住年限', fontproperties=zh, fontsize=13)
        ax.set_title(cfg['title'] + '：居住年限 × 房价年涨幅 → 买房还是租房划算', fontproperties=zh, fontsize=18, pad=14)
        for i in range(len(ys)):
            for j in range(len(xs)):
                diff = data[i][j]
                if diff < -3:
                    txt = f'买省{diff*-1:.0f}万'
                    color = '#ffffff'
                elif diff > 3:
                    txt = f'租省{diff:.0f}万'
                    color = '#ffffff'
                else:
                    txt = '持平'
                    color = '#1e293b'
                ax.text(j, i, txt, ha='center', va='center', fontsize=12, fontweight='bold', color=color, fontproperties=zh)
    else:
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels([f'{x}万' for x in xs], fontproperties=zh, fontsize=11)
        ax.set_yticks(range(len(ys)))
        ax.set_yticklabels([f'{y}万/年' for y in ys], fontproperties=zh, fontsize=11)
        ax.set_xlabel('存款（万元）', fontproperties=zh, fontsize=13)
        ax.set_ylabel('年度花费（万元/年）', fontproperties=zh, fontsize=13)
        ax.set_title(cfg['title'] + '：存款 × 年花费 → 能躺平多久', fontproperties=zh, fontsize=18, pad=14)
        for i in range(len(ys)):
            for j in range(len(xs)):
                n = data[i][j]
                txt = '花不完' if (math.isinf(n) or n >= thr) else (f'{n:.0f}年' if n >= 20 else f'{n:.1f}年')
                ax.text(j, i, txt, ha='center', va='center', fontsize=12, fontweight='bold', color='#ffffff', fontproperties=zh)

    hook = cfg.get('hook_line', '')
    if stype == 'debt':
        mid_rate = xs[len(xs) // 2]
        mid_balance = ys[-1]
        monthly = round(mid_balance * 10000 * (mid_rate / 100 / 12))
        cups = round(monthly / 20)
        note = (f'{hook} 换算：{mid_balance}万债务、{mid_rate}%利率每月光利息{monthly}元≈{cups}杯奶茶/月。'
                f'最低还款=余额×2%，还款≤利息即永不还清。测算不构成还款建议。')
    elif stype == 'savings':
        mid_save = min(cfg['y_values'], key=lambda v: abs(v - 500))
        daily = round(mid_save / 30)
        cups = round(daily / 20)
        fv20 = savings_fv(mid_save, 20, cfg.get('annual_return', 0.05))
        note = (f'{hook} 换算：每月省{mid_save}元≈每天{daily}元≈{cups}杯奶茶/天；'
                f'5%复利20年后是{fv20:.1f}万。省下的每一块钱，都是你的隐形存款。测算不构成投资建议。')
    elif stype == 'savings_cut':
        years = cfg.get('savings_years', 20.0)
        spend = min(cfg['y_values'], key=lambda v: abs(v - 5000))
        cut = min(cfg['x_values'], key=lambda c: abs(c - 0.10))
        save = monthly_saved(spend, cut)
        daily = round(save / 30)
        cups = round(daily / 20)
        fv = savings_fv(save, years, cfg.get('annual_return', 0.05))
        note = (f'{hook} 换算：月消费{spend:.0f}元、降{int(cut*100)}%→每月省{save:.0f}元≈每天{daily}元≈{cups}杯奶茶/天；'
                f'{years:.0f}年后是{fv:.1f}万。降幅≤10%无痛、≤20%轻松、≤30%伤生活、>30%极限省。测算不构成投资建议。')
    elif stype == 'prepay':
        rate = cfg.get('loan_rate_pct', 3.9)
        years = cfg.get('loan_years', 30.0)
        principal = min(cfg['y_values'], key=lambda v: abs(v - 100))
        extra = min(cfg['x_values'], key=lambda e: abs(e - 1000))
        months, interest, monthly = prepay_sim(principal, rate, years, extra)
        base = prepay_base_interest(principal, rate, years)
        saved = max(0.0, base - interest)
        note = (f'{hook} 换算：{principal:.0f}万房贷、{rate:.1f}%利率，月供{monthly:.0f}元；'
                f'每月多还{extra:.0f}元→还清缩到{months/12:.0f}年，省利息{saved:.1f}万。'
                f'节省≥50%强烈建议、30-50%划算、10-30%一般、<10%不值得。测算不构成还款建议。')
    elif stype == 'tuition':
        tuition = min(cfg['y_values'], key=lambda v: abs(v - 3))
        rise = min(cfg['x_values'], key=lambda r: abs(r - 5000))
        months = tuition_payback_months(tuition, rise)
        gain = tuition_extra_gain(tuition, rise)
        note = (f'{hook} 换算：{tuition:.0f}万学费、月薪涨{rise:.0f}元→{int(round(months))}个月回本，'
                f'回本后5年累计多赚{gain:.0f}万。'
                f'回本≤12个月闭眼投、12-24个月划算、24-36个月一般、>36个月不值得。测算不构成教育投资建议。')
    elif stype == 'emergency':
        expense = min(cfg['y_values'], key=lambda v: abs(v - 1))
        months = min(cfg['x_values'], key=lambda m: abs(m - 6))
        need = emergency_fund_need(expense, months)
        note = (f'{hook} 换算：月固定支出{expense:.1f}万、留{months:.0f}个月→应急金{need:.1f}万。'
                f'档位：不足3个月赤贫级、3-6个月底线、6-9个月标准、9-12个月稳健、12个月以上充裕（可转低波理财）。'
                f'测算不构成投资建议。')
    elif stype == 'dca':
        monthly = min(cfg['y_values'], key=lambda v: abs(v - 1000))
        age = min(cfg['x_values'], key=lambda a: abs(a - 25))
        asset = dca_fv(monthly, age)
        note = (f'{hook} 换算：每月定投{monthly:.0f}元≈每天{monthly/30:.0f}元≈{monthly/20:.0f}杯奶茶/月，'
                f'从{age:.0f}岁开始60岁约{asset:.0f}万。'
                f'档位：<50万储蓄率不足、50-150万有积累、150-300万复利发力、300-600万时间玫瑰、600万以上复利放大器。'
                f'测算不构成投资建议。')
    elif stype == 'house':
        years = min(cfg['y_values'], key=lambda v: abs(v - 5))
        growth = min(cfg['x_values'], key=lambda g: abs(g - 0.05))
        diff = house_decision(years, growth)
        be = house_breakeven(growth)
        verdict = '买省' if diff < 0 else ('基本持平' if abs(diff) <= 3 else '租省')
        note = (f'{hook} 换算：月租4000元≈每年4.8万；住{years:.0f}年、房价年涨{growth*100:.0f}%时，'
                f'买房vs租房{verdict}{abs(diff):.0f}万；盈亏平衡点在第{be:.0f}年。'
                f'判断：住3年就换买房必亏，住10年以上涨幅越高买房越值。测算不构成购房建议。')
    else:
        mid = cfg['y_values'][len(cfg['y_values']) // 2]
        daily = round(mid * 10000 / 365)
        cups = round(daily / 20)
        note = (f'{hook} 换算：年花{mid}万≈每天{daily}元≈{cups}杯奶茶/天。'
                f'超过 80 年视为「花不完」。测算不构成投资建议。')
    ax.text(0.5, -0.14, note,
            transform=ax.transAxes, ha='center', fontsize=10, color='#555555', fontproperties=zh)
    ax.text(0.5, -0.21, '投资平权 · fin-decision-matrix',
            transform=ax.transAxes, ha='center', fontsize=10, color='#888888', fontproperties=zh)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    print('PNG_OK:', out_path)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenario', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    with open(args.scenario, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    render_png(cfg, args.out)
