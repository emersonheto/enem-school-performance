import numpy as np
import pytest
from sklearn.model_selection import GroupKFold
from sklearn.neighbors import KNeighborsRegressor

from enem_school import evaluation
from enem_school.evaluation import nested_cv
from enem_school.preprocessing import N_FOLDS
from test_preprocessing import schools_frame

PARAM_GRID = {"n_neighbors": [3, 5]}


def schools_with_target(n=120):
    schools = schools_frame(n=n, seed=1)
    schools["CO_MUNICIPIO"] = np.random.default_rng(2).integers(0, 20, n)
    schools["nota_media"] = 500 + 50 * schools["IN_BIBLIOTECA"] + np.random.default_rng(3).normal(0, 10, n)
    return schools


def test_nested_cv_returns_one_row_per_outer_fold_with_finite_metrics_and_grid_params():
    result = nested_cv(KNeighborsRegressor(), PARAM_GRID, schools_with_target())

    assert result["dobra"].tolist() == list(range(1, N_FOLDS + 1))
    assert np.isfinite(result[["rmse", "mae", "r2"]].to_numpy()).all()
    assert all(set(params) == {"n_neighbors"} for params in result["melhores_parametros"])
    assert all(params["n_neighbors"] in PARAM_GRID["n_neighbors"] for params in result["melhores_parametros"])


def test_inner_search_never_splits_a_municipality_between_train_and_validation(monkeypatch):
    recorded = []

    class RecordingGroupKFold(GroupKFold):
        def split(self, X, y=None, groups=None):
            for train, validation in super().split(X, y, groups):
                recorded.append((set(groups[train]), set(groups[validation])))
                yield train, validation

    monkeypatch.setattr(evaluation, "GroupKFold", RecordingGroupKFold)

    nested_cv(KNeighborsRegressor(), PARAM_GRID, schools_with_target())

    assert recorded
    assert all(train.isdisjoint(validation) for train, validation in recorded)


def test_nested_cv_is_deterministic():
    schools = schools_with_target()

    first = nested_cv(KNeighborsRegressor(), PARAM_GRID, schools)
    second = nested_cv(KNeighborsRegressor(), PARAM_GRID, schools)

    assert first.equals(second)
