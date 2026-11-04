"""Export tidy tables for a Power BI retention dashboard: python -m dropoff.powerbi

Needs dropoff.analysis to have run first (it builds early_features and outputs/).
"""
import logging

import pandas as pd

from . import config
from .db import Database

log = logging.getLogger(__name__)


def main() -> None:
    out = config.OUT_DIR / "powerbi"
    out.mkdir(parents=True, exist_ok=True)
    db = Database()

    pres = db.query("SELECT code_module, code_presentation, module_presentation_length FROM courses "
                    "ORDER BY code_module, code_presentation")
    pres["presentation_key"] = pres["code_module"] + "-" + pres["code_presentation"]
    pres["year"] = pres["code_presentation"].str[:4].astype(int)
    pres["start_month"] = pres["code_presentation"].str[4].map({"B": "February", "J": "October"})
    pres.to_csv(out / "dim_presentation.csv", index=False)

    enrol = db.run_file("07_powerbi_enrolment.sql")
    for c in ["date_unregistration", "withdrawal_week", "clicks_pre_start", "clicks_w1_4",
              "active_days_w1_4", "early_assessments_missed"]:
        enrol[c] = enrol[c].astype("Int64")
    enrol.to_csv(out / "fact_enrolment.csv", index=False)
    db.close()

    a = pd.read_csv(config.OUT_DIR / "assessment_difficulty.csv")
    a["presentation_key"] = a["code_module"] + "-" + a["code_presentation"]
    a.drop(columns=["order_in_presentation"]).to_csv(out / "fact_assessment.csv", index=False)

    s = pd.read_csv(config.OUT_DIR / "early_warning_test_scores.csv")
    s.to_csv(out / "fact_risk_score_2014J.csv", index=False)
    log.info(f"Power BI tables written to {out}")
    for p in sorted(out.glob("*.csv")):
        log.info(f"  {p.name:<28} {sum(1 for _ in open(p)) - 1:>7,} rows")


if __name__ == "__main__":
    config.setup_logging()
    main()
