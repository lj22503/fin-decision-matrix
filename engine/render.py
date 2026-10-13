# -*- coding: utf-8 -*-
"""fin-decision-matrix · HTML 渲染

输出两类可截图产物：
1. 决策矩阵图（投顾生图端）：二维热力表格，红→琥珀→绿，"花不完"高亮。
2. 结果卡（用户自选端）：单点结论，大数字 + 对比条 + 换算句 + 文案。
设计依据：陈锦初传播方法论《截图即内容》规范。
"""
from .core import (ScenarioConfig, MatrixResult, build_matrix, single_result,
                   CELL_COLORS, build_debt_matrix, single_debt_result,
                   debt_payoff_years, DEBT_COLORS,
                   build_cut_matrix, single_cut_result, monthly_saved,
                   savings_fv, cut_judgment, SAV_CUT_COLORS,
                   build_prepay_matrix, single_prepay_result,
                   prepay_sim, prepay_base_interest, prepay_save_ratio,
                   prepay_judgment, PREPAY_COLORS, annuity_monthly_payment)

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


# ==================== 场景 2.1：信用卡最低还款陷阱 ====================

DEBT_PAGE_CSS = """
  * { margin:0; padding:0; box-sizing:border-box; font-family:"Microsoft YaHei","PingFang SC",sans-serif; }
  body { background:#1a1a1a; padding:24px; }
  .card { background:#fff; border-radius:16px; box-shadow:0 4px 20px rgba(0,0,0,.08);
          max-width:980px; margin:0 auto; padding:28px 32px; }
  h1 { font-size:30px; color:#111827; text-align:center; }
  .subtitle { text-align:center; color:#6b7280; font-size:14px; margin:6px 0 18px; }
  .emotion { display:inline-block; background:#fee2e2; color:#991b1b; font-size:11px; padding:2px 8px;
             border-radius:999px; margin-left:8px; vertical-align:middle; font-weight:700; }
  .assume { background:#f3f4f6; border-radius:10px; padding:10px 14px; font-size:13px;
            color:#374151; margin-bottom:16px; line-height:1.7; }
  .assume b { color:#991b1b; }
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

DEBT_CARD_CSS = """
  * { margin:0; padding:0; box-sizing:border-box; font-family:"Microsoft YaHei","PingFang SC",sans-serif; }
  body { background:#0f172a; padding:24px; display:flex; justify-content:center; }
  .rcard { background:linear-gradient(160deg,#1e293b,#0f172a); color:#fff; border-radius:20px;
           max-width:640px; padding:32px; box-shadow:0 12px 40px rgba(0,0,0,.4); }
  .rhead { font-size:20px; font-weight:700; color:#f87171; line-height:1.5; }
  .rlabel { font-size:13px; color:#94a3b8; margin-top:22px; }
  .rbig { font-size:52px; font-weight:800; margin:4px 0 10px; letter-spacing:1px; }
  .rsub { font-size:14px; color:#cbd5e1; line-height:1.7; }
  .rcompare { background:#111827; border-radius:12px; padding:14px 18px; margin-top:18px; font-size:14px; line-height:2; }
  .rcmp-hi { color:#f87171; font-weight:700; }
  .rcmp-lo { color:#4ade80; font-weight:700; }
  .rquote { margin-top:16px; font-size:15px; color:#f87171; font-weight:700; text-align:center; }
  .rconvert { margin-top:14px; background:#450a0a; border:1px solid #991b1b; border-radius:10px;
              padding:10px 14px; font-size:13px; color:#fecaca; line-height:1.7; }
  .rconvert b { color:#f87171; font-size:15px; }
  .rshare { margin-top:12px; background:#111827; border-left:3px solid #f87171; border-radius:8px;
            padding:10px 14px; font-size:13px; color:#e2e8f0; line-height:1.8; }
  .rshare .tag { display:inline-block; background:#f87171; color:#0f172a; font-size:11px; font-weight:700;
                 padding:1px 8px; border-radius:6px; margin-right:8px; }
  .rdisclaimer { margin-top:14px; font-size:11px; color:#64748b; line-height:1.6; }
  .rwatermark { margin-top:10px; text-align:center; font-size:11px; color:#64748b; letter-spacing:1px; }
"""


def _debt_convert_note(cfg: ScenarioConfig) -> str:
    """债务换算句：每月光利息 X 元 ≈ Y 杯奶茶/月"""
    mid_rate = cfg.x_values[len(cfg.x_values) // 2]
    mid_balance = cfg.y_values[-1]
    monthly = mid_balance * 10000 * (mid_rate / 100 / 12)
    cups = round(monthly / 20)
    return (f"换算：{mid_balance} 万债务、{mid_rate}% 利率——每月光利息 <b>{monthly:.0f} 元</b>"
            f"≈ {cups} 杯奶茶/月，一年 <b>{monthly*12/10000:.1f} 万</b>。你的钱，正在替银行打工。")


def _payoff_with_extra(balance_wan: float, rate_pct: float,
                       min_ratio: float, min_floor: float, extra: float):
    """每月多还 extra 元后的还清年数与累计利息"""
    B = balance_wan * 10000
    m = rate_pct / 100 / 12
    months = 0
    total_interest = 0.0
    while B > 0.01 and months < 60 * 12:
        interest = B * m
        pay = max(B * min_ratio, min_floor) + extra
        if pay <= interest:
            return float('inf'), float('inf'), True
        B -= (pay - interest)
        total_interest += interest
        months += 1
    return months / 12, total_interest / 10000, False


def render_debt_matrix_html(cfg: ScenarioConfig, out_path: str) -> str:
    """生成信用卡最低还款决策矩阵 HTML"""
    rows = build_debt_matrix(cfg)
    head_cells = ''.join(
        f'<th>{cfg.x_values[i]}{cfg.x_unit}</th>' for i in range(len(cfg.x_values)))
    body_rows = []
    for row in rows:
        tds = ''.join(
            f'<td style="background:{cell.color}">{cell.display}</td>' for cell in row)
        body_rows.append(f'<tr><th class="rowhead">{row[0].row_label}</th>{tds}</tr>')
    legend = (
        '<div class="legend">'
        f'<span><i class="dot" style="background:{DEBT_COLORS["never"]}"></i>永不还清</span>'
        f'<span><i class="dot" style="background:{DEBT_COLORS["danger"]}"></i>≥30年</span>'
        f'<span><i class="dot" style="background:{DEBT_COLORS["warn"]}"></i>10-30年</span>'
        f'<span><i class="dot" style="background:{DEBT_COLORS["ok"]}"></i>&lt;10年</span>'
        '</div>'
    )
    emotion = f'<span class="emotion">{cfg.emotion}</span>' if cfg.emotion else ''
    convert_note = _debt_convert_note(cfg)
    ratio_pct = cfg.min_payment_ratio * 100
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{cfg.title}</title>
<style>{DEBT_PAGE_CSS}</style></head><body>
<div class="card">
  <h1>{cfg.hook_title or cfg.title}</h1>
  <div class="subtitle">{cfg.hook_line or cfg.subtitle}{emotion}</div>
  <div class="assume">假设：每月最低还款 = 余额×<b>{ratio_pct:.0f}%</b>（不足 {cfg.min_payment_floor:.0f} 元按 {cfg.min_payment_floor:.0f} 元）；
  月利息 = 余额 × 月利率（年利率/12）；未计违约金、复利罚息。<br>{convert_note}</div>
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


def render_debt_result_card(cfg: ScenarioConfig, balance: float, rate: float,
                            extra_pay: float, out_path: str) -> str:
    """生成信用卡最低还款单点结果卡 HTML

    balance: 债务余额（万元）
    rate: 年利率（%）
    extra_pay: 对比方案：每月多还金额（元）
    """
    r = single_debt_result(cfg, balance, rate)
    e_years, e_interest, e_never = _payoff_with_extra(
        balance, rate, cfg.min_payment_ratio, cfg.min_payment_floor, extra_pay)
    m_only_years, m_only_interest, m_only_never = debt_payoff_years(
        balance, rate, cfg.min_payment_ratio, cfg.min_payment_floor)
    ratio_pct = cfg.min_payment_ratio * 100
    m = rate / 100 / 12
    monthly_min = max(balance * 10000 * ratio_pct / 100, cfg.min_payment_floor)
    monthly_int = balance * 10000 * m
    if r.display == '永不还清':
        big_text = '永不还清'
        rsub = (f'债务 {balance}{cfg.y_unit}，年利率 {rate:.0f}%：每月最低还款 {monthly_min:.0f} 元，'
                f'光利息就要 {monthly_int:.0f} 元——利息 ≥ 还款，本金永远还不完。')
        quote = '很多人以为在还钱，其实在给银行打工。'
    else:
        years_f = int(round(r.years)) if r.years >= 20 else f'{r.years:.1f}'
        big_text = f'{years_f}年'
        rsub = (f'债务 {balance}{cfg.y_unit}，年利率 {rate:.0f}%：每月最低还款 {monthly_min:.0f} 元，'
                f'还清要 {years_f} 年，累计利息约 {m_only_interest:.1f} 万。')
        quote = '你以为在还本金，其实先还的几乎全是利息。'
    if e_never:
        gap_line = f'即使每月多还 {extra_pay:.0f} 元，依然还不清——别只还最低了。'
        e_disp = '还不清'
        saved_interest = None
    else:
        saved_interest = max(0.0, m_only_interest - e_interest)
        gap_line = (f'如果每月多还 {extra_pay:.0f} 元——还清缩短到 {int(round(e_years))} 年，'
                    f'省下约 {saved_interest:.1f} 万利息。')
        e_disp = f'{int(round(e_years))}年'
    compare_html = (
        '<div class="rcompare">'
        f'&nbsp;&nbsp;只还最低：{balance}{cfg.y_unit} / {rate:.0f}% → <span class="rcmp-hi">{r.display}</span><br>'
        f'&nbsp;&nbsp;每月多还 {extra_pay:.0f} 元：→ <span class="rcmp-lo">{e_disp}</span><br>'
        f'&nbsp;&nbsp;{gap_line}'
        '</div>'
    )
    monthly_cups = monthly_int / 20
    convert_html = (
        '<div class="rconvert">'
        f'换算：每月光利息 <b>{monthly_int:.0f} 元</b> ≈ <b>{monthly_cups:.0f} 杯奶茶/月</b>'
        '——这笔钱如果用来定投，20 年后可能是另一笔资产。'
        '</div>'
    )
    share_html = ''
    if cfg.share_copy:
        share_text = cfg.share_copy.format(
            balance=balance, rate=rate, result=r.display,
            interest=f'{e_interest:.1f}' if not e_never else '∞')
        share_html = f'<div class="rshare"><span class="tag">可晒</span>{share_text}</div>'
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{cfg.title} · 结果卡</title>
<style>{DEBT_CARD_CSS}</style></head><body>
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


# ==================== 场景 7.1：消费降级（降多少才划算） ====================

SAV_PAGE_CSS = """
  * { margin:0; padding:0; box-sizing:border-box; font-family:"Microsoft YaHei","PingFang SC",sans-serif; }
  body { background:#f6f7fb; padding:24px; }
  .card { background:#fff; border-radius:16px; box-shadow:0 4px 20px rgba(0,0,0,.08);
          max-width:980px; margin:0 auto; padding:28px 32px; }
  h1 { font-size:30px; color:#111827; text-align:center; }
  .subtitle { text-align:center; color:#6b7280; font-size:14px; margin:6px 0 18px; }
  .emotion { display:inline-block; background:#dcfce7; color:#166534; font-size:11px; padding:2px 8px;
             border-radius:999px; margin-left:8px; vertical-align:middle; font-weight:700; }
  .assume { background:#f3f4f6; border-radius:10px; padding:10px 14px; font-size:13px;
            color:#374151; margin-bottom:16px; line-height:1.7; }
  .assume b { color:#166534; }
  table { width:100%; border-collapse:separate; border-spacing:4px; }
  th { padding:10px 8px; font-size:14px; color:#111827; background:#eef2ff; border-radius:8px; }
  th.rowhead { text-align:left; width:110px; }
  td { padding:10px 6px; text-align:center; font-size:14px; font-weight:700;
       color:#fff; border-radius:8px; min-width:84px; line-height:1.5; }
  td small { display:block; font-size:11px; font-weight:400; opacity:.9; }
  .foot { margin-top:16px; font-size:12px; color:#9ca3af; line-height:1.6; }
  .watermark { margin-top:14px; text-align:center; font-size:12px; color:#9ca3af; letter-spacing:1px; }
  .legend { display:flex; justify-content:center; gap:16px; margin:12px 0 16px; font-size:12px; color:#374151; }
  .legend span { display:inline-flex; align-items:center; gap:6px; }
  .dot { width:14px; height:14px; border-radius:4px; display:inline-block; }
"""

SAV_CARD_CSS = """
  * { margin:0; padding:0; box-sizing:border-box; font-family:"Microsoft YaHei","PingFang SC",sans-serif; }
  body { background:#0f172a; padding:24px; display:flex; justify-content:center; }
  .rcard { background:linear-gradient(160deg,#1e293b,#0f172a); color:#fff; border-radius:20px;
           max-width:640px; padding:32px; box-shadow:0 12px 40px rgba(0,0,0,.4); }
  .rhead { font-size:20px; font-weight:700; color:#4ade80; line-height:1.5; }
  .rlabel { font-size:13px; color:#94a3b8; margin-top:22px; }
  .rbig { font-size:46px; font-weight:800; margin:4px 0 10px; letter-spacing:1px; line-height:1.25; }
  .rsub { font-size:14px; color:#cbd5e1; line-height:1.7; }
  .rverdict { margin-top:16px; background:#111827; border-left:4px solid #4ade80; border-radius:10px;
              padding:12px 16px; font-size:14px; line-height:1.8; }
  .rverdict b { color:#4ade80; }
  .rcompare { background:#111827; border-radius:12px; padding:14px 18px; margin-top:14px; font-size:14px; line-height:2; }
  .rcmp-hi { color:#4ade80; font-weight:700; }
  .rcmp-lo { color:#94a3b8; font-weight:700; }
  .rquote { margin-top:14px; font-size:15px; color:#4ade80; font-weight:700; text-align:center; }
  .rconvert { margin-top:14px; background:#052e16; border:1px solid #166534; border-radius:10px;
              padding:10px 14px; font-size:13px; color:#86efac; line-height:1.7; }
  .rconvert b { color:#4ade80; font-size:15px; }
  .rshare { margin-top:12px; background:#111827; border-left:3px solid #4ade80; border-radius:8px;
            padding:10px 14px; font-size:13px; color:#e2e8f0; line-height:1.8; }
  .rshare .tag { display:inline-block; background:#4ade80; color:#0f172a; font-size:11px; font-weight:700;
                 padding:1px 8px; border-radius:6px; margin-right:8px; }
  .rdisclaimer { margin-top:14px; font-size:11px; color:#64748b; line-height:1.6; }
  .rwatermark { margin-top:10px; text-align:center; font-size:11px; color:#64748b; letter-spacing:1px; }
"""


def _cut_convert_note(cfg: ScenarioConfig) -> str:
    """消费降级换算句：锚点 = 月消费 5000 × 降 10%（每月省 500）"""
    spend = min(cfg.y_values, key=lambda v: abs(v - 5000))
    cut = min(cfg.x_values, key=lambda c: abs(c - 0.10))
    save = monthly_saved(spend, cut)
    daily = save / 30
    cups = daily / 20
    fv = savings_fv(save, cfg.savings_years, cfg.annual_return)
    return (f"换算：月消费 {spend:.0f} 元、降 {int(cut*100)}% → 每月省 <b>{save:.0f} 元</b> ≈ 每天 <b>{daily:.0f} 元</b>"
            f" ≈ <b>{cups:.0f} 杯奶茶/天</b>；{cfg.savings_years:.0f} 年后是 <b>{fv:.1f} 万</b>。"
            "省下的每一块钱，都是你的隐形存款。")


def render_cut_matrix_html(cfg: ScenarioConfig, out_path: str) -> str:
    """生成消费降级决策矩阵 HTML：行=当前月消费，列=降级幅度"""
    rows = build_cut_matrix(cfg)
    head_cells = ''.join(
        f'<th>降 {int(cfg.x_values[i]*100)}%</th>' for i in range(len(cfg.x_values)))
    body_rows = []
    for row in rows:
        tds = ''.join(
            f'<td style="background:{cell.color}">{cell.display}<small>{cut_judgment(cell.level)}</small></td>'
            for cell in row)
        body_rows.append(f'<tr><th class="rowhead">{row[0].row_label}</th>{tds}</tr>')
    legend = (
        '<div class="legend">'
        f'<span><i class="dot" style="background:{SAV_CUT_COLORS["comfort"]}"></i>≤10% 无痛</span>'
        f'<span><i class="dot" style="background:{SAV_CUT_COLORS["easy"]}"></i>≤20% 轻松</span>'
        f'<span><i class="dot" style="background:{SAV_CUT_COLORS["hard"]}"></i>≤30% 伤生活</span>'
        f'<span><i class="dot" style="background:{SAV_CUT_COLORS["extreme"]}"></i>&gt;30% 极限省</span>'
        '</div>'
    )
    emotion = f'<span class="emotion">{cfg.emotion}</span>' if cfg.emotion else ''
    convert_note = _cut_convert_note(cfg)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{cfg.title}</title>
<style>{SAV_PAGE_CSS}</style></head><body>
<div class="card">
  <h1>{cfg.hook_title or cfg.title}</h1>
  <div class="subtitle">{cfg.hook_line or cfg.subtitle}{emotion}</div>
  <div class="assume">假设：每月省下的钱定期投入，年化收益率 <b>{cfg.annual_return*100:.1f}%</b>（复利模型，年末计息），坚持 <b>{cfg.savings_years:.0f} 年</b>；
  未计通胀、未计中途取出；单元格 = 每月省 X 元 → {cfg.savings_years:.0f} 年后的隐形存款。
  决策断点：降幅 ≤ 10% 无痛、≤ 20% 轻松、≤ 30% 明显伤生活、&gt; 30% 极限省不建议硬扛。<br>{convert_note}</div>
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


def render_cut_result_card(cfg: ScenarioConfig, monthly_spend: float, cut_ratio: float,
                           out_path: str) -> str:
    """生成消费降级单点决策结果卡 HTML

    monthly_spend: 当前月消费（元）
    cut_ratio: 想降的幅度（0.1 = 降 10%）
    """
    r = single_cut_result(cfg, monthly_spend, cut_ratio)
    save = monthly_saved(monthly_spend, cut_ratio)
    amount = savings_fv(save, cfg.savings_years, cfg.annual_return)
    no_cut = 0.0
    daily = save / 30
    cups = daily / 20
    principal_wan = save * 12 * cfg.savings_years / 10000
    extra = max(0.0, amount - principal_wan)
    judgment = cut_judgment(r.level)
    big_text = f'每月省 {save:.0f} 元'
    rsub = (f'当前月消费 {monthly_spend:.0f} 元，降 {int(cut_ratio*100)}% → 每月省 {save:.0f} 元；'
            f'按 {cfg.annual_return*100:.1f}% 复利坚持 {cfg.savings_years:.0f} 年，隐形存款是 <b>{amount:.1f} 万</b>。')
    verdict_html = (
        '<div class="rverdict">'
        f'<b>决策判词：{judgment}</b><br>'
        f'断点参考：≤10% 无痛省；≤20% 轻松省；≤30% 明显伤生活；&gt;30% 极限省不建议硬扛。'
        '</div>'
    )
    compare_html = (
        '<div class="rcompare">'
        f'&nbsp;&nbsp;降了+复利：每月省 {save:.0f} 元 × {cfg.savings_years:.0f} 年 → <span class="rcmp-hi">{amount:.1f} 万</span><br>'
        f'&nbsp;&nbsp;如果当初没降：{cfg.savings_years:.0f} 年后的你，还是 <span class="rcmp-lo">0 元</span><br>'
        f'&nbsp;&nbsp;本金 {principal_wan:.1f} 万，多出来的 <b>{extra:.1f} 万</b>，是时间送你的。'
        '</div>'
    )
    quote = '省下的每一块钱，都是你的隐形存款——现在开始，还来得及。'
    convert_html = (
        '<div class="rconvert">'
        f'换算：每月省 {save:.0f} 元 ≈ 每天 <b>{daily:.0f} 元</b> ≈ <b>{cups:.0f} 杯奶茶/天</b>'
        '</div>'
    )
    share_html = ''
    if cfg.share_copy:
        share_text = cfg.share_copy.format(
            cut=f'{int(cut_ratio*100)}', saving=f'{save:.0f}', amount=f'{amount:.0f}')
        share_html = f'<div class="rshare"><span class="tag">可晒</span>{share_text}</div>'
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{cfg.title} · 结果卡</title>
<style>{SAV_CARD_CSS}</style></head><body>
<div class="rcard">
  <div class="rhead">{cfg.hook_title or cfg.title}</div>
  <div class="rlabel">你的决策</div>
  <div class="rbig" style="color:{r.color}">{big_text}</div>
  <div class="rsub">{rsub}</div>
  {verdict_html}
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


# ==================== 场景 2.2：房贷提前还款（每月多还一点，省多少利息） ====================

PREPAY_PAGE_CSS = """
  * { margin:0; padding:0; box-sizing:border-box; font-family:"Microsoft YaHei","PingFang SC",sans-serif; }
  body { background:#f6f7fb; padding:24px; }
  .card { background:#fff; border-radius:16px; box-shadow:0 4px 20px rgba(0,0,0,.08);
          max-width:980px; margin:0 auto; padding:28px 32px; }
  h1 { font-size:30px; color:#111827; text-align:center; }
  .subtitle { text-align:center; color:#6b7280; font-size:14px; margin:6px 0 18px; }
  .emotion { display:inline-block; background:#dcfce7; color:#166534; font-size:11px; padding:2px 8px;
             border-radius:999px; margin-left:8px; vertical-align:middle; font-weight:700; }
  .assume { background:#f3f4f6; border-radius:10px; padding:10px 14px; font-size:13px;
            color:#374151; margin-bottom:16px; line-height:1.7; }
  .assume b { color:#166534; }
  table { width:100%; border-collapse:separate; border-spacing:4px; }
  th { padding:10px 8px; font-size:14px; color:#111827; background:#eef2ff; border-radius:8px; }
  th.rowhead { text-align:left; width:110px; }
  td { padding:10px 6px; text-align:center; font-size:14px; font-weight:700;
       color:#fff; border-radius:8px; min-width:84px; line-height:1.5; }
  td small { display:block; font-size:11px; font-weight:400; opacity:.9; }
  .foot { margin-top:16px; font-size:12px; color:#9ca3af; line-height:1.6; }
  .watermark { margin-top:14px; text-align:center; font-size:12px; color:#9ca3af; letter-spacing:1px; }
  .legend { display:flex; justify-content:center; gap:16px; margin:12px 0 16px; font-size:12px; color:#374151; }
  .legend span { display:inline-flex; align-items:center; gap:6px; }
  .dot { width:14px; height:14px; border-radius:4px; display:inline-block; }
"""

PREPAY_CARD_CSS = """
  * { margin:0; padding:0; box-sizing:border-box; font-family:"Microsoft YaHei","PingFang SC",sans-serif; }
  body { background:#0f172a; padding:24px; display:flex; justify-content:center; }
  .rcard { background:linear-gradient(160deg,#1e293b,#0f172a); color:#fff; border-radius:20px;
           max-width:640px; padding:32px; box-shadow:0 12px 40px rgba(0,0,0,.4); }
  .rhead { font-size:20px; font-weight:700; color:#4ade80; line-height:1.5; }
  .rlabel { font-size:13px; color:#94a3b8; margin-top:22px; }
  .rbig { font-size:46px; font-weight:800; margin:4px 0 10px; letter-spacing:1px; line-height:1.25; }
  .rsub { font-size:14px; color:#cbd5e1; line-height:1.7; }
  .rverdict { margin-top:16px; background:#111827; border-left:4px solid #4ade80; border-radius:10px;
              padding:12px 16px; font-size:14px; line-height:1.8; }
  .rverdict b { color:#4ade80; }
  .rcompare { background:#111827; border-radius:12px; padding:14px 18px; margin-top:14px; font-size:14px; line-height:2; }
  .rcmp-hi { color:#4ade80; font-weight:700; }
  .rcmp-lo { color:#94a3b8; font-weight:700; }
  .rquote { margin-top:14px; font-size:15px; color:#4ade80; font-weight:700; text-align:center; }
  .rconvert { margin-top:14px; background:#052e16; border:1px solid #166534; border-radius:10px;
              padding:10px 14px; font-size:13px; color:#86efac; line-height:1.7; }
  .rconvert b { color:#4ade80; font-size:15px; }
  .rshare { margin-top:12px; background:#111827; border-left:3px solid #4ade80; border-radius:8px;
            padding:10px 14px; font-size:13px; color:#e2e8f0; line-height:1.8; }
  .rshare .tag { display:inline-block; background:#4ade80; color:#0f172a; font-size:11px; font-weight:700;
                 padding:1px 8px; border-radius:6px; margin-right:8px; }
  .rdisclaimer { margin-top:14px; font-size:11px; color:#64748b; line-height:1.6; }
  .rwatermark { margin-top:10px; text-align:center; font-size:11px; color:#64748b; letter-spacing:1px; }
"""


def _prepay_convert_note(cfg: ScenarioConfig) -> str:
    """提前还款换算句：锚点 = 贷款 100 万 × 每月多还 1000"""
    principal = min(cfg.y_values, key=lambda v: abs(v - 100))
    extra = min(cfg.x_values, key=lambda e: abs(e - 1000))
    months, interest, monthly = prepay_sim(
        principal, cfg.loan_rate_pct, cfg.loan_years, extra)
    base_interest = prepay_base_interest(principal, cfg.loan_rate_pct, cfg.loan_years)
    saved = max(0.0, base_interest - interest)
    years = months / 12
    return (f"换算：{principal:.0f} 万房贷、{cfg.loan_rate_pct:.1f}% 利率，月供 <b>{monthly:.0f} 元</b>；"
            f"每月多还 <b>{extra:.0f} 元</b> → 还清缩到 <b>{years:.0f} 年</b>，省利息 <b>{saved:.1f} 万</b>。"
            "你的月供，决定你敢不敢辞职。")


def render_prepay_matrix_html(cfg: ScenarioConfig, out_path: str) -> str:
    """生成房贷提前还款决策矩阵 HTML：行=贷款余额，列=每月额外还款"""
    rows = build_prepay_matrix(cfg)
    head_cells = ''.join(
        f'<th>{cfg.x_values[i]:.0f}元/月</th>' for i in range(len(cfg.x_values)))
    body_rows = []
    for row in rows:
        tds = ''.join(
            f'<td style="background:{cell.color}">{cell.display}<small>{prepay_judgment(cell.level)}</small></td>'
            for cell in row)
        body_rows.append(f'<tr><th class="rowhead">{row[0].row_label}</th>{tds}</tr>')
    legend = (
        '<div class="legend">'
        f'<span><i class="dot" style="background:{PREPAY_COLORS["big_save"]}"></i>省≥50% 强烈建议</span>'
        f'<span><i class="dot" style="background:{PREPAY_COLORS["save"]}"></i>省30-50% 划算</span>'
        f'<span><i class="dot" style="background:{PREPAY_COLORS["moderate"]}"></i>省10-30% 一般</span>'
        f'<span><i class="dot" style="background:{PREPAY_COLORS["minor"]}"></i>省&lt;10% 不值得</span>'
        '</div>'
    )
    emotion = f'<span class="emotion">{cfg.emotion}</span>' if cfg.emotion else ''
    convert_note = _prepay_convert_note(cfg)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{cfg.title}</title>
<style>{PREPAY_PAGE_CSS}</style></head><body>
<div class="card">
  <h1>{cfg.hook_title or cfg.title}</h1>
  <div class="subtitle">{cfg.hook_line or cfg.subtitle}{emotion}</div>
  <div class="assume">假设：等额本息，贷款年限 <b>{cfg.loan_years:.0f} 年</b>，年利率 <b>{cfg.loan_rate_pct:.1f}%</b>（LPR 假设，请按实际贷款合同调整）；
  每月在正常月供之外额外还一笔钱直接冲抵本金；未计提前还款违约金、税费与通胀。
  单元格 = 还清年限 + 相比不提前还省下的总利息；决策断点：节省利息 ≥ 50% 强烈建议、30-50% 划算、10-30% 一般、&lt; 10% 不值得。<br>{convert_note}</div>
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


def render_prepay_result_card(cfg: ScenarioConfig, principal_wan: float, extra_monthly: float,
                              out_path: str) -> str:
    """生成房贷提前还款单点决策结果卡 HTML

    principal_wan: 贷款余额（万元）
    extra_monthly: 每月额外还款（元）
    """
    r = single_prepay_result(cfg, principal_wan, extra_monthly)
    base_interest = prepay_base_interest(principal_wan, cfg.loan_rate_pct, cfg.loan_years)
    months, interest, monthly = prepay_sim(
        principal_wan, cfg.loan_rate_pct, cfg.loan_years, extra_monthly)
    years = months / 12
    saved = max(0.0, base_interest - interest)
    total_paid = principal_wan * 10000 + interest * 10000
    judgment = prepay_judgment(r.level)
    if extra_monthly <= 0:
        big_text = f'{int(round(years))}年'
        rsub = (f'贷款 {principal_wan:.0f} 万，年利率 {cfg.loan_rate_pct:.1f}%：'
                f'每月只还月供 {monthly:.0f} 元，还清要 {int(round(years))} 年，总利息约 {base_interest:.1f} 万。')
        quote = '什么都不做，30 年房贷就是 30 年——利息比你想的多。'
    else:
        big_text = f'省{saved:.0f}万'
        rsub = (f'贷款 {principal_wan:.0f} 万，年利率 {cfg.loan_rate_pct:.1f}%：'
                f'每月多还 {extra_monthly:.0f} 元 → 还清缩到 {years:.0f} 年，总利息从 {base_interest:.1f} 万降到 {interest:.1f} 万。')
        quote = f'每月多还 {extra_monthly:.0f} 元，30 年房贷缩到 {years:.0f} 年——省下的 {saved:.0f} 万，是银行少赚的。'
    verdict_html = (
        '<div class="rverdict">'
        f'<b>决策判词：{judgment}</b><br>'
        f'断点参考：节省利息 ≥50% 强烈建议；30-50% 划算；10-30% 一般；&lt;10% 不值得（不如拿去理财）。'
        '</div>'
    )
    no_prepay_yr = int(round(cfg.loan_years))
    compare_html = (
        '<div class="rcompare">'
        f'&nbsp;&nbsp;不提前还：{principal_wan:.0f} 万 / {cfg.loan_rate_pct:.1f}% → <span class="rcmp-lo">{no_prepay_yr} 年，利息 {base_interest:.1f} 万</span><br>'
        f'&nbsp;&nbsp;每月多还 {extra_monthly:.0f} 元：→ <span class="rcmp-hi">{years:.0f} 年，利息 {interest:.1f} 万</span><br>'
        f'&nbsp;&nbsp;省下 <b>{saved:.1f} 万</b>，相当于总利息打 {max(0.0, interest/base_interest*10):.1f} 折。'
        '</div>'
    )
    monthly_cups = monthly / 20
    convert_html = (
        '<div class="rconvert">'
        f'换算：每月多还 {extra_monthly:.0f} 元 ≈ 每天 <b>{extra_monthly/30:.0f} 元</b> ≈ <b>{extra_monthly/20:.0f} 杯奶茶/月</b>'
        '——少喝几杯奶茶，房贷早还几年。'
        '</div>'
    )
    share_html = ''
    if cfg.share_copy:
        share_text = cfg.share_copy.format(
            principal=f'{principal_wan:.0f}', extra=f'{extra_monthly:.0f}',
            years=f'{years:.0f}', saved=f'{saved:.0f}')
        share_html = f'<div class="rshare"><span class="tag">可晒</span>{share_text}</div>'
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{cfg.title} · 结果卡</title>
<style>{PREPAY_CARD_CSS}</style></head><body>
<div class="rcard">
  <div class="rhead">{cfg.hook_title or cfg.title}</div>
  <div class="rlabel">你的决策</div>
  <div class="rbig" style="color:{r.color}">{big_text}</div>
  <div class="rsub">{rsub}</div>
  {verdict_html}
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
