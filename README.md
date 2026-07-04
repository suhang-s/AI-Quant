# AI-Quant

科大讯飞 (002230.SZ) 行情数据可视化面板。

## 内容

- `index.html` — K 线图与交易量交互式面板（ECharts，离线可看，数据内嵌）
- `kdxf_daily.csv` — 近 2 年日线行情原始数据（来源：Tushare）

## 数据说明

- 股票：科大讯飞 002230.SZ
- 区间：2024-07-04 ~ 2026-07-03（484 个交易日）
- 字段：ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
- 数据来源：[Tushare](https://tushare.pro)

## 面板功能

- 顶部统计卡片：最新价、区间涨跌幅、最高/最低价、日均量、总成交额等
- K 线图：日K + MA5/MA20/MA60 均线，支持缩放拖动
- 交易量图：成交量柱状（涨红跌绿）+ 成交额折线，双 Y 轴

## 在线浏览

打开 `index.html` 即可查看，或访问在线部署地址。
