"""Shared nested cross-validation: every algorithm is tuned and evaluated the same way."""

import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import Pipeline

from enem_school import config
from enem_school.preprocessing import assign_folds, build_preprocessor, feature_columns

TARGET = "nota_media"
INNER_FOLDS = 3
PARAM_PREFIX = "regressor__"


def nested_cv(regressor, param_grid: dict, schools: pd.DataFrame, variant: str = "A", *, n_jobs: int | None = None) -> pd.DataFrame:
    """Nested CV: the outer loop estimates performance, the inner loop (GridSearchCV) picks hyperparameters.

    Outer folds come from assign_folds. For each one, the grid search sees only the outer-train schools, and its
    own 3 folds also keep each municipality in a single side. The best model, refitted on all outer-train
    schools, is scored once on the outer-test schools. param_grid keys are the regressor's own parameter names.
    Returns one row per outer fold: dobra, rmse, mae, r2, melhores_parametros.
    """
    X = schools[feature_columns(variant)]
    y = schools[TARGET]
    groups = schools["CO_MUNICIPIO"]
    folds = assign_folds(schools)
    prefixed_grid = {PARAM_PREFIX + name: values for name, values in param_grid.items()}

    rows = []
    for fold in sorted(folds.unique()):
        train = (folds != fold).to_numpy()
        test = ~train

        model = Pipeline([("preprocess", build_preprocessor(variant)), ("regressor", clone(regressor))])
        search = GridSearchCV(
            model,
            prefixed_grid,
            scoring="neg_root_mean_squared_error",
            refit=True,
            cv=GroupKFold(n_splits=INNER_FOLDS, shuffle=True, random_state=config.SEED),
            n_jobs=n_jobs,
        )
        search.fit(X[train], y[train], groups=groups[train].to_numpy())

        predictions = search.predict(X[test])
        rows.append({
            "dobra": int(fold) + 1,
            "rmse": root_mean_squared_error(y[test], predictions),
            "mae": mean_absolute_error(y[test], predictions),
            "r2": r2_score(y[test], predictions),
            "melhores_parametros": {name.removeprefix(PARAM_PREFIX): value for name, value in search.best_params_.items()},
        })
    return pd.DataFrame(rows)
