# -*- coding: utf-8 -*-
"""fin-decision-matrix · HTML 渲染

输出两类可截图产物：
1. 决策矩阵图（投顾生图端）：二维热力表格，红→琥珀→绿，"花不完"高亮。
2. 结果卡（用户自选端）：单点结论，大数字 + 对比条 + 换算句 + 文案。
设计依据：陈锦初传播方法论《截图即内容》规范。
"""
from .core import ScenarioConfig, MatrixResult, build_matrix, single_result, CELL_COLORS

PAGE_CSS = """
  * { margin:0; padding:0; box-sizing:border-box; font-family:"Microsoft YaHei","PingFang SC",sans-serif; }
  body { background:#f6f7fb; padding:24px; }
  .card { background:#fff; border-radius:16px; box-shadow:0 4px 20px rgba(0,0,0,.08);
          max-width:980px; margin:0 auto; padding:28px 32px; }
  h1 { font-size:30px; color:#111827; text-align:center; }
  .subtitle { text-align:center; color:#6b7280; font-size:14px; margin:6px 0 18px; }
  .emotion { display:inline-block; background:#fef3c7; color:#b45309; font-size:11px; padding:2px 8px;
             border-radius:999px; margin-left:8px; vertical-align:middle; font-weight:700; }
  .assume { background:#f3f4f6; border-radius:10px; padding:10px 14px; font-size:13px;
            color:#374151; margin-bottom:16px; line-height:1.7; }
  table { width:100%; border-collapse:separate; border-spacing:4px; }
  th { padding:10px 8px; font-size:14px; color:#111827; background:#eef2ff; border-radius:8px; }
  th.rowhead { text-align:left; width:110px; }
  td { padding:12px 8px; text-align:center; font-size:15px; font-weight:700;
       color:#fff; border-radius:8px; min-width:64px; }
  .foot { margin-top:16px; font-size:12px; color:#9ca3af; line-height:1.6; }
  .watermark { margin-top:14px; text-align:center; font-size:12px; color:#9ca3af; letter-spacing:1px; }
  .legend { display:flex; justify-content:center; gap:18px; margin:12px 0 16px; font-size:12px; color:#374151; }
  .legend span { display:inline-flex; align-items:center; gap:6px; }
  .dot { width:14px; height:14px; border-radius:4px; display:inline-block; }
"""

RESULT_CARD_CSS = """
  * { margin:0; padding:0; box-sizing:border-box; font-family:"Microsoft YaHei","PingFang SC",sans-serif; }
  body { background:#0f172a; padding:24px; display:flex; justify-content:center; }
  .rcard { background:linear-gradient(160deg,#1e293b,#0f172a); color:#fff; border-radius:20px;
           max-width:640px; padding:32px; box-shadow:0 12px 40px rgba(0,0,0,.4); }
  .rhead { font-size:20px; font-weight:700; color:#fbbf24; line-height:1.5; }
  .rlabel { font-size:13px; color:#94a3b8; margin-top:22px; }
  .rbig { font-size:52px; font-weight:800; margin:4px 0 10px; letter-spacing:1px; }
  .rsub { font-size:14px; color:#cbd5e1; line-height:1.7; }
  .rcompare { background:#111827; border-radius:12px; padding:14px 18px; margin-top:18px; font-size:14px; line-height:2; }
  .rcmp-hi { color:#4ade80; font-weight:700; }
  .rcmp-lo { color:#f87171; font-weight:700; }
  .rquote { margin-top:16px; font-size:15px; color:#fbbf24; font-weight:700; text-align:center; }
  .rconvert { margin-top:14px; background:#052e16; border:1px solid #166534; border-radius:10px;
              padding:10px 14px; font-size:13px; color:#86efac; line-height:1.7; }
  .rconvert b { color:#4ade80; font-size:15px; }
  .rshare { margin-top:12px; background:#111827; border-left:3px solid #fbbf24; border-radius:8px;
            padding:10px 14px; font-size:13px; color:#e2e8f0; line-height:1.8; }
  .rshare .tag { display:inline-block; background:#fbbf24; color:#0f172a; font-size:11px; font-weight:700;
                 padding:1px 8px; border-radius:6px; margin-right:8px; }
  .rdisclaimer { margin-top:14px; font-size:11px; color:#64748b; line-height:1.6; }
  .rwatermark { margin-top:10px; text-align:center; font-size:11px; color:#64748b; letter-spacing:1px; }
"""


def _convert_note(cfg: ScenarioConfig) -> str:
    """陈锦初换算句：抽象大数字 → 可感知行为（如每天 X 元 / X 杯奶茶）"""
    if not cfg.convert:
        return ''
    mid = min(cfg.y_values, key=lambda v: abs(v - 10))
    daily = mid * 10000 / 365
    cups = round(daily / 20)
    extra = cfg.convert.get('extra', '').replace('{cups}', f'{cups:.0f}')
    return (f"换算：年花 {mid}{cfg.y_unit} ≈ 每天 <b>{daily:.0f} 元</b> ≈ {cups:.0f} 杯奶茶/天"
            f"——你的存款，正在替你赚回来。")


def render_matrix_html(cfg: ScenarioConfig, out_path: str) -> str:
    """生成决策矩阵图 HTML（投顾生图端）"""
    rows = build_matrix(cfg)
    head_cells = ''.join(
        f'<th>{cfg.x_values[i]}{cfg.x_unit}</th>' for i in range(len(cfg.x_values)))
    body_rows = []
    for row in rows:
        tds = ''.join(
            f'<td style="background:{cell.color}">{cell.display}</td>' for cell in row)
        body_rows.append(f'<tr><th class="rowhead">{row[0].row_label}</th>{tds}</tr>')
    legend = (
        '<div class="legend">'
        f'<span><i class="dot" style="background:{CELL_COLORS["safe"]}"></i>花不完/永续</span>'
        f'<span><i class="dot" style="background:{CELL_COLORS["ok"]}"></i>≥30年</span>'
        f'<span><i class="dot" style="background:{CELL_COLORS["warn"]}"></i>10-30年</span>'
        f'<span><i class="dot" style="background:{CELL_COLORS["danger"]}"></i>&lt;10年</span>'
        '</div>'
    )
    emotion = f'<span class="emotion">{cfg.emotion}</span>' if cfg.emotion else ''
    convert_note = _convert_note(cfg)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{cfg.title}</title>
<style>{PAGE_CSS}</style></head><body>
<div class="card">
  <h1>{cfg.hook_title or cfg.title}</h1>
  <div class="subtitle">{cfg.hook_line or cfg.subtitle}{emotion}</div>
  <div class="assume">假设：年化实际收益率 {cfg.annual_return*100:.1f}%（已扣除通胀）；年花费恒定、无大额一次性支出；
  可持续年限超过 {cfg.perpetual_threshold:.0f} 年视为「花不完」。<br>{convert_note}</div>
  {legend}
  <table>
    <tr><th class="rowhead">{cfg.y_name}</th>{head_cells}</tr>
    {''.join(body_rows)}
  </table>
  <div class="foot">{cfg.disclaimer}</div>
  <div class="watermark">{cfg.watermark}</div>
</div>
</body></html>"""
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return out_path


def render_result_card(cfg: ScenarioConfig, principal: float, spend: float,
                       compare_principal: float, out_path: str) -> str:
    """生成单点结果卡 HTML（用户自选端）"""
    r = single_result(cfg, principal, spend)
    rc = single_result(cfg, compare_principal, spend)
    big_text = r.display if r.display == '花不完' else f'{r.display}'
    daily = spend * 10000 / 365
    if r.display == '花不完':
        rsub = f'存款 {principal}{cfg.x_unit}，每年花 {spend}{cfg.y_unit}：收益已覆盖开销，财务自由线内。'
        quote = f'你的钱，会自己养自己——每天醒来，账户自动给你发 {daily:.0f} 元。'
    else:
        years_f = int(round(r.years)) if r.years >= 20 else f'{r.years:.1f}'
        gap = spend / cfg.annual_return - principal
        rsub = f'存款 {principal}{cfg.x_unit}，每年花 {spend}{cfg.y_unit}：可持续 {years_f} 年，之后归零。'
        quote = f'躺平的底气，是本金和欲望的差。还差 {gap:.0f} 万，才够躺平。'
    if principal > compare_principal:
        gap_line = (f'如果当初多存 {principal-compare_principal:.0f}{cfg.x_unit}——'
                    f'从「{rc.display}」到「{r.display}」。一字之差，人生两条线。')
    else:
        gap_line = f'本金差 {abs(principal-compare_principal):.0f}{cfg.x_unit}，可持续性差一档。'
    compare_html = (
        '<div class="rcompare">'
        f'&nbsp;&nbsp;你的方案：存款 {principal}{cfg.x_unit} / 年花 {spend}{cfg.y_unit} → <span class="rcmp-hi">{r.display}</span><br>'
        f'&nbsp;&nbsp;对比方案：存款 {compare_principal}{cfg.x_unit} / 年花 {spend}{cfg.y_unit} → <span class="rcmp-lo">{rc.display}</span><br>'
        f'&nbsp;&nbsp;{gap_line}'
        '</div>'
    )
    convert_html = ''
    if cfg.convert:
        cups = daily / 20
        convert_html = (
            '<div class="rconvert">'
            f'换算：年花 {spend}{cfg.y_unit} ≈ 每天 <b>{daily:.0f} 元</b> ≈ <b>{cups:.0f} 杯奶茶/天</b>'
            '</div>'
        )
    share_html = ''
    if cfg.share_copy:
        share_text = cfg.share_copy.format(principal=principal, spend=spend, result=r.display)
        share_html = f'<div class="rshare"><span class="tag">可晒</span>{share_text}</div>'
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{cfg.title} · 结果卡</title>
<style>{RESULT_CARD_CSS}</style></head><body>
<div class="rcard">
  <div class="rhead">{cfg.hook_title or cfg.title}</div>
  <div class="rlabel">你的答案</div>
  <div class="rbig" style="color:{r.color}">{big_text}</div>
  <div class="rsub">{rsub}</div>
  {convert_html}
  {compare_html}
  <div class="rquote">{quote}</div>
  {share_html}
  <div class="rdisclaimer">{cfg.disclaimer}</div>
  <div class="rwatermark">{cfg.watermark}</div>
</div>
</body></html>"""
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return out_path
