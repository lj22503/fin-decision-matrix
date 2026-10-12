# -*- coding: utf-8 -*-
"""fin-decision-matrix · 计算核心

基于「二维决策图例法」的可持续年限计算引擎。
模型：固定年化实际收益率下的年金耗尽公式（4% 规则升级版）。
"""
import math
from dataclasses import dataclass


@dataclass
class MatrixResult:
    """矩阵单元格数据"""
    row_label: str          # 行标签（年花费）
    col_label: str          # 列标签（本金）
    years: float            # 可持续年数（inf 表示永续）
    display: str            # 展示文本（"花不完" / "X年"）
    level: str              # 风险档位：safe / ok / warn / danger
    color: str              # 单元格背景色


@dataclass
class ScenarioConfig:
    """场景配置（对应 scenarios/*.json）"""
    title: str
    subtitle: str
    x_name: str                     # 横轴名称（本金）
    x_unit: str
    x_values: list                  # 本金序列（万元）
    y_name: str                     # 纵轴名称（年花费）
    y_unit: str
    y_values: list                  # 年花费序列（万元）
    annual_return: float            # 年化实际收益率（已扣通胀）
    perpetual_threshold: float      # 超过该年数视为"花不完"
    disclaimer: str
    watermark: str


CELL_COLORS = {
    'safe':   '#15803d',   # 花不完 / 永续（深绿）
    'ok':     '#22c55e',   # >=30年（绿）
    'warn':   '#f59e0b',   # 10-30年（琥珀）
    'danger': '#dc2626',   # <10年（红）
}


def sustainable_years(principal: float, annual_spend: float, rate: float) -> float:
    """资金可持续年限（年金公式）。

    principal: 初始本金（万元）
    annual_spend: 年度花费（万元）
    rate: 年化实际收益率（如 0.04）

    若年花费 <= 本金×收益率（收益覆盖花费）→ 永续（inf）。
    否则 n = log(1 + r·P/E) / log(1 + r)。
    """
    if annual_spend <= 0:
        return float('inf')
    if principal <= 0:
        return 0.0
    if annual_spend <= principal * rate:
        return float('inf')
    n = math.log(1 + rate * principal / annual_spend) / math.log(1 + rate)
    return n


def risk_level(years: float, threshold: float) -> str:
    """按可持续年限划分风险档位"""
    if math.isinf(years) or years >= threshold:
        return 'safe'
    if years >= 30:
        return 'ok'
    if years >= 10:
        return 'warn'
    return 'danger'


def format_years(years: float, threshold: float) -> str:
    """展示文本：花不完 / X年"""
    if math.isinf(years) or years >= threshold:
        return '花不完'
    if years >= 20:
        return f'{int(round(years))}年'
    return f'{years:.1f}年'


def build_matrix(cfg: ScenarioConfig) -> list:
    """构建矩阵数据：rows[年花费][本金] = MatrixResult"""
    rows = []
    for spend in cfg.y_values:
        row = []
        for principal in cfg.x_values:
            years = sustainable_years(principal, spend, cfg.annual_return)
            level = risk_level(years, cfg.perpetual_threshold)
            row.append(MatrixResult(
                row_label=f'{spend}{cfg.y_unit}',
                col_label=f'{principal}{cfg.x_unit}',
                years=years,
                display=format_years(years, cfg.perpetual_threshold),
                level=level,
                color=CELL_COLORS[level],
            ))
        rows.append(row)
    return rows


def single_result(cfg: ScenarioConfig, principal: float, spend: float) -> MatrixResult:
    """单点查询（用户自选端）：输入自己的两个变量直接出结论"""
    years = sustainable_years(principal, spend, cfg.annual_return)
    level = risk_level(years, cfg.perpetual_threshold)
    return MatrixResult(
        row_label=f'{spend}{cfg.y_unit}',
        col_label=f'{principal}{cfg.x_unit}',
        years=years,
        display=format_years(years, cfg.perpetual_threshold),
        level=level,
        color=CELL_COLORS[level],
    )
