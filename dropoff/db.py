"""A thin layer over PostgreSQL (psycopg) or DuckDB.

The SQL files in sql/ are written to run unchanged on both engines.
"""
from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

import pandas as pd

from . import config


class Database:
    def __init__(self, engine: str | None = None, url: str | None = None, path: str | None = None):
        self.engine = engine or config.DB_ENGINE
        if self.engine == "postgres":
            import psycopg

            self.conn = psycopg.connect(url or config.DATABASE_URL, autocommit=True)
        elif self.engine == "duckdb":
            import duckdb

            self.conn = duckdb.connect(path or config.DUCKDB_PATH)
        else:
            raise ValueError(f"Unknown DB_ENGINE: {self.engine}")

    # -- running SQL -------------------------------------------------------
    def execute_script(self, sql: str) -> None:
        if self.engine == "postgres":
            with self.conn.cursor() as cur:
                cur.execute(sql)
        else:
            self.conn.execute(sql)

    def query(self, sql: str, params: dict | None = None) -> pd.DataFrame:
        if self.engine == "postgres":
            with self.conn.cursor() as cur:
                cur.execute(sql, params)
                cols = [d.name for d in cur.description]
                rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=cols)
            # NUMERIC comes back as Decimal; use floats for analysis.
            for c in df.columns:
                if len(df) and isinstance(df[c].dropna().iloc[0] if df[c].notna().any() else None, Decimal):
                    df[c] = df[c].astype(float)
            return df
        return self.conn.execute(sql, params or {}).df()

    def run_file(self, name: str) -> pd.DataFrame:
        return self.query(read_sql(name))

    # -- loading CSVs --------------------------------------------------------
    def load_csv(self, table: str, path: Path) -> None:
        """Load one OULAD CSV. The raw files use "?" for missing values."""
        with open(path, newline="") as f:
            header = next(csv.reader(f))
        cols = ", ".join(header)
        if self.engine == "postgres":
            sql = (
                f"COPY {table} ({cols}) FROM STDIN WITH "
                f"(FORMAT csv, HEADER true, NULL '?', FORCE_NULL ({cols}))"
            )
            with self.conn.cursor() as cur, cur.copy(sql) as copy, open(path, "rb") as f:
                while chunk := f.read(1 << 20):
                    copy.write(chunk)
        else:
            self.conn.execute(
                f"INSERT INTO {table} ({cols}) SELECT {cols} FROM "
                f"read_csv('{path.as_posix()}', header=true, nullstr='?', all_varchar=true)"
            )

    def close(self) -> None:
        self.conn.close()


def read_sql(name: str) -> str:
    return (config.SQL_DIR / name).read_text()


def load_all(db: Database, data_dir: Path) -> dict[str, int]:
    """Create the schema and load every CSV found in data_dir. Returns row counts."""
    db.execute_script(read_sql("00_schema.sql"))
    counts = {}
    for fname, table in config.TABLES.items():
        db.load_csv(table, Path(data_dir) / fname)
        counts[table] = int(db.query(f"SELECT COUNT(*) AS n FROM {table}")["n"].iloc[0])
    db.execute_script(read_sql("00_indexes.sql"))
    return counts
