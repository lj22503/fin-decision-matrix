"""生成决策矩阵热力图 PNG（投顾生图端原型）
用法: python scripts/render_png.py --scenario scenarios/retire_lietang.json --out output/躺平需要多少钱_决策矩阵.png
"""
import json, math, os, argparse

def sustainable_years(P, E, r):
    if E <= 0: return float('inf')
    if P <= 0: return 0.0
    if E <= P * r: return float('inf')
    return math.log(1 + r * P / E) / math.log(1 + r)

def build_matrix(cfg):
    xs, ys, r, thr = cfg['x_values'], cfg['y_values'], cfg['annual_return'], cfg['perpetual_threshold']
    data = []
    for y in ys:
        data.append([min(sustainable_years(x, y, r), thr) for x in xs])
    return data, xs, ys, r, thr

def render_png(cfg, out_path):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties

    zh = FontProperties(fname=r'C:\Windows\Fonts\msyh.ttc')
    data, xs, ys, r, thr = build_matrix(cfg)
    arr = np.array(data, dtype=float)
    arr_disp = arr.copy()
    arr_disp[arr >= thr] = thr
    norm = matplotlib.colors.Normalize(vmin=0, vmax=thr)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list('dec', ['#dc2626', '#f59e0b', '#22c55e', '#15803d'])

    fig, ax = plt.subplots(figsize=(13, 7.5))
    ax.imshow(arr_disp, cmap=cmap, norm=norm, aspect='auto')
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

    assume = cfg.get('assumption_note', '')
    ax.text(0.5, -0.14, assume + '超过 80 年视为「花不完」。测算不构成投资建议。',
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
