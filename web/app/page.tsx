'use client';

import { useEffect, useMemo, useState } from 'react';

type Candle = {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
};

type Timeframe = '5m' | '15m' | '1h' | '4h';

const TIMEFRAMES: { id: Timeframe; label: string; interval: string; limit: number }[] = [
  { id: '5m', label: '5m', interval: '5m', limit: 220 },
  { id: '15m', label: '15m', interval: '15m', limit: 220 },
  { id: '1h', label: '1H', interval: '1h', limit: 220 },
  { id: '4h', label: '4H', interval: '4h', limit: 220 },
];

const BTCUSDT_PRICE = 'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT';

function klinesUrl(interval: string, limit: number) {
  return `https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=${interval}&limit=${limit}`;
}

function formatUsd(value: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value);
}

function formatPriceAxis(value: number) {
  return `$${value.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

function formatTimeAxis(value: number, timeframe: Timeframe) {
  const date = new Date(value);
  if (timeframe === '1h' || timeframe === '4h') {
    return date.toLocaleString([], { month: 'short', day: '2-digit', hour: '2-digit' });
  }
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function toCandles(raw: unknown[]): Candle[] {
  return (raw || []).map((entry) => {
    const values = entry as [number, string, string, string, string, string, number, number, number, number, number, number];
    return {
      time: values[0],
      open: Number(values[1]),
      high: Number(values[2]),
      low: Number(values[3]),
      close: Number(values[4]),
    };
  });
}

function average(values: number[]) {
  if (!values.length) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function stdDev(values: number[], mean: number) {
  if (!values.length) return 0;
  const variance = average(values.map((value) => (value - mean) ** 2));
  return Math.sqrt(variance);
}

// Returns an EMA series aligned to the input values (same length).
function emaSeries(values: number[], period: number): number[] {
  if (!values.length) return [];
  const multiplier = 2 / (period + 1);
  const result: number[] = [values[0]];
  for (let i = 1; i < values.length; i += 1) {
    result.push(values[i] * multiplier + result[i - 1] * (1 - multiplier));
  }
  return result;
}

function smaSeries(values: number[], period: number): number[] {
  const result: number[] = [];
  for (let i = 0; i < values.length; i += 1) {
    const start = Math.max(0, i - period + 1);
    result.push(average(values.slice(start, i + 1)));
  }
  return result;
}

function rsiSeries(values: number[], period = 14): number[] {
  const result: number[] = new Array(values.length).fill(50);
  if (values.length < period + 1) return result;

  let gainSum = 0;
  let lossSum = 0;
  for (let i = 1; i <= period; i += 1) {
    const change = values[i] - values[i - 1];
    if (change >= 0) gainSum += change;
    else lossSum -= change;
  }
  let avgGain = gainSum / period;
  let avgLoss = lossSum / period;
  result[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);

  for (let i = period + 1; i < values.length; i += 1) {
    const change = values[i] - values[i - 1];
    const gain = change > 0 ? change : 0;
    const loss = change < 0 ? -change : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    result[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }

  for (let i = 0; i < period; i += 1) {
    result[i] = result[period];
  }

  return result;
}

function macdSeries(values: number[], fast = 12, slow = 26, signalPeriod = 9) {
  const emaFast = emaSeries(values, fast);
  const emaSlow = emaSeries(values, slow);
  const macdLine = values.map((_, i) => emaFast[i] - emaSlow[i]);
  const signalLine = emaSeries(macdLine, signalPeriod);
  const histogram = macdLine.map((value, i) => value - signalLine[i]);
  return { macdLine, signalLine, histogram };
}

function bollingerBands(values: number[], period = 20, multiplier = 2) {
  const upper: number[] = [];
  const lower: number[] = [];
  const mid: number[] = [];
  for (let i = 0; i < values.length; i += 1) {
    const start = Math.max(0, i - period + 1);
    const window = values.slice(start, i + 1);
    const mean = average(window);
    const sd = stdDev(window, mean);
    mid.push(mean);
    upper.push(mean + multiplier * sd);
    lower.push(mean - multiplier * sd);
  }
  return { upper, lower, mid };
}

type Signal = 'Strong Buy' | 'Buy' | 'Neutral' | 'Sell' | 'Strong Sell';

function signalFromScore(score: number): Signal {
  if (score >= 3) return 'Strong Buy';
  if (score >= 1) return 'Buy';
  if (score <= -3) return 'Strong Sell';
  if (score <= -1) return 'Sell';
  return 'Neutral';
}

function signalColor(signal: Signal) {
  if (signal === 'Strong Buy' || signal === 'Buy') return '#2bd784';
  if (signal === 'Strong Sell' || signal === 'Sell') return '#ff6584';
  return '#e8c15a';
}

export default function Home() {
  const [timeframe, setTimeframe] = useState<Timeframe>('15m');
  const [candles, setCandles] = useState<Candle[]>([]);
  const [price, setPrice] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const config = TIMEFRAMES.find((tf) => tf.id === timeframe) ?? TIMEFRAMES[1];

    const load = async () => {
      try {
        const [klineResponse, priceResponse] = await Promise.all([
          fetch(klinesUrl(config.interval, config.limit)),
          fetch(BTCUSDT_PRICE),
        ]);

        if (!klineResponse.ok || !priceResponse.ok) {
          throw new Error('Market data is unavailable right now.');
        }

        const klineJson = await klineResponse.json();
        const priceJson = await priceResponse.json();

        if (cancelled) return;

        const nextCandles = toCandles(klineJson as unknown[]);
        setCandles(nextCandles);
        setPrice(Number(priceJson?.price ?? nextCandles.at(-1)?.close ?? 0));
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Unable to load market data.');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    setIsLoading(true);
    load();
    const timer = setInterval(load, 15000);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [timeframe]);

  const chartCandles = useMemo(() => candles.slice(-90), [candles]);
  const currentPrice = price ?? chartCandles.at(-1)?.close ?? 0;
  const closeValues = chartCandles.map((candle) => candle.close);

  const ema9Series = useMemo(() => emaSeries(closeValues, 9), [closeValues]);
  const ema21Series = useMemo(() => emaSeries(closeValues, 21), [closeValues]);
  const sma50Series = useMemo(() => smaSeries(closeValues, 50), [closeValues]);
  const rsi = useMemo(() => rsiSeries(closeValues, 14), [closeValues]);
  const macd = useMemo(() => macdSeries(closeValues, 12, 26, 9), [closeValues]);
  const bb = useMemo(() => bollingerBands(closeValues, 20, 2), [closeValues]);

  const ema9 = ema9Series.at(-1) ?? currentPrice;
  const ema21 = ema21Series.at(-1) ?? currentPrice;
  const sma50 = sma50Series.at(-1) ?? currentPrice;
  const rsiLast = rsi.at(-1) ?? 50;
  const macdLast = macd.macdLine.at(-1) ?? 0;
  const signalLast = macd.signalLine.at(-1) ?? 0;
  const bbUpper = bb.upper.at(-1) ?? currentPrice;
  const bbLower = bb.lower.at(-1) ?? currentPrice;

  // Combine indicator votes into a single score (-4..+4).
  let score = 0;
  const votes: { label: string; verdict: 'bull' | 'bear' | 'neutral'; detail: string }[] = [];

  if (ema9 > ema21 && ema21 > sma50) {
    score += 1;
    votes.push({ label: 'EMA trend', verdict: 'bull', detail: 'EMA9 > EMA21 > SMA50' });
  } else if (ema9 < ema21 && ema21 < sma50) {
    score -= 1;
    votes.push({ label: 'EMA trend', verdict: 'bear', detail: 'EMA9 < EMA21 < SMA50' });
  } else {
    votes.push({ label: 'EMA trend', verdict: 'neutral', detail: 'Mixed moving averages' });
  }

  if (rsiLast < 30) {
    score += 1;
    votes.push({ label: 'RSI(14)', verdict: 'bull', detail: `${rsiLast.toFixed(1)} oversold` });
  } else if (rsiLast > 70) {
    score -= 1;
    votes.push({ label: 'RSI(14)', verdict: 'bear', detail: `${rsiLast.toFixed(1)} overbought` });
  } else {
    votes.push({ label: 'RSI(14)', verdict: 'neutral', detail: `${rsiLast.toFixed(1)} neutral zone` });
  }

  if (macdLast > signalLast) {
    score += 1;
    votes.push({ label: 'MACD(12,26,9)', verdict: 'bull', detail: 'MACD above signal' });
  } else if (macdLast < signalLast) {
    score -= 1;
    votes.push({ label: 'MACD(12,26,9)', verdict: 'bear', detail: 'MACD below signal' });
  } else {
    votes.push({ label: 'MACD(12,26,9)', verdict: 'neutral', detail: 'MACD flat' });
  }

  if (currentPrice <= bbLower) {
    score += 1;
    votes.push({ label: 'Bollinger Bands', verdict: 'bull', detail: 'Price at/below lower band' });
  } else if (currentPrice >= bbUpper) {
    score -= 1;
    votes.push({ label: 'Bollinger Bands', verdict: 'bear', detail: 'Price at/above upper band' });
  } else {
    votes.push({ label: 'Bollinger Bands', verdict: 'neutral', detail: 'Price within bands' });
  }

  const overallSignal = signalFromScore(score);
  const buyEntry = Math.min(bbLower, ema21);
  const sellEntry = Math.max(bbUpper, ema21);

  const width = 1200;
  const height = 460;
  const rsiHeight = 90;
  const macdHeight = 90;
  const pad = { top: 24, right: 36, bottom: 30, left: 72 };
  const minPrice = Math.min(...chartCandles.map((candle) => candle.low), currentPrice * 0.995, bbLower);
  const maxPrice = Math.max(...chartCandles.map((candle) => candle.high), currentPrice * 1.005, bbUpper);
  const priceRange = Math.max(maxPrice - minPrice, 1);

  // Reserve comfortable margin (12 bars worth of space) on the right for the latest candle
  const rightMarginBars = 12;
  const xForIndex = (index: number) => {
    const inner = width - pad.left - pad.right;
    const totalSlots = Math.max(chartCandles.length - 1 + rightMarginBars, 1);
    return pad.left + (index / totalSlots) * inner;
  };

  const yForPrice = (value: number) => {
    const inner = height - pad.top - pad.bottom;
    return pad.top + ((maxPrice - value) / priceRange) * inner;
  };

  const priceTicks = chartCandles.length
    ? Array.from({ length: 6 }, (_, index) => {
        const value = minPrice + (priceRange / 5) * index;
        return { value, y: yForPrice(value) };
      }).reverse()
    : [];

  const timeTicks = chartCandles.length
    ? Array.from({ length: 6 }, (_, index) => {
        const candleIndex = Math.round((index / 5) * (chartCandles.length - 1));
        const candle = chartCandles[candleIndex] ?? chartCandles[chartCandles.length - 1];
        return { label: formatTimeAxis(candle.time, timeframe), x: xForIndex(candleIndex) };
      })
    : [];

  const linePath = (series: number[]) =>
    series
      .map((value, index) => `${index === 0 ? 'M' : 'L'} ${xForIndex(index)} ${yForPrice(value)}`)
      .join(' ');

  const ema9Path = linePath(ema9Series);
  const ema21Path = linePath(ema21Series);
  const sma50Path = linePath(sma50Series);
  const bbUpperPath = linePath(bb.upper);
  const bbLowerPath = linePath(bb.lower);

  // RSI sub-panel
  const rsiTop = height + 14;
  const yForRsi = (value: number) => rsiTop + rsiHeight - (value / 100) * rsiHeight;
  const rsiPath = rsi
    .map((value, index) => `${index === 0 ? 'M' : 'L'} ${xForIndex(index)} ${yForRsi(value)}`)
    .join(' ');

  // MACD sub-panel
  const macdTop = rsiTop + rsiHeight + 26;
  const macdAll = [...macd.macdLine, ...macd.signalLine, ...macd.histogram].filter((v) => Number.isFinite(v));
  const macdRange = Math.max(...macdAll.map(Math.abs), 1);
  const yForMacd = (value: number) => macdTop + macdHeight / 2 - (value / macdRange) * (macdHeight / 2);
  const macdLinePath = macd.macdLine
    .map((value, index) => `${index === 0 ? 'M' : 'L'} ${xForIndex(index)} ${yForMacd(value)}`)
    .join(' ');
  const macdSignalPath = macd.signalLine
    .map((value, index) => `${index === 0 ? 'M' : 'L'} ${xForIndex(index)} ${yForMacd(value)}`)
    .join(' ');

  const totalSvgHeight = macdTop + macdHeight + 20;

  if (isLoading && !candles.length) {
    return (
      <main style={{ minHeight: '100vh', background: '#081420', color: '#eaf5ff', display: 'grid', placeItems: 'center', fontFamily: 'Arial, sans-serif' }}>
        <div>Loading BTCUSDT live chart…</div>
      </main>
    );
  }

  return (
    <main
      style={{
        minHeight: '100vh',
        background: '#081420',
        color: '#eaf5ff',
        padding: '18px 20px 40px',
        fontFamily: 'Arial, sans-serif',
      }}
    >
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        <header
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 12,
            marginBottom: 18,
            flexWrap: 'wrap',
          }}
        >
          <div>
            <div style={{ fontSize: 12, letterSpacing: 2, color: '#8ecae6', textTransform: 'uppercase' }}>
              cryptoterminal
            </div>
            <h1 style={{ margin: '8px 0 0', fontSize: 30 }}>BTCUSDT • live signal chart</h1>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf.id}
                onClick={() => setTimeframe(tf.id)}
                style={{
                  border: `1px solid ${tf.id === timeframe ? 'rgba(125, 211, 252, 0.9)' : 'rgba(120, 208, 255, 0.25)'}`,
                  background: tf.id === timeframe ? 'rgba(125, 211, 252, 0.18)' : 'rgba(18, 47, 67, 0.6)',
                  color: tf.id === timeframe ? '#bfe8ff' : '#9bb5c8',
                  borderRadius: 8,
                  padding: '8px 14px',
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {tf.label}
              </button>
            ))}
          </div>

          <div
            style={{
              border: '1px solid rgba(120, 208, 255, 0.45)',
              background: 'rgba(18, 47, 67, 0.75)',
              borderRadius: 999,
              padding: '8px 14px',
              fontSize: 12,
              letterSpacing: 1.1,
              color: '#7fe3c2',
            }}
          >
            LIVE DATA • SIGNAL ONLY
          </div>
        </header>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
            gap: 12,
            marginBottom: 18,
          }}
        >
          {[
            ['Market', 'BTC/USD'],
            ['Last price', formatUsd(currentPrice)],
            ['Signal', overallSignal],
            ['Buy entry (long)', formatUsd(buyEntry)],
            ['Sell entry (short)', formatUsd(sellEntry)],
            ['RSI(14)', rsiLast.toFixed(1)],
          ].map(([label, value]) => (
            <div
              key={label}
              style={{
                background: 'rgba(12, 23, 36, 0.9)',
                border: '1px solid rgba(132, 169, 199, 0.26)',
                borderRadius: 12,
                padding: '12px 14px',
              }}
            >
              <div style={{ fontSize: 11, color: '#8ca9bb', letterSpacing: 1.1, textTransform: 'uppercase' }}>{label}</div>
              <div
                style={{
                  fontSize: 19,
                  fontWeight: 700,
                  marginTop: 8,
                  color: label === 'Signal' ? signalColor(overallSignal) : '#eaf5ff',
                }}
              >
                {value}
              </div>
            </div>
          ))}
        </div>

        {error ? (
          <div style={{ marginBottom: 18, background: 'rgba(90, 30, 30, 0.25)', border: '1px solid rgba(255,120,120,0.3)', borderRadius: 10, padding: 12, color: '#ffc2c2' }}>
            {error}
          </div>
        ) : null}

        <div
          style={{
            background: '#0a1823',
            border: '1px solid rgba(121, 164, 193, 0.3)',
            borderRadius: 18,
            padding: 10,
            boxShadow: '0 18px 30px rgba(0,0,0,0.25)',
            marginBottom: 18,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px 2px', fontSize: 12, color: '#9bb5c8' }}>
            <span>BTCUSDT {TIMEFRAMES.find((tf) => tf.id === timeframe)?.label}</span>
            <span>{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
          </div>

          <svg viewBox={`0 0 ${width} ${totalSvgHeight}`} width="100%" height={totalSvgHeight} role="img" aria-label="Trading view style BTCUSDT live chart">
            {priceTicks.map((tick) => (
              <g key={tick.y}>
                <line x1={pad.left} x2={width - pad.right} y1={tick.y} y2={tick.y} stroke="rgba(133,160,182,0.12)" strokeWidth={1} />
                <text x={pad.left - 10} y={tick.y + 4} textAnchor="end" fill="#9bb5c8" fontSize="11">{formatPriceAxis(tick.value)}</text>
              </g>
            ))}

            {timeTicks.map((tick) => (
              <text key={`${tick.label}-${tick.x}`} x={tick.x} y={height - 8} fill="#9bb5c8" fontSize="11" textAnchor="middle">
                {tick.label}
              </text>
            ))}

            {/* Bollinger Bands */}
            <path d={bbUpperPath} fill="none" stroke="rgba(125, 211, 252, 0.45)" strokeWidth={1} strokeDasharray="3 4" />
            <path d={bbLowerPath} fill="none" stroke="rgba(125, 211, 252, 0.45)" strokeWidth={1} strokeDasharray="3 4" />

            {/* Candles */}
            <g>
              {chartCandles.map((candle, index) => {
                const x = xForIndex(index);
                const openY = yForPrice(candle.open);
                const closeY = yForPrice(candle.close);
                const highY = yForPrice(candle.high);
                const lowY = yForPrice(candle.low);
                const isUp = candle.close >= candle.open;
                const color = isUp ? '#2bd784' : '#ff6584';
                const bodyTop = Math.min(openY, closeY);
                const bodyHeight = Math.max(Math.abs(closeY - openY), 2);

                return (
                  <g key={`candle-${candle.time}`}>
                    <line x1={x} x2={x} y1={highY} y2={lowY} stroke={color} strokeWidth={1.2} />
                    <rect x={x - 4.5} y={bodyTop} width={9} height={bodyHeight} rx={2} fill={color} />
                  </g>
                );
              })}
            </g>

            {/* Moving averages */}
            <path d={ema9Path} fill="none" stroke="#7dd3fc" strokeWidth={1.6} strokeLinejoin="round" strokeLinecap="round" />
            <path d={ema21Path} fill="none" stroke="#c4b5fd" strokeWidth={1.6} strokeLinejoin="round" strokeLinecap="round" />
            <path d={sma50Path} fill="none" stroke="#f4a261" strokeWidth={1.4} strokeLinejoin="round" strokeLinecap="round" />

            {/* Buy / sell zone lines */}
            <line x1={pad.left} x2={width - pad.right} y1={yForPrice(buyEntry)} y2={yForPrice(buyEntry)} stroke="rgba(70,220,155,0.85)" strokeDasharray="6 6" strokeWidth={1.2} />
            <line x1={pad.left} x2={width - pad.right} y1={yForPrice(sellEntry)} y2={yForPrice(sellEntry)} stroke="rgba(255,110,110,0.85)" strokeDasharray="6 6" strokeWidth={1.2} />

            {/* Live price projection line & badge */}
            <line
              x1={xForIndex(chartCandles.length - 1)}
              x2={width - pad.right}
              y1={yForPrice(currentPrice)}
              y2={yForPrice(currentPrice)}
              stroke="#38bdf8"
              strokeDasharray="3 3"
              strokeWidth={1.2}
            />
            <g>
              <rect
                x={width - pad.right - 64}
                y={yForPrice(currentPrice) - 9}
                width={64}
                height={18}
                rx={4}
                fill="#0284c7"
              />
              <text
                x={width - pad.right - 32}
                y={yForPrice(currentPrice) + 4}
                textAnchor="middle"
                fill="#ffffff"
                fontSize="10"
                fontWeight="700"
              >
                {formatPriceAxis(currentPrice)}
              </text>
            </g>

            {/* Legend */}
            <g>
              <rect x={pad.left + 10} y={pad.top} width={330} height={22} rx={6} fill="rgba(15, 26, 38, 0.6)" />
              <text x={pad.left + 18} y={pad.top + 15} fill="#7dd3fc" fontSize="11">— EMA9</text>
              <text x={pad.left + 90} y={pad.top + 15} fill="#c4b5fd" fontSize="11">— EMA21</text>
              <text x={pad.left + 165} y={pad.top + 15} fill="#f4a261" fontSize="11">— SMA50</text>
              <text x={pad.left + 240} y={pad.top + 15} fill="#7dd3fc" fontSize="11" opacity={0.6}>┄ Bollinger</text>
            </g>

            {/* RSI panel */}
            <line x1={pad.left} x2={width - pad.right} y1={rsiTop} y2={rsiTop} stroke="rgba(154,169,183,0.15)" />
            <text x={pad.left} y={rsiTop - 4} fill="#9bb5c8" fontSize="11">RSI (14)</text>
            <line x1={pad.left} x2={width - pad.right} y1={yForRsi(70)} y2={yForRsi(70)} stroke="rgba(255,110,110,0.35)" strokeDasharray="3 4" />
            <line x1={pad.left} x2={width - pad.right} y1={yForRsi(30)} y2={yForRsi(30)} stroke="rgba(70,220,155,0.35)" strokeDasharray="3 4" />
            <path d={rsiPath} fill="none" stroke="#e8c15a" strokeWidth={1.4} />
            <text x={width - pad.right - 30} y={yForRsi(70) - 4} fill="#ff9aa6" fontSize="10">70</text>
            <text x={width - pad.right - 30} y={yForRsi(30) - 4} fill="#8fe3c2" fontSize="10">30</text>

            {/* MACD panel */}
            <line x1={pad.left} x2={width - pad.right} y1={macdTop} y2={macdTop} stroke="rgba(154,169,183,0.15)" />
            <text x={pad.left} y={macdTop - 4} fill="#9bb5c8" fontSize="11">MACD (12, 26, 9)</text>
            <line x1={pad.left} x2={width - pad.right} y1={yForMacd(0)} y2={yForMacd(0)} stroke="rgba(154,169,183,0.25)" />
            {macd.histogram.map((value, index) => {
              const x = xForIndex(index);
              const y0 = yForMacd(0);
              const y1 = yForMacd(value);
              return (
                <rect
                  key={`hist-${index}`}
                  x={x - 2}
                  y={Math.min(y0, y1)}
                  width={4}
                  height={Math.max(Math.abs(y1 - y0), 1)}
                  fill={value >= 0 ? 'rgba(43,215,132,0.55)' : 'rgba(255,101,132,0.55)'}
                />
              );
            })}
            <path d={macdLinePath} fill="none" stroke="#7dd3fc" strokeWidth={1.3} />
            <path d={macdSignalPath} fill="none" stroke="#f4a261" strokeWidth={1.3} />
          </svg>
        </div>

        <div
          style={{
            background: 'rgba(12, 23, 36, 0.9)',
            border: '1px solid rgba(132, 169, 199, 0.26)',
            borderRadius: 12,
            padding: '16px 18px',
          }}
        >
          <div style={{ fontSize: 13, letterSpacing: 1, color: '#8ca9bb', textTransform: 'uppercase', marginBottom: 12 }}>
            Indicator breakdown ({TIMEFRAMES.find((tf) => tf.id === timeframe)?.label})
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
            {votes.map((vote) => (
              <div
                key={vote.label}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  border: '1px solid rgba(132, 169, 199, 0.18)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{vote.label}</div>
                  <div style={{ fontSize: 12, color: '#9bb5c8' }}>{vote.detail}</div>
                </div>
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: 700,
                    padding: '4px 10px',
                    borderRadius: 999,
                    color: vote.verdict === 'bull' ? '#2bd784' : vote.verdict === 'bear' ? '#ff6584' : '#e8c15a',
                    background:
                      vote.verdict === 'bull'
                        ? 'rgba(43,215,132,0.12)'
                        : vote.verdict === 'bear'
                        ? 'rgba(255,101,132,0.12)'
                        : 'rgba(232,193,90,0.12)',
                  }}
                >
                  {vote.verdict === 'bull' ? 'Bullish' : vote.verdict === 'bear' ? 'Bearish' : 'Neutral'}
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 14, fontSize: 12, color: '#6f8ba0' }}>
            Signal-only view for research/hobby use. Not financial advice, no order execution.
          </div>
        </div>
      </div>
    </main>
  );
}
