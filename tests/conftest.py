import os

os.environ.setdefault('SEED', '42')

import pandas as pd
import pytest


@pytest.fixture
def fake_candles():
    idx = pd.date_range('2024-01-01', periods=120, freq='1h', tz='UTC')
    df = pd.DataFrame(
        {
            'time': idx.view('int64') // 10**9 * 1000,
            'open': 100.0,
            'high': 101.0,
            'low': 99.5,
            'close': 100.5,
            'volume': 1000.0,
        }
    )
    return df
