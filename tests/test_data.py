import pandas as pd
import pytest

from enem_school.data import (
    SCORE_COLUMNS,
    build_school_table,
    finalize_school_scores,
    school_score_totals,
    select_school_features,
)


def candidate(school, scores=(500, 500, 500, 500, 500), present=(1, 1, 1, 1)):
    row = {"CO_ESCOLA": school}
    row.update(dict(zip(SCORE_COLUMNS, scores)))
    row.update({f"TP_PRESENCA_{area}": p for area, p in zip(["CN", "CH", "LC", "MT"], present)})
    return row


def test_candidate_mean_is_the_average_of_the_five_scores():
    chunk = pd.DataFrame([candidate(1, scores=(400, 500, 600, 700, 800))])

    result = finalize_school_scores([school_score_totals(chunk)], min_students=1)

    assert result.loc[0, "nota_media"] == pytest.approx(600.0)


def test_excludes_absent_candidates_missing_scores_and_missing_school():
    chunk = pd.DataFrame(
        [
            candidate(1, scores=(500,) * 5),
            candidate(1, scores=(900,) * 5, present=(1, 1, 0, 1)),
            candidate(1, scores=(900, 900, 900, 900, None)),
            candidate(None, scores=(900,) * 5),
        ]
    )

    result = finalize_school_scores([school_score_totals(chunk)], min_students=1)

    assert result.to_dict("records") == [{"CO_ESCOLA": 1, "n_alunos": 1, "nota_media": 500.0}]


def test_combining_chunks_equals_aggregating_all_rows_at_once():
    rows = [candidate(1, scores=(s,) * 5) for s in (400, 500, 600)] + [candidate(2, scores=(700,) * 5)]
    whole = finalize_school_scores([school_score_totals(pd.DataFrame(rows))], min_students=1)

    chunked = finalize_school_scores(
        [school_score_totals(pd.DataFrame(rows[:2])), school_score_totals(pd.DataFrame(rows[2:]))],
        min_students=1,
    )

    pd.testing.assert_frame_equal(whole, chunked)
    assert chunked.set_index("CO_ESCOLA")["nota_media"].to_dict() == {1: 500.0, 2: 700.0}


def test_min_students_threshold_is_inclusive():
    rows = [candidate(1)] * 10 + [candidate(2)] * 9
    totals = school_score_totals(pd.DataFrame(rows))

    result = finalize_school_scores([totals], min_students=10)

    assert result["CO_ESCOLA"].tolist() == [1]
    assert result["n_alunos"].tolist() == [10]


def censo_frame():
    return pd.DataFrame(
        {
            "CO_ENTIDADE": [11, 11, 22, 33],
            "IN_BIBLIOTECA": [1, 1, 0, 1],
            "TP_DEPENDENCIA": [2, 2, 4, 3],
            "QT_MAT_MED": [100, 100, 50, 80],
            "CO_MUNICIPIO": [4300, 4300, 4301, 4302],
            "CO_UF": [43, 43, 43, 43],
            "NO_ENTIDADE": ["A", "A", "B", "C"],
        }
    )


def test_select_school_features_keeps_only_known_features_and_group_keys():
    features, keys = ["IN_BIBLIOTECA", "TP_DEPENDENCIA", "QT_MAT_MED", "IN_NOT_IN_CENSO"], ["CO_MUNICIPIO", "CO_UF"]

    selected, available = select_school_features(censo_frame(), features, keys)

    assert available == ["IN_BIBLIOTECA", "TP_DEPENDENCIA", "QT_MAT_MED"]
    assert list(selected.columns) == ["CO_ESCOLA", *available, *keys]
    assert selected["CO_ESCOLA"].tolist() == [11, 22, 33]


def test_build_school_table_keeps_only_schools_present_in_both_sources():
    scores = pd.DataFrame({"CO_ESCOLA": [11, 22, 99], "n_alunos": [10, 12, 30], "nota_media": [500.0, 550.0, 600.0]})
    selected, _ = select_school_features(censo_frame(), ["IN_BIBLIOTECA"], ["CO_MUNICIPIO"])

    table = build_school_table(scores, selected)

    assert table["CO_ESCOLA"].tolist() == [11, 22]
    assert table.loc[table["CO_ESCOLA"] == 22, "IN_BIBLIOTECA"].item() == 0
