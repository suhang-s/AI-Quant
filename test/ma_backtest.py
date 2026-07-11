#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
双均线交叉策略回测工具 (可复用)
================================
用法:
  # 基本用法 (默认 MA5/MA15, 10万资金)
  python ma_backtest.py --csv data/603259_SH_daily.csv

  # 自定义均线周期和资金
  python ma_backtest.py --csv data/002594_SZ_daily.csv --short 10 --long 30 --capital 500000

  # 指定输出目录和股票名称
  python ma_backtest.py --csv data/600900_SH_daily.csv --name "长江电力" --outdir G:/learn/test

参数说明:
  --csv       CSV文件路径 (需含 trade_date, close_qfq, vol, amount 列)
  --short     短均线周期 (默认 5)
  --long      长均线周期 (默认 15)
  --capital   初始资金 (默认 100000)
  --fee       手续费率 (默认 0.0008)
  --tax       印花税率 (默认 0.0005)
  --position  仓位比例 (默认 0.95)
  --name      股票名称 (默认从文件名推断)
  --outdir    输出目录 (默认 CSV同级的上级目录)
"""

import csv, os, json, argparse, re, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

# ── 全局配置 ──
SIMSUN = 'C:/Windows/Fonts/simsun.ttc'
mpl_font = FontProperties(fname=SIMSUN)
plt.rcParams['axes.unicode_minus'] = False

COLOR_UP   = '#e74c3c'   # 涨-红
COLOR_DOWN = '#27ae60'   # 跌-绿
COLOR_MA_S = '#e67e22'   # 短均线-橙
COLOR_MA_L = '#2980b9'   # 长均线-蓝


def load_data(path):
    """加载前复权 CSV 数据"""
    dates, close, vol, amount = [], [], [], []
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dates.append(row['trade_date'])
            close.append(float(row['close_qfq']))
            vol.append(float(row['vol']))
            amount.append(float(row['amount']))
    return dates, np.array(close), np.array(vol), np.array(amount)


def calc_sma(arr, period):
    """简单移动平均"""
    out = np.full_like(arr, np.nan, dtype=float)
    for i in range(period - 1, len(arr)):
        out[i] = np.mean(arr[i - period + 1: i + 1])
    return out


def generate_signals(close, ma_short, ma_long, long_period):
    """生成金叉/死叉交易信号"""
    n = len(close)
    signals = []
    position = False
    for i in range(long_period, n):
        if np.isnan(ma_short[i]) or np.isnan(ma_long[i]):
            continue
        prev_diff = ma_short[i-1] - ma_long[i-1]
        curr_diff = ma_short[i] - ma_long[i]
        if prev_diff <= 0 and curr_diff > 0 and not position:
            signals.append((i, 'buy', close[i]))
            position = True
        elif prev_diff >= 0 and curr_diff < 0 and position:
            signals.append((i, 'sell', close[i]))
            position = False
    if position:
        signals.append((n - 1, 'sell', close[-1]))
    return signals


def run_backtest(close, dates, signals, capital, fee_rate, stamp_tax, position_size):
    """执行回测模拟"""
    n = len(close)
    cap = capital
    shares = 0
    entry_price = 0
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
                cost = s * close[i] * (1 + fee_rate)
                cap -= cost
                shares = s
                entry_price = close[i]
                entry_idx = i
            elif sig == 'sell':
                revenue = shares * close[i] * (1 - fee_rate - stamp_tax)
                cap += revenue
                pnl = revenue - shares * entry_price * (1 + fee_rate)
                pnl_pct = pnl / (shares * entry_price * (1 + fee_rate)) * 100
                trade_records.append({
                    'buy_date': dates[entry_idx], 'buy_price': round(entry_price, 2),
                    'sell_date': dates[i], 'sell_price': round(close[i], 2),
                    'hold_days': i - entry_idx,
                    'pnl': round(pnl, 2), 'pnl_pct': round(pnl_pct, 2),
                    'win': 1 if pnl > 0 else 0
                })
                shares = 0
    return np.array(daily_values), trade_records


def calc_metrics(daily_values, trade_records, close, n, initial_capital):
    """计算回测量化指标"""
    final_value = daily_values[-1]
    total_return = (final_value - initial_capital) / initial_capital * 100
    annual_return = ((final_value / initial_capital) ** (252 / n) - 1) * 100
    daily_returns = np.diff(daily_values) / daily_values[:-1]
    rf_daily = 0.03 / 252
    excess = daily_returns - rf_daily
    sharpe = np.mean(excess) / np.std(excess) * np.sqrt(252) if np.std(excess) > 0 else 0
    peak = np.maximum.accumulate(daily_values)
    drawdown = (daily_values - peak) / peak
    max_dd = np.min(drawdown) * 100
    max_dd_idx = int(np.argmin(drawdown))
    peak_idx = int(np.argmax(daily_values[:max_dd_idx + 1])) if max_dd_idx > 0 else 0
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
    bh_return = (close[-1] - close[0]) / close[0] * 100
    return {
        'final_value': round(final_value, 2),
        'total_return_pct': round(total_return, 2),
        'annual_return_pct': round(annual_return, 2),
        'buy_hold_return_pct': round(bh_return, 2),
        'excess_return_pct': round(total_return - bh_return, 2),
        'sharpe_ratio': round(sharpe, 2),
        'max_drawdown_pct': round(max_dd, 2),
        'max_dd_peak_date': dates_of(peak_idx),
        'max_dd_trough_date': dates_of(max_dd_idx),
        'n_trades': n_trades, 'n_wins': n_wins, 'n_losses': n_losses,
        'win_rate_pct': round(win_rate, 1),
        'avg_hold_days': round(avg_hold, 0),
        'avg_win_pct': round(avg_win, 2),
        'avg_loss_pct': round(avg_loss, 2),
        'profit_factor': round(profit_factor, 2),
        'drawdown': drawdown,
        'daily_values': daily_values,
        'bh_value': round(initial_capital * close[-1] / close[0], 2),
    }


# 辅助：存储 dates 引用供 calc_metrics 内部用
_dates_ref = []
def dates_of(idx):
    return _dates_ref[idx] if idx < len(_dates_ref) else ''


def plot_strategy(dates, close, ma_short, ma_long, signals, short_p, long_p, name, code, chart_dir):
    """绘制策略信号图"""
    n = len(close)
    x = list(range(n))
    xticks_idx = list(range(0, n, max(1, n // 12)))
    xticks_labels = [dates[i] for i in xticks_idx]
    fig, ax = plt.subplots(figsize=(16, 8))
    ax.plot(x, close, color='#2c3e50', linewidth=1.2, label='收盘价(前复权)', zorder=2)
    ax.plot(x, ma_short, color=COLOR_MA_S, linewidth=1.2, label=f'MA{short_p}(短均线)', zorder=3)
    ax.plot(x, ma_long, color=COLOR_MA_L, linewidth=1.2, label=f'MA{long_p}(长均线)', zorder=3)
    buy_idx = [s[0] for s in signals if s[1] == 'buy']
    buy_price = [s[2] for s in signals if s[1] == 'buy']
    sell_idx = [s[0] for s in signals if s[1] == 'sell']
    sell_price = [s[2] for s in signals if s[1] == 'sell']
    if buy_idx:
        ax.scatter(buy_idx, buy_price, color=COLOR_UP, marker='^', s=120, zorder=5,
                   label=f'买入信号({len(buy_idx)}次)', edgecolors='white', linewidths=0.5)
    if sell_idx:
        ax.scatter(sell_idx, sell_price, color=COLOR_DOWN, marker='v', s=120, zorder=5,
                   label=f'卖出信号({len(sell_idx)}次)', edgecolors='white', linewidths=0.5)
    for idx, sig_type, _ in signals:
        color = COLOR_UP if sig_type == 'buy' else COLOR_DOWN
        ax.axvline(x=idx, color=color, alpha=0.15, linewidth=0.8)
    for idx, sig_type, price in signals:
        label = '买' if sig_type == 'buy' else '卖'
        offset = price * 0.03 if sig_type == 'buy' else -price * 0.03
        ax.annotate(label, xy=(idx, price), xytext=(idx, price + offset),
                    fontproperties=mpl_font, fontsize=9, ha='center',
                    color=COLOR_UP if sig_type == 'buy' else COLOR_DOWN, fontweight='bold')
    ax.set_title(f'{name}({code}) 双均线交叉策略 (MA{short_p}/MA{long_p})',
                 fontproperties=mpl_font, fontsize=15)
    ax.set_ylabel('价格(元)', fontproperties=mpl_font, fontsize=12)
    ax.set_xlabel('交易日期', fontproperties=mpl_font, fontsize=12)
    ax.legend(prop=mpl_font, fontsize=10, loc='upper left')
    ax.set_xticks(xticks_idx)
    ax.set_xticklabels(xticks_labels, rotation=45, ha='right')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(chart_dir, f'{code}_ma_strategy.png')
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
    ax1.plot(x, daily_values, color='#2c3e50', linewidth=1.2, label='策略净值')
    ax1.plot(x, np.full(n, initial_capital), color='gray', linewidth=0.8, linestyle='--', label='初始资金')
    bh_curve = initial_capital * close / close[0]
    ax1.plot(x, bh_curve, color='#f39c12', linewidth=1, linestyle=':', label='买入持有')
    ax1.set_title(f'{name}({code}) 双均线策略净值曲线 vs 买入持有', fontproperties=mpl_font, fontsize=14)
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
    path = os.path.join(chart_dir, f'{code}_nav_drawdown.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return path


def infer_code_name(csv_path, name_override=None):
    """从文件名推断股票代码和名称"""
    fname = os.path.basename(csv_path)
    # 匹配 688981_SH_daily.csv 格式
    m = re.match(r'(\d{6})_([A-Z]{2})_', fname)
    if m:
        code = f'{m.group(1)}.{m.group(2)}'
        file_code = f'{m.group(1)}_{m.group(2)}'
    else:
        code = 'UNKNOWN'
        file_code = 'UNKNOWN'
    name = name_override if name_override else f'股票{code}'
    return code, file_code, name


def run(csv_path, short_period=5, long_period=15, initial_capital=100000,
        fee_rate=0.0008, stamp_tax=0.0005, position_size=0.95,
        name=None, outdir=None):
    """
    主入口：执行完整回测流程
    返回结果字典
    """
    global _dates_ref

    # 推断信息
    code, file_code, stock_name = infer_code_name(csv_path, name)
    if outdir is None:
        outdir = os.path.dirname(os.path.dirname(csv_path))
    chart_dir = os.path.join(outdir, 'charts')
    os.makedirs(chart_dir, exist_ok=True)

    # 1. 加载数据
    dates, close, vol, amount = load_data(csv_path)
    n = len(close)
    _dates_ref = dates

    # 2. 计算均线
    ma_short = calc_sma(close, short_period)
    ma_long = calc_sma(close, long_period)

    # 3. 生成信号
    signals = generate_signals(close, ma_short, ma_long, long_period)

    # 4. 回测
    daily_values, trade_records = run_backtest(
        close, dates, signals, initial_capital, fee_rate, stamp_tax, position_size)

    # 5. 计算指标
    metrics = calc_metrics(daily_values, trade_records, close, n, initial_capital)

    # 6. 绘图
    strategy_chart = plot_strategy(
        dates, close, ma_short, ma_long, signals, short_period, long_period,
        stock_name, file_code, chart_dir)
    nav_chart = plot_nav(
        dates, daily_values, metrics['drawdown'], close, initial_capital,
        stock_name, file_code, chart_dir)

    # 7. 保存 JSON
    result = {
        'stock': f'{stock_name}({code})',
        'strategy': f'双均线交叉 MA{short_period}/MA{long_period}',
        'period': f'{dates[0]} ~ {dates[-1]}',
        'trading_days': n,
        'initial_capital': initial_capital,
        'final_value': metrics['final_value'],
        'total_return_pct': metrics['total_return_pct'],
        'annual_return_pct': metrics['annual_return_pct'],
        'buy_hold_return_pct': metrics['buy_hold_return_pct'],
        'excess_return_pct': metrics['excess_return_pct'],
        'sharpe_ratio': metrics['sharpe_ratio'],
        'max_drawdown_pct': metrics['max_drawdown_pct'],
        'n_trades': metrics['n_trades'],
        'n_wins': metrics['n_wins'],
        'n_losses': metrics['n_losses'],
        'win_rate_pct': metrics['win_rate_pct'],
        'avg_hold_days': metrics['avg_hold_days'],
        'avg_win_pct': metrics['avg_win_pct'],
        'avg_loss_pct': metrics['avg_loss_pct'],
        'profit_factor': metrics['profit_factor'],
        'trades': trade_records,
        'charts': {'strategy': strategy_chart, 'nav_drawdown': nav_chart},
    }
    json_path = os.path.join(outdir, f'{file_code}_backtest_result.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result, json_path, strategy_chart, nav_chart


def print_report(result):
    """打印回测报告"""
    print('=' * 60)
    print(f'  双均线交叉策略回测报告 — {result["stock"]}')
    print(f'  策略参数: {result["strategy"]}')
    print(f'  回测区间: {result["period"]} ({result["trading_days"]} 个交易日)')
    print('=' * 60)
    print(f'\n【收益指标】')
    print(f'  初始资金:       ¥{result["initial_capital"]:,.0f}')
    print(f'  最终净值:       ¥{result["final_value"]:,.2f}')
    print(f'  策略总收益:     {result["total_return_pct"]:+.2f}%')
    print(f'  年化收益率:     {result["annual_return_pct"]:+.2f}%')
    print(f'  买入持有收益:   {result["buy_hold_return_pct"]:+.2f}%')
    print(f'  超额收益:       {result["excess_return_pct"]:+.2f}%')
    print(f'\n【风险指标】')
    print(f'  夏普比率:       {result["sharpe_ratio"]:.2f}')
    print(f'  最大回撤:       {result["max_drawdown_pct"]:.2f}%')
    print(f'\n【交易统计】')
    print(f'  总交易次数:     {result["n_trades"]}')
    print(f'  胜率:           {result["win_rate_pct"]:.1f}%')
    print(f'  平均持仓天数:   {result["avg_hold_days"]:.0f}')
    print(f'  盈亏比:         {result["profit_factor"]:.2f}')
    print(f'\n【产出文件】')
    print(f'  策略图: {result["charts"]["strategy"]}')
    print(f'  净值图: {result["charts"]["nav_drawdown"]}')


def main():
    parser = argparse.ArgumentParser(description='双均线交叉策略回测工具')
    parser.add_argument('--csv', required=True, help='CSV文件路径')
    parser.add_argument('--short', type=int, default=5, help='短均线周期 (默认5)')
    parser.add_argument('--long', type=int, default=15, help='长均线周期 (默认15)')
    parser.add_argument('--capital', type=float, default=100000, help='初始资金 (默认100000)')
    parser.add_argument('--fee', type=float, default=0.0008, help='手续费率 (默认0.0008)')
    parser.add_argument('--tax', type=float, default=0.0005, help='印花税率 (默认0.0005)')
    parser.add_argument('--position', type=float, default=0.95, help='仓位比例 (默认0.95)')
    parser.add_argument('--name', default=None, help='股票名称 (默认从文件名推断)')
    parser.add_argument('--outdir', default=None, help='输出目录 (默认CSV上级目录)')
    args = parser.parse_args()

    result, json_path, _, _ = run(
        csv_path=args.csv,
        short_period=args.short,
        long_period=args.long,
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
