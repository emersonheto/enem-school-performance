"""Shared evaluation: every algorithm is tuned, evaluated and compared the same way."""

import itertools
import time

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import Pipeline

from enem_school import config
from enem_school.preprocessing import N_REPEATS, assign_folds, build_preprocessor, feature_columns

INNER_FOLDS = 3
PARAM_PREFIX = "regressor__"

# Demšar (2006), Table 5: Nemenyi q_alpha for alpha = 0.05 and k = 2..10 algorithms.
Q_ALPHA_NEMENYI_005 = {2: 1.960, 3: 2.343, 4: 2.569, 5: 2.728, 6: 2.850, 7: 2.949, 8: 3.031, 9: 3.102, 10: 3.164}


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


def compare_algorithms(results: pd.DataFrame) -> dict:
    """Friedman test over the RMSE of each (repeticao, dobra) block, then the Nemenyi post-hoc (Demšar, 2006).

    Ranks are computed inside each block (1 = lowest RMSE). Two algorithms differ when their average ranks are at
    least the critical difference apart. Returns friedman_statistic, friedman_p, ranks, critical_difference and
    significant_pairs.
    """
    rmse = results.pivot_table(index=["repeticao", "dobra"], columns="algoritmo", values="rmse")
    friedman = stats.friedmanchisquare(*[rmse[name] for name in rmse.columns])
    ranks = rmse.rank(axis=1).mean().sort_values().rename("posto médio")

    k, n_blocks = rmse.shape[1], rmse.shape[0]
    critical_difference = Q_ALPHA_NEMENYI_005[k] * np.sqrt(k * (k + 1) / (6 * n_blocks))
    pairs = pd.DataFrame(
        [{"A": a, "B": b, "diferença de postos": ranks[b] - ranks[a]} for a, b in itertools.combinations(ranks.index, 2)]
    )
    significant = pairs[pairs["diferença de postos"] >= critical_difference]
    return {
        "friedman_statistic": friedman.statistic,
        "friedman_p": friedman.pvalue,
        "ranks": ranks,
        "critical_difference": critical_difference,
        "significant_pairs": significant.sort_values("diferença de postos", ascending=False).reset_index(drop=True),
    }
