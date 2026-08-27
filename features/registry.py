"""Feature registry source of truth."""

FEATURE_LIST = [
    "return_1",
    "return_3",
    "return_6",
    "return_12",
    "return_24",
    "sma_10",
    "sma_20",
    "sma_50",
    "ema_12",
    "ema_26",
    "ema_50",
    "ema_200",
    "macd",
    "macd_signal",
    "macd_hist",
    "rsi_14",
    "stoch_k",
    "stoch_d",
    "bb_mid",
    "bb_upper",
    "bb_lower",
    "bb_width",
    "atr_14",
    "true_range",
    "adx_14",
    "plus_di_14",
    "minus_di_14",
    "obv",
    "volume_sma_20",
    "volume_ratio",
    "vwap",
    "hl_range",
    "oc_change",
    "body_ratio",
    "upper_wick_ratio",
    "lower_wick_ratio",
    "rolling_high_20",
    "rolling_low_20",
    "distance_high_20",
    "distance_low_20",
    "close_zscore_20",
    "volatility_20",
    "trend_slope_20",
]


def register_feature(name: str) -> str:
    """Register a feature name once and return it."""
    if name not in FEATURE_LIST:
        FEATURE_LIST.append(name)
    return name
