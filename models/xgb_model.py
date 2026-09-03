"""XGBoost classifier used by the P3 baseline pipeline."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss
from xgboost import XGBClassifier
from xgboost import XGBRegressor

from backtest.metrics import max_drawdown, profit_factor, sharpe_ratio, signal_coverage


def _strategy_objective(signals: Sequence[float], returns: Sequence[float]) -> float:
    """Minimize a strategy-style validation loss that rewards Sharpe and profit factor."""
    if len(signals) != len(returns):
        raise ValueError("signals and returns must have equal lengths")
    if len(signals) == 0:
        raise ValueError("signals and returns must not be empty")

    signal_array = np.asarray(list(float(value) for value in signals), dtype=float)
    return_array = np.asarray(list(float(value) for value in returns), dtype=float)
    if np.all(signal_array == 0.0):
        return 1e9

    strategy_returns = return_array * signal_array
    sharpe = sharpe_ratio(strategy_returns.tolist())
    drawdown = max_drawdown(strategy_returns.tolist())
    pf = profit_factor(strategy_returns.tolist())
    coverage = signal_coverage(signal_array.tolist())
    pf_value = min(float(np.isfinite(pf) and pf or 0.0), 10.0)
    return float(-(sharpe + 0.7 * pf_value - 2.5 * drawdown + 0.25 * coverage))


class XGBoostModel:
    """Small sklearn-compatible wrapper with stable class-probability ordering."""

    def __init__(self, **params: Any) -> None:
        defaults: dict[str, Any] = {
            "objective": "multi:softprob",
            "num_class": 3,
            "eval_metric": "mlogloss",
            "n_estimators": 300,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "n_jobs": 1,
        }
        defaults.update(params)
        self.model = XGBClassifier(**defaults)
        self.classes_ = pd.Index([-1, 0, 1], dtype="int64")

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        sample_weight: pd.Series | None = None,
    ) -> "XGBoostModel":
        encoded = y.astype(int).map({-1: 0, 0: 1, 1: 2})
        if encoded.isna().any():
            raise ValueError("y must contain only labels -1, 0, and 1")
        self.model.fit(X, encoded, sample_weight=sample_weight)
        return self

    def predict(
        self,
        X: pd.DataFrame,
        confidence_threshold: float = 0.0,
        min_margin: float = 0.0,
        top_k_fraction: float | None = None,
    ) -> pd.Series:
        probabilities = self.predict_proba(X)
        if top_k_fraction is not None:
            if not 0.0 < top_k_fraction <= 1.0:
                raise ValueError("top_k_fraction must be in the (0, 1] interval")
            score = probabilities[1] - probabilities[-1]
            take = max(1, int(round(len(X) * top_k_fraction)))
            ranked = score.abs().nlargest(take).index
            signal = pd.Series(0.0, index=X.index, name="prediction")
            signal.loc[ranked] = np.where(score.loc[ranked] >= 0.0, 1.0, -1.0)
            return signal

        if confidence_threshold <= 0.0 and min_margin <= 0.0:
            return pd.Series(self.model.predict(X), index=X.index, name="prediction").map(
                {0: -1, 1: 0, 2: 1}
            )

        probability_matrix = probabilities.to_numpy(dtype=float)
        class_index = probability_matrix.argmax(axis=1)
        top_confidence = probability_matrix[np.arange(len(probability_matrix)), class_index]
        second_confidence = np.partition(probability_matrix, -2, axis=1)[:, -2]
        signal = np.zeros(len(probability_matrix), dtype=float)
        mask = (top_confidence >= confidence_threshold) & ((top_confidence - second_confidence) >= min_margin)
        signal[mask] = probabilities.columns[class_index[mask]].to_numpy(dtype=float)
        return pd.Series(signal, index=X.index, name="prediction")

    def predict_proba(self, X: pd.DataFrame) -> pd.DataFrame:
        probabilities = self.model.predict_proba(X)
        return pd.DataFrame(probabilities, index=X.index, columns=self.classes_)


class XGBoostReturnRanker:
    """Predict future returns and expose only the strongest directional ranks."""

    def __init__(self, **params: Any) -> None:
        defaults: dict[str, Any] = {
            "objective": "reg:squarederror",
            "eval_metric": "rmse",
            "n_estimators": 300,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "n_jobs": 1,
        }
        defaults.update(params)
        self.model = XGBRegressor(**defaults)

    def fit(
        self,
        X: pd.DataFrame,
        returns: pd.Series,
        sample_weight: pd.Series | None = None,
    ) -> "XGBoostReturnRanker":
        self.model.fit(X, returns.astype(float), sample_weight=sample_weight)
        return self

    def predict_score(self, X: pd.DataFrame) -> pd.Series:
        return pd.Series(self.model.predict(X), index=X.index, name="return_score")

    def predict(
        self,
        X: pd.DataFrame,
        top_k_fraction: float = 0.10,
        position_size: float = 0.50,
    ) -> pd.Series:
        if not 0.0 < top_k_fraction <= 1.0:
            raise ValueError("top_k_fraction must be in the (0, 1] interval")
        if not 0.0 < position_size <= 1.0:
            raise ValueError("position_size must be in the (0, 1] interval")
        scores = self.predict_score(X)
        count = max(1, int(round(len(scores) * top_k_fraction)))
        selected = scores.abs().nlargest(count).index
        signal = pd.Series(0.0, index=X.index, name="prediction")
        signal.loc[selected] = np.sign(scores.loc[selected]) * position_size
        return signal


def fit(
    X: pd.DataFrame,
    y: pd.Series,
    w: pd.Series | None = None,
    **params: Any,
) -> XGBoostModel:
    """Fit and return an XGBoost classifier."""
    return XGBoostModel(**params).fit(X, y, sample_weight=w)


def predict_proba(model: XGBoostModel, X: pd.DataFrame) -> pd.DataFrame:
    """Return class probabilities in the fitted model's class order."""
    return model.predict_proba(X)


def tune(
    X: pd.DataFrame,
    y: pd.Series,
    sample_weight: pd.Series | None = None,
    validation_returns: pd.Series | None = None,
    n_trials: int = 200,
    seed: int = 42,
) -> dict[str, Any]:
    """Tune the classifier on a chronological validation split with Optuna."""
    if n_trials < 1:
        raise ValueError("n_trials must be positive")
    if len(X) != len(y):
        raise ValueError("X and y must have equal lengths")
    if validation_returns is not None and len(validation_returns) != len(X):
        raise ValueError("validation_returns must align with X and y")
    split = int(len(X) * 0.8)
    if split < 1 or split >= len(X):
        raise ValueError("X must contain at least two rows")
    import optuna

    X_train, X_valid = X.iloc[:split], X.iloc[split:]
    y_train, y_valid = y.iloc[:split], y.iloc[split:]
    weights_train = sample_weight.iloc[:split] if sample_weight is not None else None
    valid_returns = validation_returns.iloc[split:] if validation_returns is not None else None

    def objective(trial: optuna.Trial) -> float:
        model = XGBoostModel(
            max_depth=trial.suggest_int("max_depth", 3, 10),
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            min_child_weight=trial.suggest_float("min_child_weight", 1.0, 20.0),
            subsample=trial.suggest_float("subsample", 0.6, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.6, 1.0),
            n_estimators=trial.suggest_int("n_estimators", 100, 600),
            random_state=seed,
        ).fit(X_train, y_train, sample_weight=weights_train)
        if valid_returns is not None:
            signal = model.predict(
                X_valid,
                top_k_fraction=0.10,
            ).to_numpy(dtype=float)
            return _strategy_objective(signal, valid_returns.to_numpy(dtype=float))
        probabilities = model.predict_proba(X_valid)
        return float(log_loss(y_valid, probabilities.to_numpy(), labels=[-1, 0, 1]))

    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction="minimize", sampler=sampler)
    study.optimize(objective, n_trials=n_trials)
    return {"best_params": study.best_params, "best_value": float(study.best_value)}


def tune_return_ranker(
    X: pd.DataFrame,
    returns: pd.Series,
    sample_weight: pd.Series | None = None,
    n_trials: int = 200,
    seed: int = 42,
) -> dict[str, Any]:
    """Tune a return ranker on chronological strategy validation returns."""
    if n_trials < 1:
        raise ValueError("n_trials must be positive")
    if len(X) != len(returns):
        raise ValueError("X and returns must have equal lengths")
    split = int(len(X) * 0.8)
    if split < 1 or split >= len(X):
        raise ValueError("X must contain at least two rows")
    import optuna

    X_train, X_valid = X.iloc[:split], X.iloc[split:]
    y_train, y_valid = returns.iloc[:split], returns.iloc[split:]
    weights_train = sample_weight.iloc[:split] if sample_weight is not None else None

    def objective(trial: optuna.Trial) -> float:
        model = XGBoostReturnRanker(
            max_depth=trial.suggest_int("max_depth", 3, 10),
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            min_child_weight=trial.suggest_float("min_child_weight", 1.0, 20.0),
            subsample=trial.suggest_float("subsample", 0.6, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.6, 1.0),
            n_estimators=trial.suggest_int("n_estimators", 100, 600),
            random_state=seed,
        ).fit(X_train, y_train, sample_weight=weights_train)
        signal = model.predict(
            X_valid,
            top_k_fraction=0.10,
            position_size=0.50,
        ).to_numpy(dtype=float)
        return _strategy_objective(signal, y_valid.to_numpy(dtype=float))

    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction="minimize", sampler=sampler)
    study.optimize(objective, n_trials=n_trials)
    return {"best_params": study.best_params, "best_value": float(study.best_value)}


def log_metrics_to_mlflow(
    run_name: str,
    metrics: dict[str, float],
    tracking_uri: str,
    experiment_name: str = "cryptoterminal-p3",
) -> None:
    """Log baseline or model metrics to the configured MLflow tracking server."""
    import mlflow

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=run_name):
        mlflow.log_metrics({key: float(value) for key, value in metrics.items()})
