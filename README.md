# AI-Quant 量化交易策略回测

## 策略列表

### 1. 双均线交叉策略 (MA Crossover)
- 文件: `test/backtest_dashboard.html`
- 策略: MA短/长均线金叉买入、死叉卖出

### 2. 高低价格通道 + ATR 策略 (Donchian Channel + ATR)
- 看板: `test/channel_atr_dashboard.html`
- 脚本: `test/channel_atr_backtest.py`
- 策略逻辑:
  - Donchian通道: 上轨=N日最高价, 下轨=N日最低价
  - ATR: M日True Range均值, 用于动态止损
  - 买入: 收盘价突破上轨
  - 卖出: 收盘价跌破下轨 或 ATR止损(入场价 - k×ATR)

## 在线看板
- [高低通道+ATR策略看板](https://suhang-s.github.io/AI-Quant/test/channel_atr_dashboard.html)

## 数据来源
- Tushare (前复权日线数据)
- 股票: 比亚迪/南大光电/长江电力/药明康德/中芯国际
