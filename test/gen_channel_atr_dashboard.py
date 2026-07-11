#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成高低通道+ATR策略交互式看板HTML
从CSV文件中提取数据，嵌入到自包含HTML中
"""
import csv, json, os

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
OUTPUT = os.path.join(os.path.dirname(__file__), 'channel_atr_dashboard.html')

STOCKS = {
    '002594_SZ': {'name': '比亚迪', 'code': '002594.SZ', 'sector': '新能源汽车'},
    '300346_SZ': {'name': '南大光电', 'code': '300346.SZ', 'sector': '光电材料'},
    '600900_SH': {'name': '长江电力', 'code': '600900.SH', 'sector': '水电'},
    '603259_SH': {'name': '药明康德', 'code': '603259.SH', 'sector': '化学制药'},
    '688981_SH': {'name': '中芯国际', 'code': '688981.SH', 'sector': '半导体'},
}

def load_csv(path):
    """加载CSV，返回 [date, open, high, low, close, vol, amount] 列表"""
    rows = []
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = int(row['trade_date'])
            o = float(row['open_qfq'])
            h = float(row['high_qfq'])
            l = float(row['low_qfq'])
            c = float(row['close_qfq'])
            v = float(row['vol'])
            a = float(row['amount'])
            rows.append([d, round(o, 2), round(h, 2), round(l, 2), round(c, 2),
                         round(v, 2), round(a, 2)])
    return rows

# 收集数据
stocks_data = {}
for key, info in STOCKS.items():
    csv_path = os.path.join(DATA_DIR, f'{key}_daily.csv')
    if os.path.exists(csv_path):
        stocks_data[key] = {
            'name': info['name'],
            'code': info['code'],
            'sector': info['sector'],
            'data': load_csv(csv_path)
        }
        print(f"  {key}: {len(stocks_data[key]['data'])} rows")

data_json = json.dumps(stocks_data, ensure_ascii=False)

HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>高低价格通道+ATR策略回测看板</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; background: #f0f2f5; color: #2c3e50; }

.header {
    background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
    color: white; padding: 16px 24px;
    display: flex; align-items: center; justify-content: space-between;
}
.header h1 { font-size: 20px; font-weight: 600; }
.header .subtitle { font-size: 12px; opacity: 0.8; margin-top: 2px; }

.controls {
    background: white; margin: 12px; padding: 16px 20px; border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-end;
}
.ctrl-group { display: flex; flex-direction: column; gap: 4px; }
.ctrl-group label { font-size: 11px; color: #888; font-weight: 500; }
.ctrl-group select, .ctrl-group input {
    border: 1px solid #ddd; border-radius: 4px; padding: 6px 10px;
    font-size: 13px; outline: none; transition: border-color 0.2s;
    min-width: 80px;
}
.ctrl-group select:focus, .ctrl-group input:focus { border-color: #6c3082; }
.ctrl-group input[type="date"] { min-width: 130px; }

.btn-run {
    background: #6c3082; color: white; border: none; border-radius: 4px;
    padding: 8px 24px; font-size: 14px; cursor: pointer; font-weight: 500;
    transition: background 0.2s;
}
.btn-run:hover { background: #4a2058; }

.preset-row { display: flex; gap: 8px; align-items: center; }
.preset-btn {
    background: #f3e5f5; color: #6c3082; border: 1px solid #d1c4e9;
    border-radius: 4px; padding: 4px 10px; font-size: 11px; cursor: pointer;
    transition: all 0.2s;
}
.preset-btn:hover { background: #d1c4e9; }

/* 指标卡片 */
.metrics-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(145px, 1fr));
    gap: 10px; margin: 0 12px;
}
.metric-card {
    background: white; border-radius: 8px; padding: 14px 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    border-left: 3px solid #6c3082;
}
.metric-card .label { font-size: 11px; color: #888; margin-bottom: 4px; }
.metric-card .value { font-size: 20px; font-weight: 700; color: #2c3e50; }
.metric-card .value.pos { color: #e74c3c; }
.metric-card .value.neg { color: #27ae60; }
.metric-card .value.neutral { color: #2c3e50; }
.metric-card .sub { font-size: 10px; color: #aaa; margin-top: 2px; }
.metric-card.benchmark { border-left-color: #f39c12; }
.metric-card.benchmark .value { color: #f39c12; }

/* 图表容器 */
.charts-container { margin: 12px; display: flex; flex-direction: column; gap: 12px; }
.chart-box {
    background: white; border-radius: 8px; padding: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
.chart-box .chart-title {
    font-size: 14px; font-weight: 600; margin-bottom: 8px;
    display: flex; align-items: center; gap: 8px;
}
.chart-box .chart-title .badge {
    background: #f3e5f5; color: #6c3082; border-radius: 3px;
    padding: 2px 8px; font-size: 11px; font-weight: 500;
}
#chartNav { height: 380px; }
#chartDrawdown { height: 220px; }
#chartSignal { height: 500px; }
#chartATR { height: 200px; }

/* 交易明细表 */
.trades-box {
    background: white; border-radius: 8px; padding: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin: 0 12px 12px;
}
.trades-box .chart-title { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
.trades-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.trades-table th {
    background: #f5f6fa; padding: 8px 10px; text-align: left;
    font-weight: 600; color: #555; border-bottom: 2px solid #e0e0e0;
    white-space: nowrap;
}
.trades-table td {
    padding: 7px 10px; border-bottom: 1px solid #eee;
    white-space: nowrap;
}
.trades-table tr:hover td { background: #f9f9f9; }
.trades-table .win { color: #e74c3c; font-weight: 600; }
.trades-table .loss { color: #27ae60; font-weight: 600; }
.trades-table .tag {
    display: inline-block; padding: 1px 6px; border-radius: 3px;
    font-size: 10px; font-weight: 500;
}
.trades-table .tag.buy { background: #ffebee; color: #c62828; }
.trades-table .tag.sell { background: #e8f5e9; color: #2e7d32; }
.trades-table .tag.stop { background: #fff3e0; color: #e65100; }

.footer { text-align: center; padding: 16px; font-size: 11px; color: #aaa; }

/* 响应式 */
@media (max-width: 768px) {
    .controls { flex-direction: column; align-items: stretch; }
    .metrics-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
</head>
<body>

<div class="header">
    <div>
        <h1>高低价格通道 + ATR 策略回测看板</h1>
        <div class="subtitle">Donchian Channel + ATR Strategy Backtest Dashboard | 多股票 | 全参数可调 | 私募行业指标</div>
    </div>
    <div class="preset-row">
        <span style="color:rgba(255,255,255,0.6);font-size:11px;">快捷参数:</span>
        <button class="preset-btn" onclick="setPreset(10,14,1.5,100000,0.0008,0.0005,0.95)">短通道10/ATR1.5</button>
        <button class="preset-btn" onclick="setPreset(20,14,2.0,100000,0.0008,0.0005,0.95)">经典20/ATR2.0</button>
        <button class="preset-btn" onclick="setPreset(55,20,3.0,100000,0.0008,0.0005,0.95)">长通道55/ATR3.0</button>
    </div>
</div>

<div class="controls">
    <div class="ctrl-group">
        <label>股票</label>
        <select id="selStock" onchange="runBacktest()"></select>
    </div>
    <div class="ctrl-group">
        <label>通道周期</label>
        <input type="number" id="inpChannel" value="20" min="5" max="120" onchange="runBacktest()">
    </div>
    <div class="ctrl-group">
        <label>ATR周期</label>
        <input type="number" id="inpATR" value="14" min="5" max="60" onchange="runBacktest()">
    </div>
    <div class="ctrl-group">
        <label>ATR止损倍数</label>
        <input type="number" id="inpATRMult" value="2.0" min="0.5" max="5" step="0.5" onchange="runBacktest()">
    </div>
    <div class="ctrl-group">
        <label>初始资金 (元)</label>
        <input type="number" id="inpCapital" value="100000" min="10000" step="10000" onchange="runBacktest()">
    </div>
    <div class="ctrl-group">
        <label>手续费率</label>
        <input type="number" id="inpFee" value="0.0008" min="0" max="0.01" step="0.0001" onchange="runBacktest()">
    </div>
    <div class="ctrl-group">
        <label>印花税率</label>
        <input type="number" id="inpTax" value="0.0005" min="0" max="0.01" step="0.0001" onchange="runBacktest()">
    </div>
    <div class="ctrl-group">
        <label>仓位比例</label>
        <input type="number" id="inpPos" value="0.95" min="0.1" max="1" step="0.05" onchange="runBacktest()">
    </div>
    <div class="ctrl-group">
        <label>起始日期</label>
        <input type="date" id="inpStart" onchange="runBacktest()">
    </div>
    <div class="ctrl-group">
        <label>结束日期</label>
        <input type="date" id="inpEnd" onchange="runBacktest()">
    </div>
    <button class="btn-run" onclick="runBacktest()">运行回测</button>
</div>

<div class="metrics-grid" id="metricsGrid"></div>

<div class="charts-container">
    <div class="chart-box">
        <div class="chart-title"><span class="badge">图1</span>策略净值 vs 买入持有基准</div>
        <div id="chartNav"></div>
    </div>
    <div class="chart-box">
        <div class="chart-title"><span class="badge">图2</span>回撤曲线</div>
        <div id="chartDrawdown"></div>
    </div>
    <div class="chart-box">
        <div class="chart-title"><span class="badge">图3</span>价格走势 + 高低通道 + 买卖信号</div>
        <div id="chartSignal"></div>
    </div>
    <div class="chart-box">
        <div class="chart-title"><span class="badge">图4</span>ATR 波动率指标</div>
        <div id="chartATR"></div>
    </div>
</div>

<div class="trades-box">
    <div class="chart-title"><span class="badge">表1</span>交易明细</div>
    <div style="overflow-x:auto;">
        <table class="trades-table" id="tradesTable">
            <thead>
                <tr>
                    <th>#</th>
                    <th>买入日期</th>
                    <th>买入价</th>
                    <th>卖出日期</th>
                    <th>卖出价</th>
                    <th>持仓天数</th>
                    <th>盈亏(元)</th>
                    <th>盈亏(%)</th>
                    <th>卖出原因</th>
                    <th>结果</th>
                </tr>
            </thead>
            <tbody id="tradesBody"></tbody>
        </table>
    </div>
</div>

<div class="footer">
    数据来源: Tushare (前复权) | 回测引擎: 客户端实时计算 | 涨红跌绿(中国股市配色) | 无风险利率: 3%年化 | 策略: Donchian通道突破 + ATR动态止损
</div>

<script>
// ── 嵌入数据 ──
const STOCKS_DATA = ''' + data_json + ''';

// ── 全局状态 ──
let chartNav, chartDD, chartSig, chartATR;

// ── 初始化 ──
function init() {
    const sel = document.getElementById('selStock');
    for (const [key, val] of Object.entries(STOCKS_DATA)) {
        const opt = document.createElement('option');
        opt.value = key;
        opt.textContent = `${val.name} (${val.code}) - ${val.sector}`;
        sel.appendChild(opt);
    }

    const firstKey = Object.keys(STOCKS_DATA)[0];
    const firstData = STOCKS_DATA[firstKey].data;
    document.getElementById('inpStart').value = fmtDate(firstData[0][0]);
    document.getElementById('inpEnd').value = fmtDate(firstData[firstData.length - 1][0]);

    chartNav = echarts.init(document.getElementById('chartNav'));
    chartDD  = echarts.init(document.getElementById('chartDrawdown'));
    chartSig = echarts.init(document.getElementById('chartSignal'));
    chartATR = echarts.init(document.getElementById('chartATR'));

    window.addEventListener('resize', () => {
        chartNav.resize(); chartDD.resize(); chartSig.resize(); chartATR.resize();
    });

    runBacktest();
}

function fmtDate(yyyymmdd) {
    const s = String(yyyymmdd);
    return `${s.substring(0,4)}-${s.substring(4,6)}-${s.substring(6,8)}`;
}

function fmtDateLabel(yyyymmdd) {
    const s = String(yyyymmdd);
    return `${s.substring(4,6)}/${s.substring(6,8)}`;
}

function parseInputDate(val) {
    if (!val) return null;
    return parseInt(val.replace(/-/g, ''));
}

// ── Donchian通道计算 ──
function calcDonchian(high, low, period) {
    const n = high.length;
    const upper = new Array(n).fill(null);
    const lower = new Array(n).fill(null);
    const mid = new Array(n).fill(null);
    for (let i = period; i < n; i++) {
        let maxH = -Infinity, minL = Infinity;
        for (let j = i - period; j < i; j++) {
            if (high[j] > maxH) maxH = high[j];
            if (low[j] < minL) minL = low[j];
        }
        upper[i] = maxH;
        lower[i] = minL;
        mid[i] = (maxH + minL) / 2;
    }
    return { upper, lower, mid };
}

// ── ATR计算 ──
function calcATR(high, low, close, period) {
    const n = high.length;
    const tr = new Array(n).fill(0);
    const atr = new Array(n).fill(null);
    tr[0] = high[0] - low[0];
    for (let i = 1; i < n; i++) {
        tr[i] = Math.max(
            high[i] - low[i],
            Math.abs(high[i] - close[i - 1]),
            Math.abs(low[i] - close[i - 1])
        );
    }
    for (let i = period - 1; i < n; i++) {
        let sum = 0;
        for (let j = i - period + 1; j <= i; j++) sum += tr[j];
        atr[i] = sum / period;
    }
    return atr;
}

// ── 信号生成 ──
function genSignals(close, upper, lower, atr, channelP, atrMult) {
    const signals = [];
    let position = false;
    let entryPrice = 0;
    for (let i = channelP; i < close.length; i++) {
        if (upper[i] === null || atr[i] === null) continue;
        if (!position) {
            if (close[i] > upper[i]) {
                signals.push({ idx: i, type: 'buy', price: close[i], reason: '突破上轨' });
                position = true;
                entryPrice = close[i];
            }
        } else {
            let sellReason = null;
            if (close[i] < lower[i]) sellReason = '跌破下轨';
            const stopPrice = entryPrice - atrMult * atr[i];
            if (close[i] < stopPrice) sellReason = 'ATR止损';
            if (sellReason) {
                signals.push({ idx: i, type: 'sell', price: close[i], reason: sellReason });
                position = false;
                entryPrice = 0;
            }
        }
    }
    if (position) {
        signals.push({ idx: close.length - 1, type: 'sell', price: close[close.length - 1], reason: '期末平仓' });
    }
    return signals;
}

// ── 回测模拟 ──
function runSim(close, dates, signals, capital, fee, tax, posSize) {
    const n = close.length;
    let cash = capital, shares = 0, entryPrice = 0, entryIdx = 0;
    const dailyValues = new Array(n);
    const trades = [];
    const sigMap = {};
    signals.forEach(s => { sigMap[s.idx] = s; });

    for (let i = 0; i < n; i++) {
        dailyValues[i] = (shares > 0) ? cash + shares * close[i] : cash;
        if (sigMap[i]) {
            const sig = sigMap[i];
            if (sig.type === 'buy') {
                const buyAmt = cash * posSize;
                let s = Math.floor(buyAmt / close[i] / 100) * 100;
                if (s === 0) s = Math.floor(buyAmt / close[i]);
                if (s > 0) {
                    const cost = s * close[i] * (1 + fee);
                    cash -= cost;
                    shares = s;
                    entryPrice = close[i];
                    entryIdx = i;
                }
            } else if (sig.type === 'sell') {
                const revenue = shares * close[i] * (1 - fee - tax);
                cash += revenue;
                const costBasis = shares * entryPrice * (1 + fee);
                const pnl = revenue - costBasis;
                const pnlPct = pnl / costBasis * 100;
                trades.push({
                    buyDate: dates[entryIdx], buyPrice: entryPrice,
                    sellDate: dates[i], sellPrice: close[i],
                    holdDays: i - entryIdx,
                    pnl: pnl, pnlPct: pnlPct,
                    win: pnl > 0 ? 1 : 0,
                    reason: sig.reason
                });
                shares = 0;
            }
        }
    }
    return { dailyValues, trades };
}

// ── 指标计算 ──
function calcMetrics(dailyValues, trades, close, capital) {
    const n = dailyValues.length;
    const finalValue = dailyValues[n - 1];
    const totalReturn = (finalValue - capital) / capital * 100;
    const annualReturn = (Math.pow(finalValue / capital, 252 / n) - 1) * 100;

    const dailyReturns = [];
    for (let i = 1; i < n; i++) dailyReturns.push((dailyValues[i] - dailyValues[i-1]) / dailyValues[i-1]);

    const meanDR = dailyReturns.reduce((a,b) => a + b, 0) / dailyReturns.length;
    const varDR = dailyReturns.reduce((a,b) => a + (b - meanDR) ** 2, 0) / dailyReturns.length;
    const stdDR = Math.sqrt(varDR);
    const volatility = stdDR * Math.sqrt(252) * 100;

    const rfDaily = 0.03 / 252;
    const excess = dailyReturns.map(r => r - rfDaily);
    const meanExcess = excess.reduce((a,b) => a + b, 0) / excess.length;
    const stdExcess = Math.sqrt(excess.reduce((a,b) => a + (b - meanExcess) ** 2, 0) / excess.length);
    const sharpe = stdExcess > 0 ? meanExcess / stdExcess * Math.sqrt(252) : 0;

    const downside = excess.filter(r => r < 0);
    const downsideDev = downside.length > 0
        ? Math.sqrt(downside.reduce((a,b) => a + b*b, 0) / downside.length) * Math.sqrt(252) : 0;
    const sortino = downsideDev > 0 ? meanExcess * 252 / downsideDev : 0;

    let peak = dailyValues[0], maxDD = 0, maxDDPeakIdx = 0, maxDDTroughIdx = 0, currentPeakIdx = 0;
    const drawdown = new Array(n);
    for (let i = 0; i < n; i++) {
        if (dailyValues[i] > peak) { peak = dailyValues[i]; currentPeakIdx = i; }
        drawdown[i] = (dailyValues[i] - peak) / peak;
        if (drawdown[i] < maxDD) { maxDD = drawdown[i]; maxDDPeakIdx = currentPeakIdx; maxDDTroughIdx = i; }
    }
    const calmar = maxDD !== 0 ? annualReturn / (-maxDD * 100) : 0;

    const bhReturn = (close[n-1] - close[0]) / close[0] * 100;
    const bhValues = new Array(n);
    for (let i = 0; i < n; i++) bhValues[i] = capital * close[i] / close[0];

    const bhReturns = [];
    for (let i = 1; i < n; i++) bhReturns.push((bhValues[i] - bhValues[i-1]) / bhValues[i-1]);
    const meanBH = bhReturns.reduce((a,b)=>a+b,0)/bhReturns.length;
    const covXY = dailyReturns.reduce((s, r, i) => s + (r - meanDR) * (bhReturns[i] - meanBH), 0) / dailyReturns.length;
    const varY = bhReturns.reduce((s, r) => s + (r - meanBH) ** 2, 0) / bhReturns.length;
    const beta = varY > 0 ? covXY / varY : 0;
    const alpha = annualReturn - (3 + beta * (bhReturn - 0));

    const trackingErr = Math.sqrt(dailyReturns.reduce((s, r, i) => s + (r - bhReturns[i]) ** 2, 0) / dailyReturns.length) * Math.sqrt(252);
    const infoRatio = trackingErr > 0 ? (annualReturn - bhReturn) / trackingErr : 0;

    const nTrades = trades.length;
    const nWins = trades.filter(t => t.win).length;
    const nLosses = nTrades - nWins;
    const winRate = nTrades > 0 ? nWins / nTrades * 100 : 0;
    const avgHold = nTrades > 0 ? trades.reduce((s,t) => s + t.holdDays, 0) / nTrades : 0;
    const wins = trades.filter(t => t.win), losses = trades.filter(t => !t.win);
    const avgWin = wins.length > 0 ? wins.reduce((s,t) => s + t.pnlPct, 0) / wins.length : 0;
    const avgLoss = losses.length > 0 ? losses.reduce((s,t) => s + t.pnlPct, 0) / losses.length : 0;
    const totalProfit = wins.reduce((s,t) => s + t.pnl, 0);
    const totalLoss = Math.abs(losses.reduce((s,t) => s + t.pnl, 0));
    const profitFactor = totalLoss > 0 ? totalProfit / totalLoss : 0;
    const maxWin = trades.length > 0 ? Math.max(...trades.map(t => t.pnlPct)) : 0;
    const maxLoss = trades.length > 0 ? Math.min(...trades.map(t => t.pnlPct)) : 0;
    let maxConsecLoss = 0, currentConsec = 0;
    for (const t of trades) {
        if (!t.win) { currentConsec++; maxConsecLoss = Math.max(maxConsecLoss, currentConsec); }
        else currentConsec = 0;
    }

    return {
        finalValue, totalReturn, annualReturn, volatility, sharpe, sortino,
        maxDD: maxDD * 100, calmar,
        bhReturn, bhFinalValue: bhValues[n-1],
        alpha, beta, infoRatio,
        nTrades, nWins, nLosses, winRate, avgHold, avgWin, avgLoss,
        profitFactor, maxWin, maxLoss, maxConsecLoss,
        drawdown, bhValues,
        excessReturn: totalReturn - bhReturn
    };
}

// ── 主回测函数 ──
function runBacktest() {
    const stockKey = document.getElementById('selStock').value;
    const channelP = parseInt(document.getElementById('inpChannel').value);
    const atrP = parseInt(document.getElementById('inpATR').value);
    const atrMult = parseFloat(document.getElementById('inpATRMult').value);
    const capital = parseFloat(document.getElementById('inpCapital').value);
    const fee = parseFloat(document.getElementById('inpFee').value);
    const tax = parseFloat(document.getElementById('inpTax').value);
    const posSize = parseFloat(document.getElementById('inpPos').value);
    const startD = parseInputDate(document.getElementById('inpStart').value);
    const endD = parseInputDate(document.getElementById('inpEnd').value);

    const stock = STOCKS_DATA[stockKey];
    if (!stock) return;

    let filtered = stock.data.filter(r => {
        const d = r[0];
        if (startD && d < startD) return false;
        if (endD && d > endD) return false;
        return true;
    });
    if (filtered.length < channelP + atrP + 5) {
        alert('筛选后数据不足，请扩大日期范围或缩短通道周期');
        return;
    }

    const dates = filtered.map(r => r[0]);
    const open  = filtered.map(r => r[1]);
    const high  = filtered.map(r => r[2]);
    const low   = filtered.map(r => r[3]);
    const close = filtered.map(r => r[4]);
    const n = dates.length;

    // 计算通道
    const dc = calcDonchian(high, low, channelP);
    // 计算ATR
    const atr = calcATR(high, low, close, atrP);
    // 生成信号
    const signals = genSignals(close, dc.upper, dc.lower, atr, channelP, atrMult);
    // 回测
    const sim = runSim(close, dates, signals, capital, fee, tax, posSize);
    // 指标
    const m = calcMetrics(sim.dailyValues, sim.trades, close, capital);

    renderMetrics(m, capital, stock);
    renderNavChart(dates, sim.dailyValues, m.bhValues, capital, stock);
    renderDrawdownChart(dates, m.drawdown, stock);
    renderSignalChart(dates, close, dc, signals, channelP, atrMult, stock, open, high, low);
    renderATRChart(dates, atr, atrP, stock);
    renderTradesTable(sim.trades, dates);
}

// ── 渲染指标卡片 ──
function renderMetrics(m, capital, stock) {
    const grid = document.getElementById('metricsGrid');
    const cards = [
        {label: '年化收益率', value: m.annualReturn, suffix: '%', pos: m.annualReturn >= 0, sub: `总收益 ${m.totalReturn.toFixed(2)}%`},
        {label: '夏普比率', value: m.sharpe, suffix: '', pos: m.sharpe >= 1, sub: '无风险利率3%'},
        {label: '最大回撤', value: m.maxDD, suffix: '%', pos: false, neg: true, sub: '越小越好', isNeg: true},
        {label: '胜率', value: m.winRate, suffix: '%', pos: m.winRate >= 50, sub: `${m.nWins}胜${m.nLosses}负 / ${m.nTrades}笔`},
        {label: '卡玛比率', value: m.calmar, suffix: '', pos: m.calmar >= 1, sub: '年化/最大回撤'},
        {label: '索提诺比率', value: m.sortino, suffix: '', pos: m.sortino >= 1, sub: '仅下行风险'},
        {label: '年化波动率', value: m.volatility, suffix: '%', pos: false, sub: '越小越好', isNeg: true},
        {label: '盈亏比', value: m.profitFactor, suffix: '', pos: m.profitFactor >= 1.5, sub: `均盈${m.avgWin.toFixed(1)}% / 均亏${m.avgLoss.toFixed(1)}%`},
        {label: 'Alpha', value: m.alpha, suffix: '%', pos: m.alpha >= 0, sub: '超额收益(vs基准)'},
        {label: 'Beta', value: m.beta, suffix: '', pos: false, sub: '相对基准波动'},
        {label: '信息比率', value: m.infoRatio, suffix: '', pos: m.infoRatio >= 0, sub: '主动管理能力'},
        {label: '最终净值', value: m.finalValue, suffix: '', pos: m.finalValue > capital, sub: `初始¥${capital.toLocaleString()}`},
        {label: '买入持有收益', value: m.bhReturn, suffix: '%', pos: m.bhReturn >= 0, sub: `超额${m.excessReturn.toFixed(2)}%`, benchmark: true},
        {label: '最大单笔盈利', value: m.maxWin, suffix: '%', pos: true, sub: '单笔最佳'},
        {label: '最大连续亏损', value: m.maxConsecLoss, suffix: '笔', pos: false, sub: '风控参考', isNeg: true},
        {label: '平均持仓', value: m.avgHold, suffix: '天', pos: false, sub: `${m.nTrades}笔交易`},
    ];

    grid.innerHTML = cards.map(c => {
        const cls = c.benchmark ? 'metric-card benchmark' : 'metric-card';
        const valCls = c.value >= 0 ? 'value pos' : (c.isNeg ? 'value neg' : 'value neutral');
        const display = typeof c.value === 'number' ? c.value.toFixed(2) : c.value;
        return `<div class="${cls}">
            <div class="label">${c.label}</div>
            <div class="${valCls}">${display}${c.suffix}</div>
            <div class="sub">${c.sub}</div>
        </div>`;
    }).join('');
}

// ── 日期标签 ──
function getXAxisConfig(dates) {
    const n = dates.length;
    const interval = Math.max(1, Math.floor(n / 12));
    const labels = dates.map(d => fmtDateLabel(d));
    return {
        type: 'category',
        data: labels,
        axisLabel: { rotate: 0, interval: interval - 1, fontSize: 10 },
        boundaryGap: false
    };
}

// ── 净值图 ──
function renderNavChart(dates, dailyValues, bhValues, capital, stock) {
    const n = dates.length;
    chartNav.setOption({
        tooltip: { trigger: 'axis', axisPointer: { type: 'cross' },
            formatter: function(params) {
                let s = `<b>${params[0].axisValue}</b><br/>`;
                params.forEach(p => {
                    s += `${p.marker} ${p.seriesName}: ¥${p.value.toLocaleString(undefined, {maximumFractionDigits:0})}<br/>`;
                });
                return s;
            }
        },
        legend: { data: ['策略净值', '买入持有', '初始资金'], top: 5 },
        grid: { left: 70, right: 30, top: 35, bottom: 25 },
        xAxis: getXAxisConfig(dates),
        yAxis: { type: 'value', scale: true, axisLabel: { formatter: v => '¥' + (v/10000).toFixed(1) + '万' } },
        dataZoom: [{ type: 'inside', start: 0, end: 100 }, { type: 'slider', start: 0, end: 100, height: 16 }],
        series: [
            { name: '策略净值', type: 'line', data: dailyValues.map(v => Math.round(v)),
              lineStyle: { width: 1.5, color: '#6c3082' }, itemStyle: { color: '#6c3082' }, symbol: 'none', areaStyle: { color: 'rgba(108,48,130,0.05)' } },
            { name: '买入持有', type: 'line', data: bhValues.map(v => Math.round(v)),
              lineStyle: { width: 1, color: '#f39c12', type: 'dashed' }, itemStyle: { color: '#f39c12' }, symbol: 'none' },
            { name: '初始资金', type: 'line', data: new Array(n).fill(capital),
              lineStyle: { width: 0.8, color: '#bbb', type: 'dotted' }, itemStyle: { color: '#bbb' }, symbol: 'none' }
        ]
    }, true);
}

// ── 回撤图 ──
function renderDrawdownChart(dates, drawdown, stock) {
    const ddPct = drawdown.map(d => +(d * 100).toFixed(2));
    chartDD.setOption({
        tooltip: { trigger: 'axis',
            formatter: p => `<b>${p[0].axisValue}</b><br/>${p[0].marker} 回撤: ${p[0].value}%`
        },
        grid: { left: 60, right: 30, top: 15, bottom: 25 },
        xAxis: getXAxisConfig(dates),
        yAxis: { type: 'value', max: 0, axisLabel: { formatter: '{value}%' } },
        dataZoom: [{ type: 'inside', start: 0, end: 100 }],
        series: [{
            name: '回撤',
            type: 'line',
            data: ddPct,
            lineStyle: { width: 1, color: '#27ae60' },
            itemStyle: { color: '#27ae60' },
            symbol: 'none',
            areaStyle: { color: 'rgba(39,174,96,0.15)' }
        }]
    }, true);
}

// ── 信号图 ──
function renderSignalChart(dates, close, dc, signals, channelP, atrMult, stock, open, high, low) {
    const n = dates.length;

    // K线数据
    const kdata = [];
    for (let i = 0; i < n; i++) kdata.push([open[i], close[i], low[i], high[i]]);

    // 买卖点
    const buyPoints = signals.filter(s => s.type === 'buy').map(s => [s.idx, s.price]);
    const sellPoints = signals.filter(s => s.type === 'sell').map(s => [s.idx, s.price]);

    chartSig.setOption({
        tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
        legend: { data: ['K线', `上轨(${channelP}日最高)`, `下轨(${channelP}日最低)`, '中轨', `买入(${buyPoints.length})`, `卖出(${sellPoints.length})`], top: 5 },
        grid: { left: 60, right: 30, top: 35, bottom: 60 },
        xAxis: getXAxisConfig(dates),
        yAxis: { scale: true },
        dataZoom: [
            { type: 'inside', start: 0, end: 100 },
            { type: 'slider', start: 0, end: 100, height: 16, bottom: 15 }
        ],
        series: [
            {
                name: 'K线', type: 'candlestick', data: kdata,
                itemStyle: { color: '#e74c3c', color0: '#27ae60', borderColor: '#e74c3c', borderColor0: '#27ae60' }
            },
            {
                name: `上轨(${channelP}日最高)`, type: 'line', data: dc.upper,
                lineStyle: { width: 1, color: '#c0392b', type: 'dashed' }, itemStyle: { color: '#c0392b' }, symbol: 'none'
            },
            {
                name: `下轨(${channelP}日最低)`, type: 'line', data: dc.lower,
                lineStyle: { width: 1, color: '#27ae60', type: 'dashed' }, itemStyle: { color: '#27ae60' }, symbol: 'none'
            },
            {
                name: '中轨', type: 'line', data: dc.mid,
                lineStyle: { width: 0.8, color: '#7f8c8d', type: 'dotted' }, itemStyle: { color: '#7f8c8d' }, symbol: 'none'
            },
            {
                name: `买入(${buyPoints.length})`, type: 'scatter', data: buyPoints,
                symbol: 'triangle', symbolSize: 12,
                itemStyle: { color: '#e74c3c' },
                label: { show: true, formatter: '买', position: 'bottom', fontSize: 9, color: '#e74c3c' }
            },
            {
                name: `卖出(${sellPoints.length})`, type: 'scatter', data: sellPoints,
                symbol: 'pin', symbolSize: 12, symbolRotate: 180,
                itemStyle: { color: '#27ae60' },
                label: { show: true, formatter: '卖', position: 'top', fontSize: 9, color: '#27ae60' }
            }
        ]
    }, true);
}

// ── ATR图 ──
function renderATRChart(dates, atr, atrP, stock) {
    chartATR.setOption({
        tooltip: { trigger: 'axis',
            formatter: p => `<b>${p[0].axisValue}</b><br/>${p[0].marker} ATR: ${p[0].value !== null ? p[0].value.toFixed(2) : 'N/A'}`
        },
        grid: { left: 60, right: 30, top: 15, bottom: 25 },
        xAxis: getXAxisConfig(dates),
        yAxis: { type: 'value', scale: true },
        dataZoom: [{ type: 'inside', start: 0, end: 100 }],
        series: [{
            name: `ATR(${atrP}日)`,
            type: 'line',
            data: atr,
            lineStyle: { width: 1, color: '#8e44ad' },
            itemStyle: { color: '#8e44ad' },
            symbol: 'none',
            areaStyle: { color: 'rgba(142,68,173,0.1)' }
        }]
    }, true);
}

// ── 交易明细表 ──
function renderTradesTable(trades, dates) {
    const tbody = document.getElementById('tradesBody');
    if (trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;color:#999;padding:20px;">无交易记录</td></tr>';
        return;
    }
    tbody.innerHTML = trades.map((t, i) => {
        const cls = t.win ? 'win' : 'loss';
        const tag = t.win
            ? '<span class="tag" style="background:#ffebee;color:#c62828;">盈利</span>'
            : '<span class="tag" style="background:#e8f5e9;color:#2e7d32;">亏损</span>';
        const reasonTag = t.reason === 'ATR止损'
            ? '<span class="tag stop">ATR止损</span>'
            : t.reason === '跌破下轨'
            ? '<span class="tag sell">跌破下轨</span>'
            : `<span class="tag" style="background:#e3f2fd;color:#1565c0;">${t.reason}</span>`;
        return `<tr>
            <td>${i + 1}</td>
            <td>${fmtDate(t.buyDate)}</td>
            <td>${t.buyPrice.toFixed(2)}</td>
            <td>${fmtDate(t.sellDate)}</td>
            <td>${t.sellPrice.toFixed(2)}</td>
            <td>${t.holdDays}</td>
            <td class="${cls}">${t.pnl >= 0 ? '+' : ''}${t.pnl.toFixed(2)}</td>
            <td class="${cls}">${t.pnlPct >= 0 ? '+' : ''}${t.pnlPct.toFixed(2)}%</td>
            <td>${reasonTag}</td>
            <td>${tag}</td>
        </tr>`;
    }).join('');
}

// ── 快捷参数 ──
function setPreset(channel, atr, atrMult, cap, fee, tax, pos) {
    document.getElementById('inpChannel').value = channel;
    document.getElementById('inpATR').value = atr;
    document.getElementById('inpATRMult').value = atrMult;
    document.getElementById('inpCapital').value = cap;
    document.getElementById('inpFee').value = fee;
    document.getElementById('inpTax').value = tax;
    document.getElementById('inpPos').value = pos;
    runBacktest();
}

// 启动
init();
</script>
</body>
</html>'''

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(HTML)

size_kb = os.path.getsize(OUTPUT) / 1024
print(f"\n看板已生成: {OUTPUT}")
print(f"文件大小: {size_kb:.1f} KB")
