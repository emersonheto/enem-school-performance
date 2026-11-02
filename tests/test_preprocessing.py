import numpy as np
import pandas as pd
import pytest

from enem_school import config
from enem_school.preprocessing import (
    DROPPED_FEATURES,
    INEP_EXTREME_VALUE,
    N_FOLDS,
    assign_folds,
    build_preprocessor,
    feature_columns,
    mark_extreme_values,
)


def schools_frame(n=40, seed=0):
    rng = np.random.default_rng(seed)
    data = {c: rng.integers(0, 2, n).astype(float) for c in config.INFRASTRUCTURE_FEATURES}
    data.update({c: rng.integers(0, 500, n).astype(float) for c in config.SIZE_FEATURES})
    data.update(
        {
            "TP_DEPENDENCIA": rng.choice([1, 2, 3, 4], n),
            "TP_LOCALIZACAO": rng.choice([1, 2], n),
            "TP_LOCALIZACAO_DIFERENCIADA": rng.choice([0, 1, 2], n).astype(float),
            "CO_REGIAO": rng.choice([1, 2, 3, 4, 5], n),
            "SG_UF": rng.choice(["RS", "SP", "BA"], n),
            "CO_MUNICIPIO": rng.integers(0, 12, n),
        }
    )
    return pd.DataFrame(data)


def test_variant_a_drops_redundant_features_only():
    features = feature_columns("A")

    assert not set(DROPPED_FEATURES) & set(features)
    assert set(features) == set(config.FEATURES) - set(DROPPED_FEATURES)


def test_variants_b_and_c_remove_the_public_private_proxies():
    assert set(feature_columns("A")) - set(feature_columns("B")) == {"TP_DEPENDENCIA"}
    assert set(feature_columns("A")) - set(feature_columns("C")) == {"TP_DEPENDENCIA", "IN_ALIMENTACAO"}


def test_unknown_variant_is_rejected():
    with pytest.raises(ValueError):
        feature_columns("Z")


def test_mark_extreme_values_turns_the_code_into_missing_plus_flag_without_touching_the_input():
    X = pd.DataFrame({"QT_DESKTOP_ALUNO": [10.0, INEP_EXTREME_VALUE, None], "QT_COMP_PORTATIL_ALUNO": [0.0, 3.0, 5.0]})
    original = X.copy()

    result = mark_extreme_values(X)

    assert result["QT_DESKTOP_ALUNO"].tolist()[0] == 10.0
    assert result["QT_DESKTOP_ALUNO"].isna().tolist() == [False, True, True]
    assert result["QT_DESKTOP_ALUNO_extremo"].tolist() == [0, 1, 0]
    assert result["QT_COMP_PORTATIL_ALUNO_extremo"].tolist() == [0, 0, 0]
    pd.testing.assert_frame_equal(X, original)


def test_preprocessor_output_has_no_missing_values_and_one_hot_network_columns():
    schools = schools_frame()
    schools.loc[0, "QT_MAT_MED"] = None
    schools.loc[1, "QT_DESKTOP_ALUNO"] = INEP_EXTREME_VALUE

    preprocessor = build_preprocessor("A").set_output(transform="pandas")
    out = preprocessor.fit_transform(schools[feature_columns("A")])

    assert not out.isna().any().any()
    assert sum("TP_DEPENDENCIA" in c for c in out.columns) == 4
    assert any(c.endswith("QT_DESKTOP_ALUNO_extremo") for c in out.columns)


def test_preprocessor_learns_imputation_and_scale_from_training_rows_only():
    train, test = schools_frame(seed=1), schools_frame(seed=2)
    test["QT_MAT_MED"] = 100_000.0

    preprocessor = build_preprocessor("A").set_output(transform="pandas")
    preprocessor.fit(train[feature_columns("A")])
    scaled_train = preprocessor.transform(train[feature_columns("A")])
    scaled_test = preprocessor.transform(test[feature_columns("A")])

    count_column = next(c for c in scaled_train.columns if c.endswith("QT_MAT_MED"))
    assert scaled_train[count_column].mean() == pytest.approx(0, abs=1e-9)
    assert scaled_test[count_column].min() > 3


def test_assign_folds_keeps_each_municipality_in_one_fold_and_is_reproducible():
    schools = schools_frame(n=200)

    folds = assign_folds(schools)

    assert sorted(folds.unique()) == list(range(N_FOLDS))
    assert schools.groupby("CO_MUNICIPIO")["CO_MUNICIPIO"].size().index.size == 12
    assert (folds.groupby(schools["CO_MUNICIPIO"]).nunique() == 1).all()
    pd.testing.assert_series_equal(folds, assign_folds(schools))
