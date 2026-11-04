import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dropoff.db import Database, load_all  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def db(tmp_path_factory):
    """A DuckDB database loaded with the six-student fixture."""
    path = tmp_path_factory.mktemp("db") / "fixture.duckdb"
    database = Database(engine="duckdb", path=str(path))
    load_all(database, FIXTURES)
    database.execute_script((ROOT / "sql" / "04_early_features.sql").read_text())
    yield database
    database.close()
