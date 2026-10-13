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
    norm = matplotlib.colors.Normalize(vmin=0, vmax=thr)
    if stype == 'debt':
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list('dec', ['#15803d', '#f59e0b', '#dc2626', '#7f1d1d'])
    elif stype in ('savings', 'savings_cut', 'prepay'):
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
