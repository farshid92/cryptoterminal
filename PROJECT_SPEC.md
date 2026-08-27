PROJECT SPEC — CRYPTOTERMINAL v1.0
Bitcoin-first daily trading ANALYSIS system. Read fully. Obey strictly.
═══════════════════════════════════════════════════════════════
1. ROLE & MISSION
You are the sole senior engineer on this repo. You build, in strict phaseorder, a BTC trading analysis platform: data ingestion → features → labels→ validated models → signal serving → monitoring. You never execute trades.You never skip validation gates. Quality > speed > cleverness.

2. HARD RULES (NEVER VIOLATE)
R1. NO order execution, exchange keys, or trading logic beyond signals.R2. Free/public APIs only: Binance public REST+WS (primary), CoinGecko (fallback), CryptoCompare news (sentiment). No paid tiers.R3. Work ONLY inside the active phase. If a task spans phases, split it and finish the current-phase part first.R4. Before writing ANY file: state its path. Before creating a NEW dependency: justify in one line and flag [NEW-DEP].R5. Never invent library methods/endpoints. If uncertain about an API, say "UNVERIFIED" and provide the official docs URL next to it.R6. Every numeric run must be reproducible: seed RNGs (SEED env var, default 42), pin versions, log dataset hash to MLflow.R7. ALL timestamps UTC epoch-ms internally; ISO-8601 only at display edges.R8. Point-in-time correctness everywhere: no feature may use data dated after its own timestamp. Any code risking look-ahead bias is a bug.R9. Real-time context aware: WS messages update state; never block event loops; heavy work goes to Celery tasks.R10. On conflict between an existing file and this spec → STOP and ask.R11. Model promotion is metric-gated only (see §6 gates). Never promote because code "looks right".R12. Scope-lock defaults: symbol=BTCUSDT; intervals={1m,5m,15m,1h,4h,1d}; base timeframe=1h. Changes require explicit user instruction.

3. TECH STACK (PINNED — do not substitute without asking)
Backend/Data : Python 3.11, ccxt, pandas, numpy, numba, scipy, scikit-learn, xgboost, lightgbm, torch>=2.2, pytorch-lightning, pytorch-forecasting, optuna, mlflow, feast[serving], dagster, fastapi, uvicorn, celery, redis-py(→valkey compatible), sqlalchemy2+ asyncpg, pandera, pyarrow, onnx, onnxruntimeStorage : TimescaleDB (timescale/timescaledb:latest-pg16), Valkey 7, MinIOServing(opt) : NVIDIA Triton (fallback: onnxruntime embedded in FastAPI — use this until Phase 5 Gate requires scale)Monitoring : prometheus-client, Grafana, Loki (Phase 6 only)Frontend : Next.js 14 (App Router, TypeScript), Tailwind, Radix UI, lightweight-charts@4.x, zustand, @tanstack/react-queryInfra : Docker Compose (dev), GitHub Actions CI, ruff, pytestForbidden : TA-Lib binary dep (implement in features/ with numba; validate vs pandas-ta values in tests only).

4. CANONICAL REPO STRUCTURE (create exactly; never improvise paths)
cryptoterminal/├─ .github/│ ├─ copilot-instructions.md # copy of this spec│ └─ workflows/ci.yml├─ infra/docker-compose.yml # timescaledb,valkey,minio,mlflow,│ # api,scheduler,dagster,web,prometheus├─ config/{settings.py,.env.example} # pydantic-settings; see §8├─ ingestion/│ ├─ binance_rest.py # historical klines paginator│ ├─ binance_ws.py # live stream worker│ ├─ gap_detector.py # missing-candle scan/report│ └─ writers.py # upserts → TSDB, pub → valkey├─ features/│ ├─ technical.py # ~45 indicator feats (numba)│ ├─ price_action.py # candle/pattern/swing/S-R/MTF (~25)│ ├─ derived.py # crosses,divergences,slopes,regime (~15)│ ├─ sentiment.py # cryptocompare fetch → score rows│ ├─ builder.py # merge → parquet + feast materialize│ └─ registry.py # FEATURE_LIST source-of-truth list├─ labeling/│ ├─ triple_barrier.py # labels+touch_times+returns│ └─ sample_weights.py # uniqueness×ret-mag×time-decay├─ models/│ ├─ baselines.py # buyhold/random/rsi/sma strategies│ ├─ xgb_model.py # primary classifier│ ├─ lstm_model.py # BiLSTM+attn seq classifier│ ├─ tft_model.py # multi-horizon quantiles│ ├─ cnn_model.py # 1D conv pattern detector│ ├─ finbert_sentiment.py # fine-tune wrapper│ ├─ meta_learner.py # stacking combiner + calibration│ └─ export_onnx.py # export + 1e-5 parity checks├─ backtest/│ ├─ purged_cv.py # purge+embargo folds│ ├─ walk_forward.py # expanding-window OOS harness│ └─ metrics.py # sharpe,sortino,calmar,PF,DD,hit...├─ serving/│ ├─ main.py # FastAPI app+routes (see §7)│ ├─ signal_engine.py # candle→feats→infer→combine→signal│ ├─ risk_reward.py # entry/SL(structural)/TP1(2R)/TP2│ └─ ws_fanout.py # valkey sub → client WS push├─ pipeline/assets.py # dagster defs wiring phases 1-4├─ workers/celery_app.py # backtest/retrain jobs├─ mlops/{drift.py,retrain.py} # PSI/KL drift, auto-retrain trigger├─ web/ # Next.js dashboard (see §9)├─ tests/ # mirrors src layout; pytest├─ scripts/{bootstrap_db.sh,backfill.sh,seed_checks.sh}├─ notebooks/01_eda.ipynb ... # research only, importable src pkg├─ docs/│ ├─ ARCHITECTURE.md # diagram+service boundaries│ ├─ ROADMAP.md # §6 verbatim + gate status table│ ├─ DATA_DICTIONARY.md # every feature def (Phase 1 creates)│ └─ CONTRACTS.md # API+schema contracts (§7 seed)├─ README.md # quickstart, structure, phase status├─ pyproject.toml # deps locked; ruff+mypy config└─ Makefile # setup/backfill/train/test/up targets

5. FILE CONTRACTS (responsibility one-liners — implement to these)
ingestion/binance_rest.fetch_klines(sym,interval,start,end)->rows[dict]Paginate limit=1000 backwards→forwards; dedupe on PK; retry exp-backoff.
writers.upsert_candles(df): ON CONFLICT (symbol,time) DO UPDATE.
gap_detector.scan(table,gap='1min')->report df (flag, do NOT fill).
features/technical.compute_all(df_ohlcv)->df_feats (pure fn, no IO).Each fn tested vs small hand-computed arrays; edge: const-price,vol=0.
price_action.detect_patterns(c)->list[{name,bias,strength}]
price_action.support_resistance(c,n_swing=20,cluster_pct=0.005)->lvls
labeling.triple_barrier(c,atr,horizon,tp_m=2.0,sl_m=1.0)-> {label[-1,0,1],touch_i,ret}
backtest.purged_cv(n,touch_times,n_splits=5,embargo_bars)
backtest.walk_forward(model_factory,data,train_w,test_w)->oos_pred_df
models.*.fit/train(X,y,w)/predict_proba; identical interface across all.
export_onnx.export_and_verify(m,sample)->path (assert max|Δ|<1e-5).
signal_engine.run_once(sym,tf)->{signal,conf,probs,rr,ts} ->valkey+TSDB.
risk_reward.levels(entry,atr,support,resistance,direction)->dictSL=(structural ∓0.5ATR); TP1=entry±2·risk; TP2=opposite structural.
6. PHASES & ACCEPTANCE GATES (build strictly top-down)
P0 Foundation : docker stack green; backfill BTCUSDT 1m from listing; aggregates verified; WS 10-min soak ok. GATE: OHLCV-violation count==0; aggregate spot-check 10/10 pass.P1 Features : registry.py defines ALL feats; builder emits parquet; feast online latency<5ms p99. GATE: unit tests 100%; null-rate<5% post-warmup; PIT audit 100 random ts match recompute-from-prefix.P2 Labels : triple barrier + weights + splits. GATE: class dist within 25–45% each; purge proof zero train/test overlap; held-out last-6mo untouched (grep-guard in CI comment).P3 XGBoost : Optuna 200 trials; baselines first (buyhold,random, RSI-rev,SMA-cross) logged to MLflow. GATE: OOS-wf Sharpe ≥ sma_baseline+0.3; DD≤30%; PF≥1.3; ≥10% non-neutral signals; rolling90d Sharpe>0 in ≥70% windows.P4 Ensemble : add LSTM,CNN,TFT,FinBERT→meta learner(stacking). GATE: ens Sharpe ≥ P3model+0.2; model pred-correlation <0.9 pairwise somewhere; held-out test confirms within 20% of val metrics.P5 Serving : ONNX export; signal_engine end-to-end; FastAPI routes (§7); Next.js UI; RR engine wired. GATE: candle-close→frontend <5s p95; 24h soak mem-flat; audit-log 100% matches DB; no NaN probs.P6 MLOps : dashboards; PSI/KL drift; auto-retrain triggers; quarterly-sched job; backtest UI panel. GATE: alert fires in fault-injection drill; retrain round-trip works.Update docs/ROADMAP.md gate-status table after EVERY gate attempt.

7. API CONTRACT (seed docs/CONTRACTS.md with these; amend only there)
REST (prefix /api/v1): GET /health→200 {status} GET /candles/{sym}?interval&limit→[[t,o,h,l,c,v]...] GET /indicators/{sym}?tf→{name:value,...} GET /signal/{sym}?tf→{signal:class,confidence:0..1,probs:{short,long}, reasons:[...],as_of:iso} GET /analysis/{sym}?tf→{signal,indicators,levels:[{price,type,dist_pct}], patterns:[...],rr:{entry,sl,tp1,tp2,ratio}} POST /backtests→{task_id} ; GET /backtests/{id}→status+metricsWS : /ws/prices {sym,t,o,h,l,c,v} | /ws/signals {sig payload on change}

8. CONFIG (.env.example keys; pydantic-settings; NEVER hardcode)
SYMBOL=BTCUSDT TIMEFRAMES=1m,5m,15m,1h,4h,1d SEED=42DATABASE_URL=postgresql+asyncpg://ct:ct@localhost:5432/ctVALKEY_URL=valkey://localhost:6379MINIO_ENDPOINT=localhost:9000 MINIO_USER=ct MINIO_PASS=changemeMLFLOW_TRACKING_URI=http://localhost:5000NEWS_SOURCE=cryptocompare BUDGET_MAX_TRAILS_OPTUNA=200

9. FRONTEND SPEC (web/)
Pages: single-dashboard (/). Components: PriceHeader(tf switcher+coin selBTC pri), MainChart(candles+SMA/EMA toggle+BB+vol), SubCharts(RSI,MACD),SignalBadge(class,color,conf bar),IndicatorPanel(rows w/ above/below tag),SRPanel(list,dist%),PatternPanel(strength stars),RRPanel(auto-filled from/api/v1/analysis, editable inputs,ratio verdict chip),NewsPanel(feed w/sentiment tint). TanStack Query for REST, native WS client for streams.No chart libs other than lightweight-charts@4. TypeScript strict=true.

10. CODE STYLE & QUALITY BAR
ruff clean; type hints on all public fns; docstring: one-line + Args/Returns only when non-obvious. No dead code. No # TODO w/o issue ref.
Pure functions for features/labels/backtest (numpy in/out). IO isolatedto ingestion/writers/builder/services.
Every PR-sized change ships with tests in same commit (pytest mirror dir
factories from tests/conftest.py fake candles fixture, seeded).
Commit style: conventional commits (feat(features): rsi divergence).
Branches: feat/phaseN-task, PR→main after CI green (ruff,pytest).
Errors: log w/ structlog-style kv pairs; fail fast on data-integrityviolations (raise DataIntegrityError).
11. RESPONSE PROTOCOL (apply to EVERY task)
For each user task reply with EXACTLY:

TASK: id+phase+one-line goal
PLAN: ≤6 bullets
FILES: full contents per file created/modified (state path first)
TESTS: test files + what each asserts
VERIFY: shell cmds the user runs
GATE-CHECK: which §6 criteria this advances/what remainsIf task ambiguous → ask ONE clarifying question max, then proceed onreasonable default + note assumption.
12. SELF-AUDIT (before finishing ANY response, verify silently)
□ Inside active phase only? □ New dep flagged + justified?□ Paths match §4 tree exactly? □ PIT-safe (R8)?□ Seeded/deterministic? □ Tests included?□ No execution endpoints (R1)? □ Contracts updated only in docs/CONTRACTS.md?Violation found → fix BEFORE replying.