"""Shared nested cross-validation: every algorithm is tuned and evaluated the same way."""

import time

import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import Pipeline

from enem_school import config
from enem_school.preprocessing import N_REPEATS, assign_folds, build_preprocessor, feature_columns

INNER_FOLDS = 3
PARAM_PREFIX = "regressor__"


def _build_model(regressor, variant: str) -> Pipeline:
    return Pipeline([("preprocess", build_preprocessor(variant)), ("regressor", clone(regressor))])


def _score(y_true, predictions) -> dict:
    return {
        "rmse": root_mean_squared_error(y_true, predictions),
        "mae": mean_absolute_error(y_true, predictions),
        "r2": r2_score(y_true, predictions),
    }


def nested_cv(
    regressor, param_grid: dict, schools: pd.DataFrame, variant: str = "A", *, repeats: int = N_REPEATS, n_jobs: int | None = None
) -> pd.DataFrame:
    """Nested CV: the outer loop estimates performance, the inner loop (GridSearchCV) picks hyperparameters.

    The outer loop is repeated `repeats` times, each with its own municipality shuffle (assign_folds). For each
    outer fold, the grid search sees only the outer-train schools, and its own 3 folds also keep each
    municipality in a single side. The best model, refitted on all outer-train schools, is scored once on the
    outer-test schools. param_grid keys are the regressor's own parameter names.
    Returns one row per repetition and outer fold: repeticao, dobra, rmse, mae, r2, melhores_parametros.
    """
    X = schools[feature_columns(variant)]
    y = schools[config.TARGET]
    groups = schools["CO_MUNICIPIO"]
    prefixed_grid = {PARAM_PREFIX + name: values for name, values in param_grid.items()}

    rows = []
    for repeat in range(repeats):
        folds = assign_folds(schools, repeat)
        for fold in sorted(folds.unique()):
            train = (folds != fold).to_numpy()
            test = ~train

            search = GridSearchCV(
                _build_model(regressor, variant),
                prefixed_grid,
                scoring="neg_root_mean_squared_error",
                refit=True,
                cv=GroupKFold(n_splits=INNER_FOLDS, shuffle=True, random_state=config.SEED),
                n_jobs=n_jobs,
            )
            search.fit(X[train], y[train], groups=groups[train].to_numpy())

            rows.append({
                "repeticao": repeat + 1,
                "dobra": int(fold) + 1,
                **_score(y[test], search.predict(X[test])),
                "melhores_parametros": {name.removeprefix(PARAM_PREFIX): value for name, value in search.best_params_.items()},
            })
    return pd.DataFrame(rows)


def spot_check(regressors: dict, schools: pd.DataFrame, variant: str = "A", *, repeats: int = N_REPEATS) -> pd.DataFrame:
    """Quick comparison of several algorithms with default settings (no tuning).

    The folds of each repetition are computed once and shared by all algorithms, so they are compared on
    identical train/test splits. Returns one row per algorithm, repetition and outer fold:
    algoritmo, repeticao, dobra, rmse, mae, r2, segundos_treino (time spent fitting).
    """
    X = schools[feature_columns(variant)]
    y = schools[config.TARGET]

    rows = []
    for repeat in range(repeats):
        folds = assign_folds(schools, repeat)
        for fold in sorted(folds.unique()):
            train = (folds != fold).to_numpy()
            test = ~train
            for name, regressor in regressors.items():
                model = _build_model(regressor, variant)
                start = time.perf_counter()
                model.fit(X[train], y[train])
                fit_seconds = time.perf_counter() - start

                rows.append({
                    "algoritmo": name,
                    "repeticao": repeat + 1,
                    "dobra": int(fold) + 1,
                    **_score(y[test], model.predict(X[test])),
                    "segundos_treino": fit_seconds,
                })
    return pd.DataFrame(rows)
