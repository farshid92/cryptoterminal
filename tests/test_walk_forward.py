import pandas as pd

from backtest.walk_forward import walk_forward


class SimpleModel:
    def fit(self, X, y):
        self.mean_ = float(y.mean())
        return self

    def predict(self, X):
        return [self.mean_] * len(X)


def test_walk_forward_returns_oos_predictions_for_each_split():
    data = pd.DataFrame(
        {
            'feature_a': list(range(12)),
            'feature_b': list(range(12, 24)),
            'target': [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
        }
    )

    out = walk_forward(SimpleModel, data, train_w=4, test_w=2)

    assert not out.empty
    assert set(out.columns) == {'split', 'row_index', 'actual', 'prediction'}
    assert len(out) == 8
    assert out['prediction'].nunique() == 1
