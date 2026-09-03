# Web dashboard

Simple signal-only market dashboard for hobby use.

It shows a live BTCUSDT candlestick chart with switchable timeframes (5m, 15m, 1H, 4H) and a mixed indicator suite:

- EMA(9), EMA(21), SMA(50) trend overlay
- Bollinger Bands (20, 2)
- RSI(14) sub-panel
- MACD(12, 26, 9) sub-panel

The indicators are combined into a single Buy / Sell / Neutral suggestion with a per-indicator breakdown, and annotated buy/short entry zone lines. There is no execution logic, broker APIs, or wallet integration — this is a signal-only research view, not financial advice.
