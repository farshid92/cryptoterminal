"""Walk-forward evaluation harness."""

from __future__ import annotations

import pandas as pd


def walk_forward(model_factory, data, train_w, test_w):
    """Evaluate a model over expanding walk-forward splits.

    Args:
        model_factory: callable returning a fitted model with fit(X, y) and predict(X).
        data: pandas DataFrame containing a target column and feature columns.
        train_w: training window size.
        test_w: test window size.

    Returns:
        A DataFrame with OOS predictions and actuals for each walk-forward split.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError('data must be a pandas DataFrame')
    if 'target' not in data.columns:
        raise ValueError('data must contain a target column')
    if train_w <= 0 or test_w <= 0:
        raise ValueError('train_w and test_w must be positive integers')

    frames: list[pd.DataFrame] = []
    total_rows = len(data)
    index = 0

    while index + train_w + test_w <= total_rows:
        train_slice = data.iloc[index : index + train_w].copy()
        test_slice = data.iloc[index + train_w : index + train_w + test_w].copy()

        model = model_factory()
        feature_columns = [column for column in train_slice.columns if column != 'target']
        X_train = train_slice[feature_columns]
        y_train = train_slice['target']
        X_test = test_slice[feature_columns]

        model.fit(X_train, y_train)
        predictions = model.predict(X_test)

        split_df = pd.DataFrame(
            {
                'split': index,
                'row_index': test_slice.index,
                'actual': test_slice['target'].to_numpy(),
                'prediction': predictions,
            }
        )
        frames.append(split_df)
        index += test_w

    if not frames:
        return pd.DataFrame(columns=['split', 'row_index', 'actual', 'prediction'])

    return pd.concat(frames, ignore_index=True)
