# -*- coding: utf-8 -*-
"""fin-decision-matrix · CLI 入口

用法：
  python main.py --matrix <scenario_json> <out_html>
  python main.py --card <scenario_json> <principal> <spend> [compare_principal] <out_html>
"""
import argparse
import json
import sys
from engine.core import ScenarioConfig
from engine.render import render_matrix_html, render_result_card


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
        annual_return=d['annual_return'],
        perpetual_threshold=d['perpetual_threshold'],
        disclaimer=d['disclaimer'],
        watermark=d['watermark'],
    )


def main():
    parser = argparse.ArgumentParser(description='躺平退休决策计算器')
    parser.add_argument('--mode', choices=['matrix', 'card'], required=True)
    parser.add_argument('--scenario', required=True, help='场景配置 JSON')
    parser.add_argument('--out', required=True, help='输出 HTML 路径')
    parser.add_argument('--principal', type=float, default=None)
    parser.add_argument('--spend', type=float, default=None)
    parser.add_argument('--compare', type=float, default=None, help='对比本金')
    args = parser.parse_args()

    cfg = load_config(args.scenario)
    if args.mode == 'matrix':
        path = render_matrix_html(cfg, args.out)
        print(f'[matrix] 已生成: {path}')
    elif args.mode == 'card':
        if args.principal is None or args.spend is None:
            print('card 模式需要 --principal 与 --spend', file=sys.stderr)
            sys.exit(1)
        compare = args.compare if args.compare else cfg.x_values[0]
        path = render_result_card(cfg, args.principal, args.spend, compare, args.out)
        print(f'[card] 已生成: {path}')


if __name__ == '__main__':
    main()
