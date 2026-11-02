"""Shared preprocessing: every model in the project uses the same features, transformer and folds."""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from enem_school import config

# Censo data dictionary: "88888 - registro com marcação de valor extremo".
INEP_EXTREME_VALUE = 88888
EXTREME_CODED_FEATURES = ["QT_DESKTOP_ALUNO", "QT_COMP_PORTATIL_ALUNO"]
EXTREME_FLAG_SUFFIX = "_extremo"
EXTREME_FLAGS = [column + EXTREME_FLAG_SUFFIX for column in EXTREME_CODED_FEATURES]

# CO_REGIAO is implied by SG_UF; QT_TUR_MED repeats QT_MAT_MED (Spearman 0.96).
DROPPED_FEATURES = ["CO_REGIAO", "QT_TUR_MED"]

# A: all features. B: without the public/private network. C: also without school meals (PNAE, a public-school proxy).
VARIANTS = {
    "A": [],
    "B": ["TP_DEPENDENCIA"],
    "C": ["TP_DEPENDENCIA", "IN_ALIMENTACAO"],
}

N_FOLDS = 5
N_REPEATS = 3


def feature_columns(variant: str = "A") -> list[str]:
    """Model features for a variant, in config.FEATURES order."""
    if variant not in VARIANTS:
        raise ValueError(f"Unknown variant {variant}, expected one of {list(VARIANTS.keys())}")
    excluded = DROPPED_FEATURES + VARIANTS[variant]
    return [column for column in config.FEATURES if column not in excluded]


def mark_extreme_values(X: pd.DataFrame) -> pd.DataFrame:
    """Return a copy where 88888 becomes missing and each EXTREME_CODED_FEATURES column gets a 0/1 flag column."""
    X = X.copy()
    for column in EXTREME_CODED_FEATURES:
        is_extreme = X[column] == INEP_EXTREME_VALUE
        X[column + EXTREME_FLAG_SUFFIX] = is_extreme.astype(int)
        X[column] = X[column].mask(is_extreme)
    return X


def _extreme_feature_names(transformer, input_features):
    return [*input_features, *EXTREME_FLAGS]


def build_preprocessor(variant: str = "A") -> Pipeline:
    """Pipeline: mark_extreme_values, then impute, log1p + scale counts, keep binaries, one-hot categoricals.

    Everything that learns from data (medians, modes, means, scales, categories) is fitted inside the
    pipeline, so cross-validation fits it on the training folds only.
    """
    features = feature_columns(variant)
    counts = [c for c in config.SIZE_FEATURES if c in features]
    binaries = [c for c in config.INFRASTRUCTURE_FEATURES if c in features] + EXTREME_FLAGS
    categorical = [c for c in config.CATEGORICAL_FEATURES if c in features]

    count_steps = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("log1p", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
        ("scale", StandardScaler()),
    ])
    binary_steps = SimpleImputer(strategy="most_frequent")
    categorical_steps = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent")),
        ("one_hot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    columns = ColumnTransformer([
        ("counts", count_steps, counts),
        ("binaries", binary_steps, binaries),
        ("categorical", categorical_steps, categorical),
    ])
    return Pipeline([
        ("extreme_values", FunctionTransformer(mark_extreme_values, feature_names_out=_extreme_feature_names)),
        ("columns", columns),
    ])


def assign_folds(schools: pd.DataFrame, repeat: int = 0) -> pd.Series:
    """Fold number (0..N_FOLDS-1) for each school, grouping by municipality.

    Each repetition shuffles the municipalities differently (seed config.SEED + repeat); repeat=0 is the
    original single partition.
    """
    folds = pd.Series(-1, index=schools.index, name="fold")
    splitter = GroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=config.SEED + repeat)
    for fold, (_, test_rows) in enumerate(splitter.split(schools, groups=schools["CO_MUNICIPIO"])):
        folds.iloc[test_rows] = fold
    return folds
