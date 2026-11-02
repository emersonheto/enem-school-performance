import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.dummy import DummyRegressor
from sklearn.model_selection import GroupKFold
from sklearn.neighbors import KNeighborsRegressor

from enem_school import evaluation
from enem_school.evaluation import nested_cv, spot_check
from enem_school.preprocessing import N_FOLDS
from test_preprocessing import schools_frame

PARAM_GRID = {"n_neighbors": [3, 5]}


def schools_with_target(n=120):
    schools = schools_frame(n=n, seed=1)
    schools["CO_MUNICIPIO"] = np.random.default_rng(2).integers(0, 20, n)
    schools["nota_media"] = 500 + 50 * schools["IN_BIBLIOTECA"] + np.random.default_rng(3).normal(0, 10, n)
    return schools


TRAIN_LOG = []


class LoggingMean(RegressorMixin, BaseEstimator):
    """Predicts the training mean and logs which training targets it saw, tagged with its own name."""

    def __init__(self, name="a"):
        self.name = name

    def fit(self, X, y):
        TRAIN_LOG.append((self.name, round(float(np.sum(y)), 6)))
        self.mean_ = float(np.mean(y))
        return self

    def predict(self, X):
        return np.full(len(X), self.mean_)


def test_nested_cv_returns_one_row_per_repetition_and_outer_fold_with_finite_metrics_and_grid_params():
    result = nested_cv(KNeighborsRegressor(), PARAM_GRID, schools_with_target(), repeats=2)

    assert result["repeticao"].tolist() == [1] * N_FOLDS + [2] * N_FOLDS
    assert result["dobra"].tolist() == list(range(1, N_FOLDS + 1)) * 2
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

    nested_cv(KNeighborsRegressor(), PARAM_GRID, schools_with_target(), repeats=2)

    assert recorded
    assert all(train.isdisjoint(validation) for train, validation in recorded)


def test_nested_cv_is_deterministic():
    schools = schools_with_target()

    first = nested_cv(KNeighborsRegressor(), PARAM_GRID, schools, repeats=2)
    second = nested_cv(KNeighborsRegressor(), PARAM_GRID, schools, repeats=2)

    assert first.equals(second)


def test_spot_check_returns_one_row_per_algorithm_repetition_and_fold_with_finite_metrics():
    regressors = {"Media": DummyRegressor(strategy="mean"), "kNN": KNeighborsRegressor()}

    result = spot_check(regressors, schools_with_target(), repeats=2)

    assert list(result.columns) == ["algoritmo", "repeticao", "dobra", "rmse", "mae", "r2", "segundos_treino"]
    assert len(result) == len(regressors) * 2 * N_FOLDS
    assert set(result["algoritmo"]) == set(regressors)
    assert np.isfinite(result[["rmse", "mae", "r2", "segundos_treino"]].to_numpy()).all()


def test_spot_check_gives_every_algorithm_the_same_folds_within_a_repetition():
    TRAIN_LOG.clear()

    spot_check({"a": LoggingMean("a"), "b": LoggingMean("b")}, schools_with_target(), repeats=2)

    seen = {}
    for name, fingerprint in TRAIN_LOG:
        seen.setdefault(name, []).append(fingerprint)
    assert seen["a"] == seen["b"]
    assert len(set(seen["a"])) == 2 * N_FOLDS
