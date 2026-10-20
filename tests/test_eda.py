import pandas as pd

from enem_school import config
from enem_school.eda import INEP_EXTREME_VALUE, count_feature_profile, find_inconsistencies


def test_find_inconsistencies_counts_each_rule_and_ignores_missing_values():
    schools = pd.DataFrame(
        {
            "QT_MAT_MED": [100, 100, 0, None],
            "QT_DOC_MED": [10, 0, 5, 3],
            "QT_TUR_MED": [4, 4, 0, 2],
            "QT_SALAS_UTILIZADAS": [10, 5, 8, None],
            "QT_SALAS_UTILIZA_CLIMATIZADAS": [5, 9, 8, 2],
            "IN_INTERNET": [1, 0, 1, None],
            "IN_BANDA_LARGA": [1, 1, 0, 1],
            "n_alunos": [20, 150, 12, 30],
            "QT_DESKTOP_ALUNO": [10, INEP_EXTREME_VALUE, 3, None],
            "QT_COMP_PORTATIL_ALUNO": [INEP_EXTREME_VALUE, INEP_EXTREME_VALUE, 0, 1],
        }
    )

    result = find_inconsistencies(schools).set_index("rule")["schools"].to_dict()

    assert result == {
        "high school enrolment > 0 but no high school teachers": 1,
        "high school enrolment is zero": 1,
        "air-conditioned rooms > rooms in use": 1,
        "broadband without internet": 1,
        "ENEM candidates > high school enrolment": 2,
        "INEP extreme-value code 88888 in a count": 2,
    }


def test_count_feature_profile_reports_the_extreme_value_code_apart_from_the_scale():
    schools = pd.DataFrame({c: [1, 2, 3, 4] for c in config.SIZE_FEATURES})
    schools["QT_DESKTOP_ALUNO"] = [10, 20, 30, INEP_EXTREME_VALUE]

    profile = count_feature_profile(schools).set_index("atributo").loc["QT_DESKTOP_ALUNO"]

    assert profile["marcados_88888"] == 1
    assert profile["máximo"] == 30
    assert profile["mediana"] == 20
