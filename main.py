# -*- coding: utf-8 -*-
"""fin-decision-matrix · CLI 入口

用法：
  python main.py --mode matrix --scenario <scenario_json> --out <out_html>
  python main.py --mode card --scenario <scenario_json> --out <out_html> [--arg1 V] [--arg2 V] [--extra V]

场景类型（scenario_type）：
  retire: 躺平退休（arg1=存款万, arg2=年花万, extra=对比存款万）
  debt:   信用卡最低还款（arg1=债务万, arg2=年利率%, extra=每月多还元）
  savings_cut: 消费降级（arg1=当前月消费元, arg2=降级幅度小数如0.1）
"""
import argparse
import json
import sys
from engine.core import ScenarioConfig
from engine.render import (render_matrix_html, render_result_card,
                           render_debt_matrix_html, render_debt_result_card,
                           render_cut_matrix_html, render_cut_result_card,
                           render_prepay_matrix_html, render_prepay_result_card,
                           render_tuition_matrix_html, render_tuition_result_card)


def load_config(path: str) -> ScenarioConfig:
    with open(path, 'r', encoding='utf-8') as f:
        d = json.load(f)
    return ScenarioConfig(
        title=d['title'],
        subtitle=d['subtitle'],
        x_name=d['x_name'],
        x_unit=d['x_unit'],
        x_values=d['x_values'],
        y_name=d['y_name'],
        y_unit=d['y_unit'],
        y_values=d['y_values'],
        annual_return=d.get('annual_return', 0.0),
        perpetual_threshold=d.get('perpetual_threshold', 80),
        disclaimer=d['disclaimer'],
        watermark=d['watermark'],
        hook_title=d.get('hook_title', ''),
        hook_line=d.get('hook_line', ''),
        emotion=d.get('emotion', ''),
        convert=d.get('convert'),
        share_copy=d.get('share_copy', ''),
        min_payment_ratio=d.get('min_payment_ratio', 0.02),
        min_payment_floor=d.get('min_payment_floor', 50.0),
        loan_rate_pct=d.get('loan_rate_pct', 3.9),
        loan_years=d.get('loan_years', 30.0),
        scenario_type=d.get('scenario_type', 'retire'),
    )


def main():
    parser = argparse.ArgumentParser(description='fin-decision-matrix 决策计算器')
    parser.add_argument('--mode', choices=['matrix', 'card'], required=True)
    parser.add_argument('--scenario', required=True, help='场景配置 JSON')
    parser.add_argument('--out', required=True, help='输出 HTML 路径')
    parser.add_argument('--arg1', type=float, default=None, help='参数1（本金/债务）')
    parser.add_argument('--arg2', type=float, default=None, help='参数2（年花/利率）')
    parser.add_argument('--extra', type=float, default=None, help='对比参数（对比本金/每月多还）')
    args = parser.parse_args()

    cfg = load_config(args.scenario)
    if args.mode == 'matrix':
        if cfg.scenario_type == 'debt':
            path = render_debt_matrix_html(cfg, args.out)
        elif cfg.scenario_type == 'savings_cut':
            path = render_cut_matrix_html(cfg, args.out)
        elif cfg.scenario_type == 'prepay':
            path = render_prepay_matrix_html(cfg, args.out)
        elif cfg.scenario_type == 'tuition':
            path = render_tuition_matrix_html(cfg, args.out)
        else:
            path = render_matrix_html(cfg, args.out)
        print(f'[matrix] 已生成: {path}')
    elif args.mode == 'card':
        if args.arg1 is None or args.arg2 is None:
            print('card 模式需要 --arg1 与 --arg2', file=sys.stderr)
            sys.exit(1)
        if cfg.scenario_type == 'debt':
            extra = args.extra if args.extra else 500
            path = render_debt_result_card(cfg, args.arg1, args.arg2, extra, args.out)
        elif cfg.scenario_type == 'savings_cut':
            path = render_cut_result_card(cfg, args.arg1, args.arg2, args.out)
        elif cfg.scenario_type == 'prepay':
            path = render_prepay_result_card(cfg, args.arg1, args.arg2, args.out)
        elif cfg.scenario_type == 'tuition':
            path = render_tuition_result_card(cfg, args.arg1, args.arg2, args.out)
        else:
            compare = args.extra if args.extra else cfg.x_values[0]
            path = render_result_card(cfg, args.arg1, args.arg2, compare, args.out)
        print(f'[card] 已生成: {path}')


if __name__ == '__main__':
    main()
