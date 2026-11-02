"""Descriptive summaries of the school table used by scripts/eda.py."""

import pandas as pd

from enem_school import config

TARGET = "nota_media"

# Censo data dictionary: "88888 - registro com marcação de valor extremo" (e.g. more than 4 computers per 3 enrolments).
INEP_EXTREME_VALUE = 88888

DEPENDENCIA_LABELS = {1: "Federal", 2: "Estadual", 3: "Municipal", 4: "Privada"}
REGIAO_LABELS = {1: "Norte", 2: "Nordeste", 3: "Sudeste", 4: "Sul", 5: "Centro-Oeste"}
LOCALIZACAO_LABELS = {1: "Urbana", 2: "Rural"}


def find_inconsistencies(schools: pd.DataFrame) -> pd.DataFrame:
    """Count schools breaking each plausibility rule; a missing value never counts as a violation."""
    enrolment = schools["QT_MAT_MED"]
    rules = {
        "high school enrolment > 0 but no high school teachers": (enrolment > 0) & (schools["QT_DOC_MED"] == 0),
        "high school enrolment is zero": enrolment == 0,
        "air-conditioned rooms > rooms in use": schools["QT_SALAS_UTILIZA_CLIMATIZADAS"]
        > schools["QT_SALAS_UTILIZADAS"],
        "broadband without internet": (schools["IN_BANDA_LARGA"] == 1) & (schools["IN_INTERNET"] == 0),
        "ENEM candidates > high school enrolment": schools["n_alunos"] > enrolment,
        "INEP extreme-value code 88888 in a count": (
            schools[[c for c in config.SIZE_FEATURES if c in schools]] == INEP_EXTREME_VALUE
        ).any(axis=1),
    }
    return pd.DataFrame({"rule": list(rules), "schools": [int(mask.sum()) for mask in rules.values()]})


def feature_types() -> pd.DataFrame:
    groups = [
        ("Infraestrutura (binária, IN_*)", config.INFRASTRUCTURE_FEATURES),
        ("Tamanho e recursos (contagem, QT_*)", config.SIZE_FEATURES),
        ("Rede e localização (categórica)", config.CATEGORICAL_FEATURES),
    ]
    return pd.DataFrame({"grupo": [g for g, _ in groups], "atributos": [len(c) for _, c in groups]})


def missing_rates(schools: pd.DataFrame) -> pd.Series:
    return schools[config.FEATURES].isna().mean().sort_values(ascending=False, kind="stable")


def binary_prevalence(schools: pd.DataFrame) -> pd.Series:
    """Share of schools with each binary feature equal to 1, ignoring missing values."""
    return schools[config.INFRASTRUCTURE_FEATURES].mean().sort_values(kind="stable")


def count_feature_profile(schools: pd.DataFrame) -> pd.DataFrame:
    """Scale of the count features, leaving out the INEP extreme-value code, which is counted apart.

    Outliers are values beyond 1.5 IQR from the quartiles.
    """
    rows = []
    for column in config.SIZE_FEATURES:
        marked = schools[column] == INEP_EXTREME_VALUE
        values = schools.loc[~marked, column].dropna()
        q1, q3 = values.quantile([0.25, 0.75])
        iqr = q3 - q1
        outliers = ((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)).mean()
        rows.append(
            {
                "atributo": column,
                "mediana": values.median(),
                "p99": values.quantile(0.99),
                "máximo": values.max(),
                "assimetria": values.skew(),
                "zeros": (values == 0).mean(),
                "outliers_iqr": outliers,
                "marcados_88888": int(marked.sum()),
            }
        )
    return pd.DataFrame(rows)


def target_by(schools: pd.DataFrame, column: str, labels: dict[int, str]) -> pd.DataFrame:
    grouped = schools.groupby(schools[column].map(labels))[TARGET]
    return grouped.agg(escolas="count", media="mean", desvio="std", mediana="median").sort_values("media", kind="stable")


def spearman_with_target(schools: pd.DataFrame) -> pd.Series:
    numeric = config.INFRASTRUCTURE_FEATURES + config.SIZE_FEATURES
    return schools[numeric].corrwith(schools[TARGET], method="spearman").sort_values(kind="stable")


def correlated_pairs(schools: pd.DataFrame, threshold: float = 0.8) -> pd.DataFrame:
    numeric = config.INFRASTRUCTURE_FEATURES + config.SIZE_FEATURES
    corr = schools[numeric].corr(method="spearman")
    pairs = [
        {"a": a, "b": b, "spearman": corr.loc[a, b]}
        for i, a in enumerate(numeric)
        for b in numeric[i + 1 :]
        if abs(corr.loc[a, b]) >= threshold
    ]
    return pd.DataFrame(pairs, columns=["a", "b", "spearman"]).sort_values("spearman", ascending=False, kind="stable")


def noise_by_school_size(schools: pd.DataFrame) -> pd.DataFrame:
    """Spread of the target by number of ENEM candidates: small schools have noisier means."""
    bins = pd.cut(schools["n_alunos"], [9, 14, 19, 29, 49, 99, schools["n_alunos"].max()])
    return schools.groupby(bins, observed=True)[TARGET].agg(escolas="count", desvio="std")
