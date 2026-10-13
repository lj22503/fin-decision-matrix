# -*- coding: utf-8 -*-
"""fin-decision-matrix · HTML 渲染

输出两类可截图产物：
1. 决策矩阵图（投顾生图端）：二维热力表格，红→琥珀→绿，"花不完"高亮。
2. 结果卡（用户自选端）：单点结论，大数字 + 对比条 + 换算句 + 文案。
设计依据：陈锦初传播方法论《截图即内容》规范。
"""
import math
from .core import (ScenarioConfig, MatrixResult, build_matrix, single_result,
                   CELL_COLORS, build_debt_matrix, single_debt_result,
                   debt_payoff_years, DEBT_COLORS,
                   build_cut_matrix, single_cut_result, monthly_saved,
                   savings_fv, cut_judgment, SAV_CUT_COLORS,
                   build_prepay_matrix, single_prepay_result,
                   prepay_sim, prepay_base_interest, prepay_save_ratio,
                   prepay_judgment, PREPAY_COLORS, annuity_monthly_payment,
                   build_tuition_matrix, single_tuition_result,
                   tuition_payback_months, tuition_extra_gain,
                   tuition_display, tuition_judgment, TUITION_COLORS,
                   build_emergency_matrix, single_emergency_result,
                   emergency_fund_need, emergency_judgment,
                   emergency_level, EMERGENCY_COLORS,
                   build_dca_matrix, single_dca_result,
                   dca_fv, dca_judgment, dca_level, dca_late_gap, DCA_COLORS)

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


# ==================== 场景 7.2：应急金（我该留多少救命钱？） ====================

EMERGENCY_PAGE_CSS = """
  * { margin:0; padding:0; box-sizing:border-box; font-family:"Microsoft YaHei","PingFang SC",sans-serif; }
  body { background:#f6f7fb; padding:24px; }
  .card { background:#fff; border-radius:16px; box-shadow:0 4px 20px rgba(0,0,0,.08);
          max-width:980px; margin:0 auto; padding:28px 32px; }
  h1 { font-size:30px; color:#111827; text-align:center; }
  .subtitle { text-align:center; color:#6b7280; font-size:14px; margin:6px 0 18px; }
  .emotion { display:inline-block; background:#dbeafe; color:#1d4ed8; font-size:11px; padding:2px 8px;
             border-radius:999px; margin-left:8px; vertical-align:middle; font-weight:700; }
  .assume { background:#f3f4f6; border-radius:10px; padding:10px 14px; font-size:13px;
            color:#374151; margin-bottom:16px; line-height:1.7; }
  .assume b { color:#1d4ed8; }
  table { width:100%; border-collapse:separate; border-spacing:4px; }
  th { padding:10px 8px; font-size:14px; color:#111827; background:#e0f2fe; border-radius:8px; }
  th.rowhead { text-align:left; width:120px; }
  td { padding:10px 6px; text-align:center; font-size:15px; font-weight:700;
       color:#fff; border-radius:8px; min-width:96px; line-height:1.5; }
  td small { display:block; font-size:11px; font-weight:400; opacity:.9; }
  .foot { margin-top:16px; font-size:12px; color:#9ca3af; line-height:1.6; }
  .watermark { margin-top:14px; text-align:center; font-size:12px; color:#9ca3af; letter-spacing:1px; }
  .legend { display:flex; justify-content:center; gap:16px; margin:12px 0 16px; font-size:12px; color:#374151; flex-wrap:wrap; }
  .legend span { display:inline-flex; align-items:center; gap:6px; }
  .dot { width:14px; height:14px; border-radius:4px; display:inline-block; }
"""

EMERGENCY_CARD_CSS = """
  * { margin:0; padding:0; box-sizing:border-box; font-family:"Microsoft YaHei","PingFang SC",sans-serif; }
  body { background:#0c1226; padding:24px; display:flex; justify-content:center; }
  .rcard { background:linear-gradient(160deg,#1e2a4a,#0c1226); color:#fff; border-radius:20px;
           max-width:640px; padding:32px; box-shadow:0 12px 40px rgba(0,0,0,.4); }
  .rhead { font-size:20px; font-weight:700; color:#60a5fa; line-height:1.5; }
  .rlabel { font-size:13px; color:#94a3b8; margin-top:22px; }
  .rbig { font-size:46px; font-weight:800; margin:4px 0 10px; letter-spacing:1px; line-height:1.25; }
  .rsub { font-size:14px; color:#cbd5e1; line-height:1.7; }
  .rverdict { margin-top:16px; background:#0f172a; border-left:4px solid #60a5fa; border-radius:10px;
              padding:12px 16px; font-size:14px; line-height:1.8; }
  .rverdict b { color:#60a5fa; }
  .rcompare { background:#0f172a; border-radius:12px; padding:14px 18px; margin-top:14px; font-size:14px; line-height:2; }
  .rcmp-hi { color:#60a5fa; font-weight:700; }
  .rcmp-lo { color:#94a3b8; font-weight:700; }
  .rquote { margin-top:14px; font-size:15px; color:#60a5fa; font-weight:700; text-align:center; }
  .rconvert { margin-top:14px; background:#0a2540; border:1px solid #1e3a8a; border-radius:10px;
              padding:10px 14px; font-size:13px; color:#93c5fd; line-height:1.7; }
  .rconvert b { color:#60a5fa; font-size:15px; }
  .rshare { margin-top:12px; background:#0f172a; border-left:3px solid #60a5fa; border-radius:8px;
            padding:10px 14px; font-size:13px; color:#e2e8f0; line-height:1.8; }
  .rshare .tag { display:inline-block; background:#60a5fa; color:#0c1226; font-size:11px; font-weight:700;
                 padding:1px 8px; border-radius:6px; margin-right:8px; }
  .rdisclaimer { margin-top:14px; font-size:11px; color:#64748b; line-height:1.6; }
  .rwatermark { margin-top:10px; text-align:center; font-size:11px; color:#64748b; letter-spacing:1px; }
"""


def _emergency_convert_note(cfg: ScenarioConfig) -> str:
    """应急金换算句：锚点 = 月支出 1 万 × 6 个月"""
    expense = min(cfg.y_values, key=lambda v: abs(v - 1))
    months = min(cfg.x_values, key=lambda m: abs(m - 6))
    need = emergency_fund_need(expense, months)
    return (f"换算：月固定支出 {expense:.1f} 万、留 <b>{months:.0f} 个月</b> → 应急金 <b>{need:.0f} 万</b>。"
            "安全感不是玄学，是几个月工资。")


def render_emergency_matrix_html(cfg: ScenarioConfig, out_path: str) -> str:
    """生成应急金决策矩阵 HTML：行=月固定支出，列=目标安全月数"""
    rows = build_emergency_matrix(cfg)
    head_cells = ''.join(
        f'<th>{cfg.x_values[i]:.0f}个月</th>' for i in range(len(cfg.x_values)))
    body_rows = []
    for row in rows:
        tds = ''.join(
            f'<td style="background:{cell.color}">{cell.display.split(" · ")[0]}<small>安全月数 {cell.display.split(" · ")[1]}</small></td>'
            for cell in row)
        body_rows.append(f'<tr><th class="rowhead">{row[0].row_label}</th>{tds}</tr>')
    legend = (
        '<div class="legend">'
        f'<span><i class="dot" style="background:{EMERGENCY_COLORS["bare"]}"></i>不足3个月 赤贫级</span>'
        f'<span><i class="dot" style="background:{EMERGENCY_COLORS["minimal"]}"></i>3-6个月 底线</span>'
        f'<span><i class="dot" style="background:{EMERGENCY_COLORS["standard"]}"></i>6-9个月 标准</span>'
        f'<span><i class="dot" style="background:{EMERGENCY_COLORS["solid"]}"></i>9-12个月 稳健</span>'
        f'<span><i class="dot" style="background:{EMERGENCY_COLORS["plenty"]}"></i>12个月+ 充裕</span>'
        '</div>'
    )
    emotion = f'<span class="emotion">{cfg.emotion}</span>' if cfg.emotion else ''
    convert_note = _emergency_convert_note(cfg)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{cfg.title}</title>
<style>{EMERGENCY_PAGE_CSS}</style></head><body>
<div class="card">
  <h1>{cfg.hook_title or cfg.title}</h1>
  <div class="subtitle">{cfg.hook_line or cfg.subtitle}{emotion}</div>
  <div class="assume">假设：应急金 = 月固定支出 × 目标安全月数。档位参考：单收入家庭建议 6-9 个月、双收入 3-6 个月、有老人需赡养 9-12 个月。超过 12 个月的现金会跑输通胀，建议转低波理财。<br>{convert_note}</div>
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


def render_emergency_result_card(cfg: ScenarioConfig, monthly_expense_wan: float, safety_months: float,
                                 out_path: str) -> str:
    """生成应急金单点决策结果卡 HTML

    monthly_expense_wan: 月固定支出（万元）
    safety_months: 目标安全月数（3-12）
    """
    r = single_emergency_result(cfg, monthly_expense_wan, safety_months)
    need = emergency_fund_need(monthly_expense_wan, safety_months)
    judgment = emergency_judgment(r.level)
    big_text = f'{need:.1f} 万'
    rsub = (f'月固定支出 {monthly_expense_wan:.1f} 万 × 目标安全月数 {safety_months:.0f} 个月 → '
            f'建议应急金 {need:.1f} 万。')
    quote = f'你的安全感，值 {safety_months:.0f} 个月工资——先留够救命钱，再谈投资。'
    verdict_html = (
        '<div class="rverdict">'
        f'<b>决策判词：{judgment}</b><br>'
        '档位参考：不足 3 个月赤贫级；3-6 个月底线；6-9 个月标准；9-12 个月稳健；12 个月以上充裕（可转低波理财）。'
        '</div>'
    )
    compare_html = (
        '<div class="rcompare">'
        f'&nbsp;&nbsp;只留 3 个月：&nbsp;&nbsp;约 <span class="rcmp-lo">{monthly_expense_wan*3:.1f} 万</span>——突发开支一来就崩<br>'
        f'&nbsp;&nbsp;留到 {safety_months:.0f} 个月：<b>{need:.1f} 万</b>——<span class="rcmp-hi">多备 {monthly_expense_wan*(safety_months-3):.1f} 万</span>，换一份从容<br>'
        f'&nbsp;&nbsp;差值：<b>{monthly_expense_wan*(safety_months-3):.1f} 万</b>——这就是你给自己买的"失业保险"。'
        '</div>'
    )
    convert_html = (
        '<div class="rconvert">'
        f'换算：{need:.1f} 万应急金 ≈ {safety_months:.0f} 个月工资 ≈ '
        f'<b>{need*10000/30:.0f} 杯奶茶</b>——关键时刻，它是你的底气和话语权。'
        '</div>'
    )
    share_html = ''
    if cfg.share_copy:
        share_text = cfg.share_copy.format(
            expense=f'{monthly_expense_wan:.1f}', months=f'{safety_months:.0f}',
            need=f'{need:.1f}')
        share_html = f'<div class="rshare"><span class="tag">可晒</span>{share_text}</div>'
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{cfg.title} · 结果卡</title>
<style>{EMERGENCY_CARD_CSS}</style></head><body>
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

# ==================== 场景 6.2：技能投资回收期（这笔学费，值不值？） ====================

TUITION_PAGE_CSS = """
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

TUITION_CARD_CSS = """
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


def _tuition_convert_note(cfg: ScenarioConfig) -> str:
    """学费换算句：锚点 = 学费 3 万 × 月薪涨 5000"""
    tuition = min(cfg.y_values, key=lambda v: abs(v - 3))
    rise = min(cfg.x_values, key=lambda r: abs(r - 5000))
    months = tuition_payback_months(tuition, rise)
    gain = tuition_extra_gain(tuition, rise)
    daily = rise / 30
    return (f"换算：{tuition:.0f} 万学费、月薪涨 <b>{rise:.0f} 元</b> → <b>{tuition_display(months)}</b>，"
            f"回本后 5 年累计多赚 <b>{gain:.0f} 万</b>（每天多赚 <b>{daily:.0f} 元</b>）。"
            "学技能，先算回本周期。")


def render_tuition_matrix_html(cfg: ScenarioConfig, out_path: str) -> str:
    """生成学费回收期决策矩阵 HTML：行=学费投入，列=预期月薪涨幅"""
    rows = build_tuition_matrix(cfg)
    head_cells = ''.join(
        f'<th>+{cfg.x_values[i]:.0f}元/月</th>' for i in range(len(cfg.x_values)))
    body_rows = []
    for row in rows:
        tds = ''.join(
            f'<td style="background:{cell.color}">{cell.display.split(" · ")[0]}<small>后5年多赚{cell.display.split(" · ")[1].replace("后5年多赚", "")}</small></td>'
            for cell in row)
        body_rows.append(f'<tr><th class="rowhead">{row[0].row_label}</th>{tds}</tr>')
    legend = (
        '<div class="legend">'
        f'<span><i class="dot" style="background:{TUITION_COLORS["fast"]}"></i>回本≤12个月 闭眼投</span>'
        f'<span><i class="dot" style="background:{TUITION_COLORS["good"]}"></i>12-24个月 划算</span>'
        f'<span><i class="dot" style="background:{TUITION_COLORS["okay"]}"></i>24-36个月 一般</span>'
        f'<span><i class="dot" style="background:{TUITION_COLORS["slow"]}"></i>&gt;36个月 不值得</span>'
        '</div>'
    )
    emotion = f'<span class="emotion">{cfg.emotion}</span>' if cfg.emotion else ''
    convert_note = _tuition_convert_note(cfg)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{cfg.title}</title>
<style>{TUITION_PAGE_CSS}</style></head><body>
<div class="card">
  <h1>{cfg.hook_title or cfg.title}</h1>
  <div class="subtitle">{cfg.hook_line or cfg.subtitle}{emotion}</div>
  <div class="assume">假设：回本周期 = 学费 ÷ 月薪涨幅，即"多赚的钱追平投入"所需月数；未计折现、跳槽风险与职业天花板差异。
  单元格 = 回本周期 + 回本后 5 年累计多赚；决策断点：回本 ≤ 12 个月闭眼投、12-24 个月划算、24-36 个月一般、&gt; 36 个月不值得。<br>{convert_note}</div>
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


def render_tuition_result_card(cfg: ScenarioConfig, tuition_wan: float, salary_rise: float,
                               out_path: str) -> str:
    """生成学费单点决策结果卡 HTML

    tuition_wan: 学费/投入（万元）
    salary_rise: 预期月薪涨幅（元/月）
    """
    r = single_tuition_result(cfg, tuition_wan, salary_rise)
    months = tuition_payback_months(tuition_wan, salary_rise)
    gain = tuition_extra_gain(tuition_wan, salary_rise)
    judgment = tuition_judgment(r.level)
    if math.isinf(months):
        big_text = '回不了本'
        rsub = f'学费 {tuition_wan:.0f} 万、月薪不涨：这笔投入没有回收期，花的每一分都在亏。'
        quote = '不涨薪的培训，是最贵的消费。'
    else:
        big_text = tuition_display(months)
        rsub = (f'学费 {tuition_wan:.0f} 万、预期月薪涨 {salary_rise:.0f} 元 → {tuition_display(months)}，'
                f'回本后 5 年累计多赚 {gain:.0f} 万。')
        quote = f'{tuition_wan:.0f} 万学费、月薪涨 {salary_rise:.0f} 元，{tuition_display(months)}——剩下的都是赚的。'
    verdict_html = (
        '<div class="rverdict">'
        f'<b>决策判词：{judgment}</b><br>'
        '断点参考：回本 ≤12 个月闭眼投；12-24 个月划算；24-36 个月一般；&gt;36 个月不值得（不如先存钱）。'
        '</div>'
    )
    daily_rise = salary_rise / 30
    compare_html = (
        '<div class="rcompare">'
        f'&nbsp;&nbsp;不学：&nbsp;&nbsp;&nbsp;&nbsp;月薪维持 <span class="rcmp-lo">{salary_rise:.0f} 元涨幅为 0</span><br>'
        f'&nbsp;&nbsp;学了：&nbsp;&nbsp;&nbsp;&nbsp;月薪涨 <span class="rcmp-hi">{salary_rise:.0f} 元</span>，'
        f'回本后 5 年累计多赚 <b>{gain:.1f} 万</b><br>'
        f'&nbsp;&nbsp;差值：<b>{gain:.1f} 万</b>——多赚的部分，全是你给自己的加薪。'
        '</div>'
    )
    convert_html = (
        '<div class="rconvert">'
        f'换算：月薪涨 {salary_rise:.0f} 元 ≈ 每天多赚 <b>{daily_rise:.0f} 元</b> ≈ <b>{salary_rise/20:.0f} 杯奶茶/月</b>'
        '——这笔"隐形加薪"，比涨薪更可控。'
        '</div>'
    )
    share_html = ''
    if cfg.share_copy:
        share_text = cfg.share_copy.format(
            tuition=f'{tuition_wan:.0f}', rise=f'{salary_rise:.0f}',
            payback=tuition_display(months), gain=f'{gain:.0f}')
        share_html = f'<div class="rshare"><span class="tag">可晒</span>{share_text}</div>'
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{cfg.title} · 结果卡</title>
<style>{TUITION_CARD_CSS}</style></head><body>
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


# ==================== 场景 1.1：定投复利（开始定投晚一年，到底差多少？） ====================

DCA_PAGE_CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Microsoft YaHei','PingFang SC',sans-serif; background:#f6f7fb; color:#1f2937; padding:24px; }
.card { max-width:880px; margin:0 auto; background:#fff; border-radius:16px; padding:28px 32px; box-shadow:0 4px 20px rgba(0,0,0,.06); }
h1 { font-size:26px; color:#0f172a; margin-bottom:6px; }
.subtitle { color:#64748b; font-size:14px; margin-bottom:14px; }
.emotion { display:inline-block; margin-left:8px; background:#ecfdf5; color:#059669; border-radius:20px; padding:2px 12px; font-size:12px; }
.assume { background:#f0fdf4; border-left:4px solid #22c55e; padding:10px 14px; border-radius:8px; color:#374151; font-size:13px; line-height:1.7; margin-bottom:14px; }
.legend { margin:10px 0 14px; font-size:12px; color:#475569; display:flex; flex-wrap:wrap; gap:10px 16px; }
.legend .dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:4px; vertical-align:middle; }
table { width:100%; border-collapse:collapse; }
th { background:#f1f5f9; color:#475569; font-size:14px; padding:10px 8px; border:1px solid #e2e8f0; }
td { color:#fff; text-align:center; font-weight:700; font-size:17px; padding:12px 8px; border:1px solid #e2e8f0; }
td small { display:block; font-weight:400; font-size:11px; opacity:.95; margin-top:2px; }
th.rowhead { background:#e2e8f0; color:#1e293b; font-size:13px; }
.foot { color:#94a3b8; font-size:11px; margin-top:14px; line-height:1.6; }
.watermark { color:#cbd5e1; font-size:10px; text-align:right; margin-top:6px; }
"""

DCA_CARD_CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Microsoft YaHei','PingFang SC',sans-serif; background:linear-gradient(160deg,#064e3b,#065f46); min-height:100vh; padding:24px; display:flex; align-items:center; justify-content:center; }
.rcard { max-width:560px; background:#fff; border-radius:20px; padding:32px 30px; box-shadow:0 12px 40px rgba(0,0,0,.35); }
.rhead { font-size:20px; color:#0f172a; font-weight:700; margin-bottom:4px; }
.rlabel { color:#94a3b8; font-size:12px; margin:18px 0 4px; }
.rbig { font-size:46px; font-weight:800; line-height:1.15; }
.rsub { color:#64748b; font-size:13px; margin:6px 0 14px; }
.rverdict { background:#f8fafc; border-radius:10px; padding:12px 14px; font-size:13px; color:#334155; line-height:1.7; margin-bottom:10px; }
.rverdict b { color:#065f46; }
.rcompare { background:#fffbeb; border-radius:10px; padding:12px 14px; font-size:13px; color:#57534e; line-height:1.8; margin-bottom:10px; }
.rcmp-lo { color:#dc2626; font-weight:700; }
.rcmp-hi { color:#059669; font-weight:700; }
.rconvert { background:#ecfdf5; border-radius:10px; padding:12px 14px; font-size:13px; color:#065f46; line-height:1.7; margin-bottom:10px; }
.rconvert b { color:#047857; }
.rquote { font-size:14px; color:#475569; padding:8px 0 4px; font-style:italic; }
.rshare { background:#f0fdf4; border:1px dashed #86efac; border-radius:10px; padding:10px 14px; font-size:13px; color:#166534; margin:10px 0; }
.rshare .tag { background:#22c55e; color:#fff; border-radius:4px; padding:1px 8px; font-size:11px; margin-right:6px; }
.rdisclaimer { color:#94a3b8; font-size:10px; margin-top:12px; line-height:1.6; }
.rwatermark { color:#cbd5e1; font-size:10px; text-align:right; margin-top:4px; }
"""


def _dca_convert_note(cfg: ScenarioConfig) -> str:
    """定投换算句：每月定投金额 ≈ 每天多少 ≈ 奶茶"""
    monthly = min(cfg.y_values, key=lambda v: abs(v - 1000))
    age = min(cfg.x_values, key=lambda a: abs(a - 25))
    asset = dca_fv(monthly, age)
    daily = monthly / 30
    return (f'换算：每月定投 {monthly:.0f} 元 ≈ 每天 {daily:.0f} 元 ≈ {monthly/20:.0f} 杯奶茶/月——'
            f'从 {age:.0f} 岁开始，60 岁约 <b>{asset:.0f} 万</b>。')


def render_dca_matrix_html(cfg: ScenarioConfig, out_path: str) -> str:
    """生成定投决策矩阵 HTML：行=每月定投金额，列=开始年龄"""
    rows = build_dca_matrix(cfg)
    head_cells = ''.join(
        f'<th>{cfg.x_values[i]:.0f}岁</th>' for i in range(len(cfg.x_values)))
    body_rows = []
    for row in rows:
        tds = ''.join(
            f'<td style="background:{cell.color}">{cell.display}<small>60岁资产</small></td>'
            for cell in row)
        body_rows.append(f'<tr><th class="rowhead">{row[0].row_label}</th>{tds}</tr>')
    legend = (
        '<div class="legend">'
        f'<span><i class="dot" style="background:{DCA_COLORS["small"]}"></i>&lt;50万</span>'
        f'<span><i class="dot" style="background:{DCA_COLORS["mid"]}"></i>50-150万</span>'
        f'<span><i class="dot" style="background:{DCA_COLORS["good"]}"></i>150-300万</span>'
        f'<span><i class="dot" style="background:{DCA_COLORS["big"]}"></i>300-600万</span>'
        f'<span><i class="dot" style="background:{DCA_COLORS["huge"]}"></i>600万+</span>'
        '</div>'
    )
    emotion = f'<span class="emotion">{cfg.emotion}</span>' if cfg.emotion else ''
    convert_note = _dca_convert_note(cfg)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{cfg.title}</title>
<style>{DCA_PAGE_CSS}</style></head><body>
<div class="card">
  <h1>{cfg.hook_title or cfg.title}</h1>
  <div class="subtitle">{cfg.hook_line or cfg.subtitle}{emotion}</div>
  <div class="assume">假设：每月定投金额固定不变，长期年化 8%（A股/美股宽基指数长期平均口径，不代表每年收益）。单元格 = 定投到 60 岁的总资产。<br>{convert_note}</div>
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


def render_dca_result_card(cfg: ScenarioConfig, monthly: float, start_age: float,
                           out_path: str) -> str:
    """生成定投单点决策结果卡 HTML

    monthly: 每月定投金额（元）
    start_age: 开始定投年龄（20-40）
    """
    r = single_dca_result(cfg, monthly, start_age)
    asset = dca_fv(monthly, start_age)
    judgment = dca_judgment(r.level)
    big_text = f'{asset:.0f} 万'
    rsub = (f'每月定投 {monthly:.0f} 元 × 从 {start_age:.0f} 岁开始 → 60 岁总资产 {asset:.0f} 万'
            f'（年化 8%）。')
    quote = f'晚开始 5 年，少赚一辆车——最好的定投时机，就是现在。'
    gap5 = dca_late_gap(monthly, start_age, start_age + 5)
    gap10 = dca_late_gap(monthly, start_age, start_age + 10)
    verdict_html = (
        '<div class="rverdict">'
        f'<b>决策判词：{judgment}</b><br>'
        '档位参考：60 岁资产 &lt;50 万 储蓄率不足；50-150 万 有积累；150-300 万 复利发力；300-600 万 时间玫瑰；600 万以上 复利放大器。'
        '</div>'
    )
    compare_html = (
        '<div class="rcompare">'
        f'&nbsp;&nbsp;晚 5 年开始：&nbsp;&nbsp;约少 <span class="rcmp-lo">{gap5:.0f} 万</span><br>'
        f'&nbsp;&nbsp;晚 10 年开始：约少 <span class="rcmp-lo">{gap10:.0f} 万</span><br>'
        f'&nbsp;&nbsp;差值：<b>{gap10-gap5:.0f} 万</b>——拖得越久，越追不回时间。'
        '</div>'
    )
    convert_html = (
        '<div class="rconvert">'
        f'换算：每月 {monthly:.0f} 元 ≈ 每天 {monthly/30:.0f} 元 ≈ {monthly/20:.0f} 杯奶茶/月——'
        f'少喝 {monthly/20:.0f} 杯奶茶，60 岁多 <b>{asset:.0f} 万</b>。'
        '</div>'
    )
    share_html = ''
    if cfg.share_copy:
        share_text = cfg.share_copy.format(
            monthly=f'{monthly:.0f}', start_age=f'{start_age:.0f}', asset=f'{asset:.0f}')
        share_html = f'<div class="rshare"><span class="tag">可晒</span>{share_text}</div>'
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{cfg.title} · 结果卡</title>
<style>{DCA_CARD_CSS}</style></head><body>
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
