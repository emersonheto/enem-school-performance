"""Build data/processed/schools_enem2025_censo2024.parquet and its metadata JSON.

Usage (from the repository root): uv run python scripts/build_dataset.py
"""

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import sklearn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from enem_school import config  # noqa: E402
from enem_school.data import (  # noqa: E402
    CENSO_SCHOOL_ID,
    build_school_table,
    finalize_school_scores,
    locate_or_download,
    read_censo_schools,
    read_enem_results,
    school_score_totals,
    select_school_features,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    enem_zip = locate_or_download(config.ENEM_URL, config.RAW_DIR, [])
    censo_zip = locate_or_download(config.CENSO_URL, config.RAW_DIR, [])
    print(f"ENEM:  {enem_zip}")
    print(f"Censo: {censo_zip}")

    totals = [school_score_totals(chunk) for chunk in read_enem_results(enem_zip)]
    all_schools = finalize_school_scores(totals, min_students=1)
    scores = all_schools[all_schools["n_alunos"] >= config.MIN_STUDENTS_PER_SCHOOL].reset_index(drop=True)
    print(f"Valid candidates with a school: {all_schools['n_alunos'].sum():,} in {len(all_schools):,} schools")
    print(f"Schools with >= {config.MIN_STUDENTS_PER_SCHOOL} candidates: {len(scores):,}")

    censo = read_censo_schools(censo_zip, [CENSO_SCHOOL_ID, *config.FEATURES, *config.GROUP_KEYS])
    selected, features = select_school_features(censo, config.FEATURES, config.GROUP_KEYS)
    missing = sorted(set(config.FEATURES) - set(features))
    table = build_school_table(scores, selected)
    print(f"Censo schools: {len(selected):,}; features available: {len(features)} of {len(config.FEATURES)}")
    print(f"Joined schools: {len(table):,} ({len(table) / len(scores):.1%} of ENEM schools)")
    print(f"nota_media: {table['nota_media'].mean():.1f} +/- {table['nota_media'].std():.1f}")

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    table.to_parquet(config.SCHOOL_TABLE, index=False)
    metadata = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": {
            "enem": {"url": config.ENEM_URL, "file": enem_zip.name, "sha256": sha256(enem_zip)},
            "censo": {"url": config.CENSO_URL, "file": censo_zip.name, "sha256": sha256(censo_zip)},
        },
        "min_students_per_school": config.MIN_STUDENTS_PER_SCHOOL,
        "valid_candidates": int(all_schools["n_alunos"].sum()),
        "enem_schools": len(all_schools),
        "enem_schools_above_threshold": len(scores),
        "censo_schools": len(selected),
        "joined_schools": len(table),
        "features": features,
        "missing_features": missing,
        "group_keys": config.GROUP_KEYS,
        "target": "nota_media",
        "versions": {"python": platform.python_version(), "pandas": pd.__version__, "scikit-learn": sklearn.__version__},
    }
    config.SCHOOL_TABLE_METADATA.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {config.SCHOOL_TABLE} and {config.SCHOOL_TABLE_METADATA.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
