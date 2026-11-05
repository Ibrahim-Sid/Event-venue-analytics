"""
ETL: load the CSVs from data/raw/ into PostgreSQL.

Steps
  1. (Re)create the schema from sql/01_schema.sql
  2. Read each CSV with pandas and run basic data-quality checks
  3. Insert tables in foreign-key order
  4. Reset SERIAL sequences so new inserts get correct ids

Usage:
    python etl/load_data.py
Connection string is read from the DATABASE_URL environment variable
(default: postgresql+psycopg://postgres:postgres@localhost:5432/eventdb).
"""

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/eventdb")

# Load order matters because of foreign keys
TABLES = ["customers", "event_types", "rooms", "services",
          "events", "event_rooms", "event_services"]
DATE_COLS = {"events": ["booked_at", "start_date", "end_date"]}


def check_quality(name: str, df: pd.DataFrame) -> None:
    """Simple data-quality gate – fail loudly instead of loading bad data."""
    if df.empty:
        raise ValueError(f"{name}: file is empty")
    pk = df.columns[0]
    if name not in ("event_rooms", "event_services") and df[pk].duplicated().any():
        raise ValueError(f"{name}: duplicate primary keys in {pk}")
    if name == "events":
        bad = df[df["end_date"] < df["start_date"]]
        if not bad.empty:
            raise ValueError(f"events: {len(bad)} rows end before they start")
        missing = df[(df["status"] == "completed") & df["actual_attendees"].isna()]
        if not missing.empty:
            raise ValueError(f"events: {len(missing)} completed events without attendees")


def main() -> None:
    engine = create_engine(DB_URL)

    with engine.begin() as conn:
        conn.execute(text((ROOT / "sql" / "01_schema.sql").read_text(encoding="utf-8")))
        print("Schema created")

        for name in TABLES:
            df = pd.read_csv(RAW / f"{name}.csv", parse_dates=DATE_COLS.get(name, False))
            if name == "events":
                df["actual_attendees"] = df["actual_attendees"].astype("Int64")
            check_quality(name, df)
            df.to_sql(name, conn, if_exists="append", index=False, method="multi", chunksize=1000)
            print(f"  loaded {len(df):>6} rows into {name}")

        # keep SERIAL sequences in sync with the explicit ids we inserted
        for name in ["customers", "event_types", "rooms", "services", "events"]:
            pk = f"{name[:-1]}_id" if name != "event_types" else "event_type_id"
            conn.execute(text(
                f"SELECT setval(pg_get_serial_sequence('{name}', '{pk}'), (SELECT MAX({pk}) FROM {name}))"
            ))

    print("Done.")


if __name__ == "__main__":
    main()
