"""Build the small sample in data/sample/ from the full raw data.

Keeps modules AAA and GGG, 100 random students per presentation (seed 7),
and only VLE rows before day 28 (the only ones the analysis reads).
The sample is for running the pipeline offline. Its numbers are NOT the findings.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "sample"
MODULES = ["AAA", "GGG"]
PER_PRESENTATION = 100


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    read = lambda f: pd.read_csv(RAW / f, dtype=str, keep_default_na=False)  # noqa: E731
    info = read("studentInfo.csv")
    info = info[info["code_module"].isin(MODULES)]
    info = info.groupby(["code_module", "code_presentation"]).sample(n=PER_PRESENTATION, random_state=7)
    keys = info[["code_module", "code_presentation", "id_student"]]

    def by_student(df):
        return df.merge(keys, on=["code_module", "code_presentation", "id_student"])

    courses = read("courses.csv")
    assessments = read("assessments.csv")
    vle = read("vle.csv")
    courses = courses[courses["code_module"].isin(MODULES)]
    assessments = assessments[assessments["code_module"].isin(MODULES)]
    vle = vle[vle["code_module"].isin(MODULES)]
    reg = by_student(read("studentRegistration.csv"))
    sa = read("studentAssessment.csv")
    sa = sa[sa["id_assessment"].isin(assessments["id_assessment"]) & sa["id_student"].isin(keys["id_student"])]
    sa = sa.merge(assessments[["id_assessment", "code_module", "code_presentation"]], on="id_assessment")
    sa = by_student(sa)[["id_assessment", "id_student", "date_submitted", "is_banked", "score"]]
    svle = pd.read_csv(RAW / "studentVle.csv", dtype=str)
    svle = svle[svle["code_module"].isin(MODULES) & (svle["date"].astype(int) < 28)]
    svle = by_student(svle)

    for name, df in [("courses.csv", courses), ("assessments.csv", assessments), ("vle.csv", vle),
                     ("studentInfo.csv", info), ("studentRegistration.csv", reg),
                     ("studentAssessment.csv", sa), ("studentVle.csv", svle)]:
        df.to_csv(OUT / name, index=False)
        print(f"{name:<26} {len(df):>7,} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
