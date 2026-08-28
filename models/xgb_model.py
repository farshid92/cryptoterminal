"""XGBoost classifier used by the P3 baseline pipeline."""

from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.metrics import log_loss
from xgboost import XGBClassifier


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

    def predict(self, X: pd.DataFrame) -> pd.Series:
        return pd.Series(self.model.predict(X), index=X.index, name="prediction").map(
            {0: -1, 1: 0, 2: 1}
        )

    def predict_proba(self, X: pd.DataFrame) -> pd.DataFrame:
        probabilities = self.model.predict_proba(X)
        return pd.DataFrame(probabilities, index=X.index, columns=self.classes_)


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
    n_trials: int = 200,
    seed: int = 42,
) -> dict[str, Any]:
    """Tune the classifier on a chronological validation split with Optuna."""
    if n_trials < 1:
        raise ValueError("n_trials must be positive")
    if len(X) != len(y):
        raise ValueError("X and y must have equal lengths")
    split = int(len(X) * 0.8)
    if split < 1 or split >= len(X):
        raise ValueError("X must contain at least two rows")
    import optuna

    X_train, X_valid = X.iloc[:split], X.iloc[split:]
    y_train, y_valid = y.iloc[:split], y.iloc[split:]
    weights_train = sample_weight.iloc[:split] if sample_weight is not None else None

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
        probabilities = model.predict_proba(X_valid)
        return float(log_loss(y_valid, probabilities.to_numpy(), labels=[-1, 0, 1]))

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
