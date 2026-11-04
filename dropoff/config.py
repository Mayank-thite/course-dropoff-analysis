"""Paths and settings. Everything can be overridden with environment variables."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT / "sql"
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data" / "raw"))
OUT_DIR = Path(os.environ.get("OUT_DIR", ROOT / "outputs"))
DOCS_DIR = Path(os.environ.get("DOCS_DIR", ROOT / "docs"))

# "postgres" (default) or "duckdb"
DB_ENGINE = os.environ.get("DB_ENGINE", "postgres")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://oulad:oulad@localhost:5432/oulad")
DUCKDB_PATH = os.environ.get("DUCKDB_PATH", str(ROOT / "data" / "oulad.duckdb"))

# Raw CSV file -> table name
TABLES = {
    "courses.csv": "courses",
    "assessments.csv": "assessments",
    "vle.csv": "vle",
    "studentInfo.csv": "student_info",
    "studentRegistration.csv": "student_registration",
    "studentAssessment.csv": "student_assessment",
    "studentVle.csv": "student_vle",
}

# Early-warning window: days 0 to 27 of the presentation (weeks 1 to 4).
EARLY_DAYS = 28
# Presentation held out for testing the early-warning model.
TEST_PRESENTATION = "2014J"
# Share of students an advisor team could contact. Every scorer flags this share.
FLAG_SHARE = 0.20
SEED = 7


def setup_logging() -> None:
    """One log format for every pipeline step."""
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
