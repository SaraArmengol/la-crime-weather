"""Persist processed data as Parquet and load it into DuckDB for SQL analysis.

DuckDB is an in-process analytical database: no server, and it queries Parquet
files directly. It lets the aggregations live in versioned .sql files.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from crime_weather.config import PROJECT_ROOT

SQL_DIR = PROJECT_ROOT / "sql"


def write_parquet(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def load_into_duckdb(db_path: Path, tables: dict[str, Path]) -> None:
    import duckdb

    with duckdb.connect(str(db_path)) as con:
        for name, parquet_path in tables.items():
            # Table names come from code, not user input; paths from config.
            con.execute(
                f"CREATE OR REPLACE TABLE {name} AS "
                f"SELECT * FROM read_parquet('{parquet_path.as_posix()}')"
            )


def run_sql_file(db_path: Path, sql_name: str) -> pd.DataFrame:
    import duckdb

    query = (SQL_DIR / sql_name).read_text(encoding="utf-8")
    with duckdb.connect(str(db_path), read_only=True) as con:
        return con.execute(query).df()
