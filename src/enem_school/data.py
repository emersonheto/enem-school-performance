"""Build the school-level table: ENEM scores averaged per school, joined with Censo Escolar features."""

import subprocess
import urllib.request
from collections.abc import Iterable, Iterator
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

SCORE_COLUMNS = ["NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO"]
PRESENCE_COLUMNS = ["TP_PRESENCA_CN", "TP_PRESENCA_CH", "TP_PRESENCA_LC", "TP_PRESENCA_MT"]
PRESENT = 1
CENSO_SCHOOL_ID = "CO_ENTIDADE"


def school_score_totals(chunk: pd.DataFrame) -> pd.DataFrame:
    """Sum and count of candidate mean scores per school, for one chunk of ENEM results.

    A candidate counts only when present at the four exams, with all five scores and a school code.
    """
    valid = chunk[(chunk[PRESENCE_COLUMNS] == PRESENT).all(axis=1)]
    valid = valid.dropna(subset=SCORE_COLUMNS + ["CO_ESCOLA"])
    candidate_mean = valid[SCORE_COLUMNS].mean(axis=1)
    return candidate_mean.groupby(valid["CO_ESCOLA"].astype("int64")).agg(["sum", "count"])


def finalize_school_scores(totals: Iterable[pd.DataFrame], min_students: int) -> pd.DataFrame:
    """Combine per-chunk totals into one row per school with at least `min_students` candidates."""
    combined = pd.concat(list(totals)).groupby(level=0).sum()
    combined = combined[combined["count"] >= min_students]
    scores = pd.DataFrame(
        {
            "CO_ESCOLA": combined.index.astype("int64"),
            "n_alunos": combined["count"].astype("int64").to_numpy(),
            "nota_media": (combined["sum"] / combined["count"]).to_numpy(),
        }
    )
    return scores.sort_values("CO_ESCOLA").reset_index(drop=True)


def select_school_features(
    censo: pd.DataFrame, features: list[str], group_keys: list[str]
) -> tuple[pd.DataFrame, list[str]]:
    """One row per Censo school with the available features and the grouping keys."""
    available = [c for c in features if c in censo.columns]
    selected = censo[[CENSO_SCHOOL_ID, *available, *group_keys]].rename(columns={CENSO_SCHOOL_ID: "CO_ESCOLA"})
    selected = selected.dropna(subset=["CO_ESCOLA"]).astype({"CO_ESCOLA": "int64"})
    selected = selected.drop_duplicates(subset="CO_ESCOLA", keep="first").reset_index(drop=True)
    return selected, available


def build_school_table(scores: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    """Schools present both in the ENEM aggregation and in the Censo."""
    return scores.merge(selected, on="CO_ESCOLA", how="inner").sort_values("CO_ESCOLA").reset_index(drop=True)


def locate_or_download(url: str, raw_dir: Path, search_dirs: list[Path]) -> Path:
    """Reuse a raw file already on disk; otherwise download it into `raw_dir`."""
    name = url.rsplit("/", 1)[-1]
    for directory in [raw_dir, *search_dirs]:
        if (directory / name).is_file():
            return directory / name
    raw_dir.mkdir(parents=True, exist_ok=True)
    target = raw_dir / name
    partial = target.with_suffix(".part")
    urllib.request.urlretrieve(url, partial)
    partial.rename(target)
    return target


def _zip_member(zip_path: Path, must_contain: str) -> str:
    with ZipFile(zip_path) as archive:
        names = [n for n in archive.namelist() if must_contain in n.upper() and n.lower().endswith(".csv")]
    if not names:
        raise FileNotFoundError(f"No CSV containing {must_contain!r} in {zip_path}")
    return names[0]


def read_enem_results(enem_zip: Path, chunksize: int = 200_000) -> Iterator[pd.DataFrame]:
    """Stream RESULTADOS_<year>.csv in chunks.

    INEP zips can use Deflate64, which Python's zipfile cannot read, so the member is piped through `unzip -p`.
    """
    member = _zip_member(enem_zip, "RESULTADOS")
    with subprocess.Popen(["unzip", "-p", str(enem_zip), member], stdout=subprocess.PIPE) as proc:
        yield from pd.read_csv(
            proc.stdout,
            sep=";",
            encoding="latin1",
            usecols=["CO_ESCOLA", *SCORE_COLUMNS, *PRESENCE_COLUMNS],
            chunksize=chunksize,
        )


def read_censo_schools(censo_zip: Path, columns: list[str]) -> pd.DataFrame:
    """Read the main Censo table (microdados_ed_basica_<year>.csv), only the requested columns that exist."""
    member = _zip_member(censo_zip, "ED_BASICA")
    with ZipFile(censo_zip) as archive, archive.open(member) as handle:
        return pd.read_csv(
            handle, sep=";", encoding="latin1", usecols=lambda c: c in set(columns), low_memory=False
        )
