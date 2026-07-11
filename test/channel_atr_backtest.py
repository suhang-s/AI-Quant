#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高低价格通道 + ATR 策略回测工具 (可复用)
========================================
策略逻辑:
  - 计算Donchian通道: 上轨=N日最高价, 下轨=N日最低价, 中轨=(上+下)/2
  - 计算ATR: M日True Range均值, 用于动态止损
  - 买入信号: 收盘价突破上轨 (close > upper_channel_prev)
  - 卖出信号: 收盘价跌破下轨 (close < lower_channel_prev)
              或 ATR止损 (close < entry_price - atr_mult * ATR)

用法:
  # 基本用法 (默认 20日通道, 14日ATR, 2倍ATR止损, 10万资金)
  python channel_atr_backtest.py --csv data/603259_SH_daily.csv

  # 自定义通道周期和ATR参数
  python channel_atr_backtest.py --csv data/002594_SZ_daily.csv --channel 10 --atr 14 --atr-mult 2.0 --capital 500000

  # 指定输出目录和股票名称
  python channel_atr_backtest.py --csv data/600900_SH_daily.csv --name "长江电力" --outdir G:/learn/test

参数说明:
  --csv        CSV文件路径 (需含 trade_date, open_qfq, high_qfq, low_qfq, close_qfq 列)
  --channel    通道周期 (默认 20)
  --atr        ATR周期 (默认 14)
  --atr-mult   ATR止损倍数 (默认 2.0)
  --capital    初始资金 (默认 100000)
  --fee        手续费率 (默认 0.0008)
  --tax        印花税率 (默认 0.0005)
  --position   仓位比例 (默认 0.95)
  --name       股票名称 (默认从文件名推断)
  --outdir     输出目录 (默认CSV同级的上级目录)
"""

import csv, os, json, argparse, re, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Patch

# ── 全局配置 ──
SIMSUN = 'C:/Windows/Fonts/simsun.ttc'
mpl_font = FontProperties(fname=SIMSUN)
plt.rcParams['axes.unicode_minus'] = False

COLOR_UP     = '#e74c3c'   # 涨-红
COLOR_DOWN   = '#27ae60'   # 跌-绿
COLOR_UPPER  = '#c0392b'   # 上轨-暗红
COLOR_LOWER  = '#27ae60'   # 下轨-绿
COLOR_MID    = '#7f8c8d'   # 中轨-灰
COLOR_ATR    = '#8e44ad'   # ATR-紫
COLOR_PRICE  = '#2c3e50'   # 收盘价-深蓝


def load_data(path):
    """加载前复权 CSV 数据，返回日期、OHLC、成交量、成交额"""
    dates, open_p, high, low, close = [], [], [], [], []
    vol, amount = [], []
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dates.append(row['trade_date'])
            open_p.append(float(row['open_qfq']))
            high.append(float(row['high_qfq']))
            low.append(float(row['low_qfq']))
            close.append(float(row['close_qfq']))
            vol.append(float(row['vol']))
            amount.append(float(row['amount']))
    return (dates, np.array(open_p), np.array(high),
            np.array(low), np.array(close),
            np.array(vol), np.array(amount))


def calc_donchian(high, low, period):
    """
    计算Donchian通道
    返回: upper(N日最高), lower(N日最低), mid(中轨)
    注意: 使用前N日数据(不含当日)，即 upper[i] = max(high[i-period:i])
    """
    n = len(high)
    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)
    mid = np.full(n, np.nan)
    for i in range(period, n):
        upper[i] = np.max(high[i - period:i])
        lower[i] = np.min(low[i - period:i])
        mid[i] = (upper[i] + lower[i]) / 2
    return upper, lower, mid


def calc_atr(high, low, close, period):
    """
    计算ATR (Average True Range)
    TR = max(high-low, |high-prev_close|, |low-prev_close|)
    ATR = SMA(TR, period)
    """
    n = len(high)
    tr = np.full(n, np.nan)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1])
        )
    atr = np.full(n, np.nan)
    for i in range(period - 1, n):
        atr[i] = np.mean(tr[i - period + 1: i + 1])
    return atr, tr


def generate_signals(close, upper, lower, atr, channel_period, atr_mult):
    """
    生成交易信号:
    - 买入: 收盘价突破上轨 (close[i] > upper[i])
    - 卖出: 收盘价跌破下轨 (close[i] < lower[i])
            或 ATR止损 (close[i] < entry_price - atr_mult * atr[i])
    """
    n = len(close)
    signals = []
    position = False
    entry_price = 0.0

    for i in range(channel_period, n):
        if np.isnan(upper[i]) or np.isnan(atr[i]):
            continue

        if not position:
            # 买入: 突破上轨
            if close[i] > upper[i]:
                signals.append((i, 'buy', close[i]))
                position = True
                entry_price = close[i]
        else:
            # 卖出条件1: 跌破下轨
            sell_signal = False
            if close[i] < lower[i]:
                sell_signal = True
            # 卖出条件2: ATR止损
            stop_price = entry_price - atr_mult * atr[i]
            if close[i] < stop_price:
                sell_signal = True

            if sell_signal:
                signals.append((i, 'sell', close[i]))
                position = False
                entry_price = 0.0

    # 如果最后还持仓, 在最后一天卖出
    if position:
        signals.append((n - 1, 'sell', close[-1]))

    return signals


def run_backtest(close, dates, signals, capital, fee_rate, stamp_tax, position_size):
    """执行回测模拟"""
    n = len(close)
    cap = capital
    shares = 0
    entry_price = 0.0
    entry_idx = 0
    trade_records = []
    daily_values = []
    signal_dict = {s[0]: s[1] for s in signals}

    for i in range(n):
        daily_value = cap + shares * close[i] if shares > 0 else cap
        daily_values.append(daily_value)
        if i in signal_dict:
            sig = signal_dict[i]
            if sig == 'buy':
                buy_amount = cap * position_size
                s = int(buy_amount / close[i] / 100) * 100
                if s == 0:
                    s = int(buy_amount / close[i])
                if s > 0:
                    cost = s * close[i] * (1 + fee_rate)
                    cap -= cost
                    shares = s
                    entry_price = close[i]
                    entry_idx = i
            elif sig == 'sell':
                revenue = shares * close[i] * (1 - fee_rate - stamp_tax)
                cap += revenue
                cost_basis = shares * entry_price * (1 + fee_rate)
                pnl = revenue - cost_basis
                pnl_pct = pnl / cost_basis * 100 if cost_basis > 0 else 0
                trade_records.append({
                    'buy_date': dates[entry_idx], 'buy_price': round(entry_price, 2),
                    'sell_date': dates[i], 'sell_price': round(close[i], 2),
                    'hold_days': i - entry_idx,
                    'pnl': round(pnl, 2), 'pnl_pct': round(pnl_pct, 2),
                    'win': 1 if pnl > 0 else 0
                })
                shares = 0
    return np.array(daily_values), trade_records


_dates_ref = []

def calc_metrics(daily_values, trade_records, close, n, initial_capital):
    """计算回测量化指标 (私募行业标准)"""
    final_value = daily_values[-1]
    total_return = (final_value - initial_capital) / initial_capital * 100
    annual_return = ((final_value / initial_capital) ** (252 / n) - 1) * 100

    daily_returns = np.diff(daily_values) / daily_values[:-1]
    rf_daily = 0.03 / 252
    excess = daily_returns - rf_daily

    # 夏普比率
    sharpe = np.mean(excess) / np.std(excess) * np.sqrt(252) if np.std(excess) > 0 else 0

    # 年化波动率
    volatility = np.std(daily_returns) * np.sqrt(252) * 100

    # 索提诺比率 (仅下行波动)
    downside = excess[excess < 0]
    downside_dev = np.sqrt(np.mean(downside ** 2)) * np.sqrt(252) if len(downside) > 0 else 0
    sortino = np.mean(excess) * 252 / downside_dev if downside_dev > 0 else 0

    # 最大回撤
    peak = np.maximum.accumulate(daily_values)
    drawdown = (daily_values - peak) / peak
    max_dd = np.min(drawdown) * 100
    max_dd_idx = int(np.argmin(drawdown))
    peak_idx = int(np.argmax(daily_values[:max_dd_idx + 1])) if max_dd_idx > 0 else 0

    # 卡玛比率
    calmar = annual_return / (-max_dd) if max_dd != 0 else 0

    # 买入持有
    bh_return = (close[-1] - close[0]) / close[0] * 100
    bh_values = initial_capital * close / close[0]

    # Alpha & Beta
    bh_returns = np.diff(bh_values) / bh_values[:-1]
    mean_dr = np.mean(daily_returns)
    mean_bh = np.mean(bh_returns)
    cov_xy = np.mean((daily_returns - mean_dr) * (bh_returns - mean_bh))
    var_y = np.var(bh_returns)
    beta = cov_xy / var_y if var_y > 0 else 0
    alpha = annual_return - (3 + beta * (bh_return - 0))

    # 信息比率
    tracking_err = np.sqrt(np.mean((daily_returns - bh_returns) ** 2)) * np.sqrt(252)
    info_ratio = (annual_return - bh_return) / tracking_err if tracking_err > 0 else 0

    # 交易统计
    n_trades = len(trade_records)
    n_wins = sum(t['win'] for t in trade_records)
    n_losses = n_trades - n_wins
    win_rate = n_wins / n_trades * 100 if n_trades > 0 else 0
    avg_hold = np.mean([t['hold_days'] for t in trade_records]) if trade_records else 0
    avg_win = np.mean([t['pnl_pct'] for t in trade_records if t['win']]) if n_wins > 0 else 0
    avg_loss = np.mean([t['pnl_pct'] for t in trade_records if not t['win']]) if n_losses > 0 else 0
    total_profit = sum(t['pnl'] for t in trade_records if t['win'])
    total_loss = abs(sum(t['pnl'] for t in trade_records if not t['win']))
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

    max_win = max([t['pnl_pct'] for t in trade_records], default=0)
    max_loss_pct = min([t['pnl_pct'] for t in trade_records], default=0)

    # 最大连续亏损
    max_consec_loss = 0
    current_consec = 0
    for t in trade_records:
        if not t['win']:
            current_consec += 1
            max_consec_loss = max(max_consec_loss, current_consec)
        else:
            current_consec = 0

    return {
        'final_value': round(final_value, 2),
        'total_return_pct': round(total_return, 2),
        'annual_return_pct': round(annual_return, 2),
        'buy_hold_return_pct': round(bh_return, 2),
        'excess_return_pct': round(total_return - bh_return, 2),
        'sharpe_ratio': round(sharpe, 2),
        'sortino_ratio': round(sortino, 2),
        'max_drawdown_pct': round(max_dd, 2),
        'max_dd_peak_date': _dates_ref[peak_idx] if peak_idx < len(_dates_ref) else '',
        'max_dd_trough_date': _dates_ref[max_dd_idx] if max_dd_idx < len(_dates_ref) else '',
        'calmar_ratio': round(calmar, 2),
        'volatility_pct': round(volatility, 2),
        'alpha': round(alpha, 2),
        'beta': round(beta, 2),
        'info_ratio': round(info_ratio, 2),
        'n_trades': n_trades, 'n_wins': n_wins, 'n_losses': n_losses,
        'win_rate_pct': round(win_rate, 1),
        'avg_hold_days': round(avg_hold, 0),
        'avg_win_pct': round(avg_win, 2),
        'avg_loss_pct': round(avg_loss, 2),
        'profit_factor': round(profit_factor, 2),
        'max_win_pct': round(max_win, 2),
        'max_loss_pct': round(max_loss_pct, 2),
        'max_consec_loss': max_consec_loss,
        'drawdown': drawdown,
        'daily_values': daily_values,
        'bh_value': round(initial_capital * close[-1] / close[0], 2),
    }


def plot_strategy(dates, close, upper, lower, mid, atr, signals,
                  channel_p, atr_p, atr_mult, name, code, chart_dir):
    """绘制策略信号图: 股价+通道+ATR+买卖信号"""
    n = len(close)
    x = list(range(n))
    xticks_idx = list(range(0, n, max(1, n // 12)))
    xticks_labels = [dates[i] for i in xticks_idx]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10),
                                    gridspec_kw={'height_ratios': [3, 1]})

    # 上图: 价格 + 通道 + 信号
    ax1.plot(x, close, color=COLOR_PRICE, linewidth=1.2, label='收盘价(前复权)', zorder=2)
    ax1.plot(x, upper, color=COLOR_UPPER, linewidth=1, linestyle='--',
             label=f'上轨({channel_p}日最高)', zorder=3, alpha=0.8)
    ax1.plot(x, lower, color=COLOR_LOWER, linewidth=1, linestyle='--',
             label=f'下轨({channel_p}日最低)', zorder=3, alpha=0.8)
    ax1.plot(x, mid, color=COLOR_MID, linewidth=0.8, linestyle=':',
             label=f'中轨', zorder=3, alpha=0.6)
    ax1.fill_between(x, lower, upper, alpha=0.06, color='#8e44ad')

    # 买卖信号
    buy_idx = [s[0] for s in signals if s[1] == 'buy']
    buy_price = [s[2] for s in signals if s[1] == 'buy']
    sell_idx = [s[0] for s in signals if s[1] == 'sell']
    sell_price = [s[2] for s in signals if s[1] == 'sell']

    if buy_idx:
        ax1.scatter(buy_idx, buy_price, color=COLOR_UP, marker='^', s=120, zorder=5,
                    label=f'买入信号({len(buy_idx)}次)', edgecolors='white', linewidths=0.5)
    if sell_idx:
        ax1.scatter(sell_idx, sell_price, color=COLOR_DOWN, marker='v', s=120, zorder=5,
                    label=f'卖出信号({len(sell_idx)}次)', edgecolors='white', linewidths=0.5)

    for idx, sig_type, price in signals:
        label = '买' if sig_type == 'buy' else '卖'
        offset = price * 0.03 if sig_type == 'buy' else -price * 0.03
        ax1.annotate(label, xy=(idx, price), xytext=(idx, price + offset),
                     fontproperties=mpl_font, fontsize=9, ha='center',
                     color=COLOR_UP if sig_type == 'buy' else COLOR_DOWN, fontweight='bold')

    ax1.set_title(f'{name}({code}) 高低价格通道+ATR策略 (通道{channel_p}日, ATR{atr_p}日, 止损{atr_mult}倍ATR)',
                  fontproperties=mpl_font, fontsize=14)
    ax1.set_ylabel('价格(元)', fontproperties=mpl_font, fontsize=12)
    ax1.legend(prop=mpl_font, fontsize=9, loc='upper left')
    ax1.set_xticks(xticks_idx)
    ax1.set_xticklabels(xticks_labels, rotation=45, ha='right')
    ax1.grid(True, alpha=0.3)

    # 下图: ATR
    ax2.plot(x, atr, color=COLOR_ATR, linewidth=1, label=f'ATR({atr_p}日)')
    ax2.fill_between(x, atr, 0, alpha=0.1, color=COLOR_ATR)
    ax2.set_title(f'ATR (Average True Range, {atr_p}日) — 波动率指标',
                  fontproperties=mpl_font, fontsize=12)
    ax2.set_ylabel('ATR', fontproperties=mpl_font, fontsize=11)
    ax2.set_xlabel('交易日期', fontproperties=mpl_font, fontsize=12)
    ax2.legend(prop=mpl_font, fontsize=10)
    ax2.set_xticks(xticks_idx)
    ax2.set_xticklabels(xticks_labels, rotation=45, ha='right')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(chart_dir, f'{code}_channel_atr_strategy.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return path


def plot_nav(dates, daily_values, drawdown, close, initial_capital, name, code, chart_dir):
    """绘制净值+回撤图"""
    n = len(close)
    x = list(range(n))
    xticks_idx = list(range(0, n, max(1, n // 12)))
    xticks_labels = [dates[i] for i in xticks_idx]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [3, 1]})

    ax1.plot(x, daily_values, color='#1a237e', linewidth=1.2, label='策略净值')
    ax1.plot(x, np.full(n, initial_capital), color='gray', linewidth=0.8,
             linestyle='--', label='初始资金')
    bh_curve = initial_capital * close / close[0]
    ax1.plot(x, bh_curve, color='#f39c12', linewidth=1, linestyle=':', label='买入持有')

    ax1.set_title(f'{name}({code}) 通道+ATR策略净值曲线 vs 买入持有',
                  fontproperties=mpl_font, fontsize=14)
    ax1.set_ylabel('净值(元)', fontproperties=mpl_font)
    ax1.legend(prop=mpl_font, fontsize=10)
    ax1.grid(True, alpha=0.3)

    ax2.fill_between(x, drawdown * 100, 0, color=COLOR_DOWN, alpha=0.3)
    ax2.plot(x, drawdown * 100, color=COLOR_DOWN, linewidth=0.8)
    ax2.set_title('回撤曲线', fontproperties=mpl_font, fontsize=12)
    ax2.set_ylabel('回撤(%)', fontproperties=mpl_font)
    ax2.set_xlabel('交易日期', fontproperties=mpl_font)
    ax2.grid(True, alpha=0.3)

    for ax in [ax1, ax2]:
        ax.set_xticks(xticks_idx)
        ax.set_xticklabels(xticks_labels, rotation=45, ha='right')

    plt.tight_layout()
    path = os.path.join(chart_dir, f'{code}_channel_atr_nav.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return path


def infer_code_name(csv_path, name_override=None):
    """从文件名推断股票代码和名称"""
    fname = os.path.basename(csv_path)
    m = re.match(r'(\d{6})_([A-Z]{2})_', fname)
    if m:
        code = f'{m.group(1)}.{m.group(2)}'
        file_code = f'{m.group(1)}_{m.group(2)}'
    else:
        code = 'UNKNOWN'
        file_code = 'UNKNOWN'
    name = name_override if name_override else f'股票{code}'
    return code, file_code, name


def run(csv_path, channel_period=20, atr_period=14, atr_mult=2.0,
        initial_capital=100000, fee_rate=0.0008, stamp_tax=0.0005,
        position_size=0.95, name=None, outdir=None):
    """
    主入口：执行完整回测流程
    返回 (result_dict, json_path, strategy_chart, nav_chart)
    """
    global _dates_ref

    code, file_code, stock_name = infer_code_name(csv_path, name)
    if outdir is None:
        outdir = os.path.dirname(os.path.dirname(csv_path))
    chart_dir = os.path.join(outdir, 'charts')
    os.makedirs(chart_dir, exist_ok=True)

    # 1. 加载数据
    dates, open_p, high, low, close, vol, amount = load_data(csv_path)
    n = len(close)
    _dates_ref = dates

    # 2. 计算Donchian通道
    upper, lower, mid = calc_donchian(high, low, channel_period)

    # 3. 计算ATR
    atr, tr = calc_atr(high, low, close, atr_period)

    # 4. 生成交易信号
    signals = generate_signals(close, upper, lower, atr, channel_period, atr_mult)

    # 5. 回测模拟
    daily_values, trade_records = run_backtest(
        close, dates, signals, initial_capital, fee_rate, stamp_tax, position_size)

    # 6. 计算指标
    metrics = calc_metrics(daily_values, trade_records, close, n, initial_capital)

    # 7. 绘图
    strategy_chart = plot_strategy(
        dates, close, upper, lower, mid, atr, signals,
        channel_period, atr_period, atr_mult, stock_name, file_code, chart_dir)
    nav_chart = plot_nav(
        dates, daily_values, metrics['drawdown'], close, initial_capital,
        stock_name, file_code, chart_dir)

    # 8. 保存JSON
    result = {
        'stock': f'{stock_name}({code})',
        'strategy': f'高低通道({channel_period}日) + ATR({atr_period}日, {atr_mult}倍止损)',
        'period': f'{dates[0]} ~ {dates[-1]}',
        'trading_days': n,
        'initial_capital': initial_capital,
        'final_value': metrics['final_value'],
        'total_return_pct': metrics['total_return_pct'],
        'annual_return_pct': metrics['annual_return_pct'],
        'buy_hold_return_pct': metrics['buy_hold_return_pct'],
        'excess_return_pct': metrics['excess_return_pct'],
        'sharpe_ratio': metrics['sharpe_ratio'],
        'sortino_ratio': metrics['sortino_ratio'],
        'max_drawdown_pct': metrics['max_drawdown_pct'],
        'calmar_ratio': metrics['calmar_ratio'],
        'volatility_pct': metrics['volatility_pct'],
        'alpha': metrics['alpha'],
        'beta': metrics['beta'],
        'info_ratio': metrics['info_ratio'],
        'n_trades': metrics['n_trades'],
        'n_wins': metrics['n_wins'],
        'n_losses': metrics['n_losses'],
        'win_rate_pct': metrics['win_rate_pct'],
        'avg_hold_days': metrics['avg_hold_days'],
        'avg_win_pct': metrics['avg_win_pct'],
        'avg_loss_pct': metrics['avg_loss_pct'],
        'profit_factor': metrics['profit_factor'],
        'max_win_pct': metrics['max_win_pct'],
        'max_loss_pct': metrics['max_loss_pct'],
        'max_consec_loss': metrics['max_consec_loss'],
        'trades': trade_records,
        'charts': {'strategy': strategy_chart, 'nav_drawdown': nav_chart},
    }
    json_path = os.path.join(outdir, f'{file_code}_channel_atr_result.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result, json_path, strategy_chart, nav_chart


def print_report(result):
    """打印回测报告"""
    print('=' * 65)
    print(f'  高低价格通道+ATR策略回测报告 — {result["stock"]}')
    print(f'  策略参数: {result["strategy"]}')
    print(f'  回测区间: {result["period"]} ({result["trading_days"]} 个交易日)')
    print('=' * 65)
    print(f'\n【收益指标】')
    print(f'  初始资金:       ¥{result["initial_capital"]:,.0f}')
    print(f'  最终净值:       ¥{result["final_value"]:,.2f}')
    print(f'  策略总收益:     {result["total_return_pct"]:+.2f}%')
    print(f'  年化收益率:     {result["annual_return_pct"]:+.2f}%')
    print(f'  买入持有收益:   {result["buy_hold_return_pct"]:+.2f}%')
    print(f'  超额收益:       {result["excess_return_pct"]:+.2f}%')
    print(f'  Alpha:          {result["alpha"]:+.2f}%')
    print(f'  Beta:           {result["beta"]:.2f}')
    print(f'  信息比率:       {result["info_ratio"]:.2f}')
    print(f'\n【风险指标】')
    print(f'  夏普比率:       {result["sharpe_ratio"]:.2f}')
    print(f'  索提诺比率:     {result["sortino_ratio"]:.2f}')
    print(f'  卡玛比率:       {result["calmar_ratio"]:.2f}')
    print(f'  最大回撤:       {result["max_drawdown_pct"]:.2f}%')
    print(f'  年化波动率:     {result["volatility_pct"]:.2f}%')
    print(f'\n【交易统计】')
    print(f'  总交易次数:     {result["n_trades"]}')
    print(f'  胜率:           {result["win_rate_pct"]:.1f}%')
    print(f'  平均持仓天数:   {result["avg_hold_days"]:.0f}')
    print(f'  盈亏比:         {result["profit_factor"]:.2f}')
    print(f'  最大单笔盈利:   {result["max_win_pct"]:+.2f}%')
    print(f'  最大单笔亏损:   {result["max_loss_pct"]:+.2f}%')
    print(f'  最大连续亏损:   {result["max_consec_loss"]}笔')
    print(f'\n【产出文件】')
    print(f'  策略图: {result["charts"]["strategy"]}')
    print(f'  净值图: {result["charts"]["nav_drawdown"]}')


def main():
    parser = argparse.ArgumentParser(description='高低价格通道+ATR策略回测工具')
    parser.add_argument('--csv', required=True, help='CSV文件路径')
    parser.add_argument('--channel', type=int, default=20, help='通道周期 (默认20)')
    parser.add_argument('--atr', type=int, default=14, help='ATR周期 (默认14)')
    parser.add_argument('--atr-mult', type=float, default=2.0, dest='atr_mult',
                        help='ATR止损倍数 (默认2.0)')
    parser.add_argument('--capital', type=float, default=100000, help='初始资金 (默认100000)')
    parser.add_argument('--fee', type=float, default=0.0008, help='手续费率 (默认0.0008)')
    parser.add_argument('--tax', type=float, default=0.0005, help='印花税率 (默认0.0005)')
    parser.add_argument('--position', type=float, default=0.95, help='仓位比例 (默认0.95)')
    parser.add_argument('--name', default=None, help='股票名称 (默认从文件名推断)')
    parser.add_argument('--outdir', default=None, help='输出目录 (默认CSV上级目录)')
    args = parser.parse_args()

    result, json_path, _, _ = run(
        csv_path=args.csv,
        channel_period=args.channel,
        atr_period=args.atr,
        atr_mult=args.atr_mult,
        initial_capital=args.capital,
        fee_rate=args.fee,
        stamp_tax=args.tax,
        position_size=args.position,
        name=args.name,
        outdir=args.outdir,
    )
    result['json_path'] = json_path
    print_report(result)
    print(f'  JSON:  {json_path}')
    print('\n=== 回测完成 ===')


if __name__ == '__main__':
    main()
