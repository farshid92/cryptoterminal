import pandas as pd
import pytest

from labeling.triple_barrier import triple_barrier


def test_triple_barrier_assigns_first_touch_and_return():
    candles = pd.DataFrame({"close": [100.0, 101.0, 104.0, 98.0, 100.0]})

    result = triple_barrier(candles, atr=2.0, horizon=3, tp_m=2.0, sl_m=1.0)

    assert result.loc[0, "label"] == 1
    assert result.loc[0, "touch_i"] == 2
    assert result.loc[0, "ret"] == pytest.approx(0.04)
    assert result.loc[1, "label"] == -1
    assert result.loc[1, "touch_i"] == 3


def test_triple_barrier_expires_neutral_at_horizon():
    candles = pd.DataFrame({"close": [100.0, 100.5, 100.2, 100.4]})

    result = triple_barrier(candles, atr=10.0, horizon=2)

    assert result["label"].tolist() == [0, 0, 0, 0]
    assert result["touch_i"].tolist() == [2, 3, 3, 3]
