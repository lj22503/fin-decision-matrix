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
