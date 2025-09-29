#!/usr/bin/env python3
"""Utility to load CSV data into a SQLite database."""

# Source: Implemented with assistance from OpenAI's GPT-5 (Codex) in the Harvard CS106 Codex CLI.

import argparse
import csv
import sqlite3
from pathlib import Path
import re
import sys
from typing import Iterable, List

VALID_IDENTIFIER = re.compile(r"[a-z_][a-z0-9_]*$")


def normalize_identifier(value: str) -> str:
    """Normalize identifiers by trimming whitespace, dropping BOMs, and lowercasing."""
    return value.strip().lstrip("\ufeff").lower()


def validate_identifier(raw_value: str, kind: str) -> str:
    """Ensure the provided value is a valid SQL identifier and return a cleaned version."""
    value = normalize_identifier(raw_value)
    if not value:
        raise ValueError(f"{kind} '{raw_value}' is empty after stripping whitespace")
    if not VALID_IDENTIFIER.match(value):
        raise ValueError(f"{kind} '{raw_value}' is not a valid SQL identifier")
    return value


def create_table(connection: sqlite3.Connection, table_name: str, columns: Iterable[str]) -> None:
    """Create (or replace) a table using the provided column names."""
    column_definitions = ", ".join(f"{col} TEXT" for col in columns)
    drop_sql = f"DROP TABLE IF EXISTS {table_name};"
    create_sql = f"CREATE TABLE {table_name} ({column_definitions});"
    connection.executescript(f"{drop_sql}\n{create_sql}")


def insert_rows(connection: sqlite3.Connection, table_name: str, columns: List[str], rows: Iterable[List[str]]) -> None:
    """Insert the provided rows into the specified table."""
    columns_joined = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    insert_sql = f"INSERT INTO {table_name} ({columns_joined}) VALUES ({placeholders});"
    connection.executemany(insert_sql, rows)


def load_csv_to_sqlite(db_path: Path, csv_path: Path) -> None:
    """Load the CSV file into the SQLite database."""
    table_name = validate_identifier(csv_path.stem, "Table name")

    with csv_path.open(newline='', encoding='utf-8') as csv_file:
        reader = csv.reader(csv_file)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("CSV file is empty") from exc

        columns = [validate_identifier(col, "Column name") for col in header]
        rows = list(reader)

    with sqlite3.connect(db_path) as connection:
        create_table(connection, table_name, columns)
        insert_rows(connection, table_name, columns, rows)
        connection.commit()


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load a CSV file into a SQLite database.")
    parser.add_argument("database", type=Path, help="Output SQLite database filename")
    parser.add_argument("csv", type=Path, help="Input CSV file with header row")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    if not args.csv.exists():
        raise SystemExit(f"CSV file not found: {args.csv}")

    try:
        load_csv_to_sqlite(args.database, args.csv)
    except ValueError as exc:
        raise SystemExit(str(exc))

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
