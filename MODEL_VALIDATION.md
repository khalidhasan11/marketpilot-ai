# Model Validation — MarketPilot AI

## Status: UNVALIDATED (by design and by evidence)
No model in this system has demonstrated an out-of-sample edge. `confidence_level`
is hard-set to `UNVALIDATED` in every prediction until the criteria below are met.

## Prior evidence (predecessor prototype, honest in-sample backtest)
- BTC/USDT 5m directional: **51.74% win rate** vs **54.05% break-even** (85% payout)
  → **−15.95 units over 373 trades — no edge.**
- BTC 15m: 56.0% (200 trades) — in-sample, overfitting caution applies.
- ETH: ≈43.6% on both horizons — clearly no edge.
- MarketPilot's own first live-window backtest (500 × 5m candles, EMA-cross strategy,
  R:R 3:1, fees included): 5 decided trades, 20% win rate, profit factor 0.34,
  expectancy −$89.03 on $10,000 at 1% risk. Small sample — reported, not hidden.

## Validation protocol (required before any accuracy claim)
1. Chronological train/test split only — never shuffled (leakage prevention).
2. Walk-forward folds in `backtest.walk_forward`; no parameter tuning on test folds.
3. Forward paper trading: record every prediction + outcome in `model_predictions` /
   `signal_outcomes` for **weeks**, across regimes.
4. Report Brier score, log-loss-style calibration, win rate, profit factor, expectancy,
   max drawdown — by asset, timeframe, regime and model version.
5. Only after ≥200 out-of-sample decided signals with profit factor > 1 net of fees
   may `confidence_level` be revisited — and even then, past performance ≠ future results.

## Anti-overfitting rules enforced in code
- Indicators use closed candles only; backtest enters at the *next* candle open.
- Fees (0.1%) and slippage are on by default; break-even maths is printed next to results.
- Losing results are stored and displayed identically to winning ones.
