"""Database configuration and connection management."""

import os
import urllib.parse

import pandas as pd

from sqlalchemy import create_engine, text


def get_db_connection_string():
    """
    Database helper to retrieve the database connection string
    """

    return os.getenv("DBCONNECTIONSTRINGDEV")


def read_sql(query: str = "", params: dict = None, conn_string: str = "") -> pd.DataFrame:
    """
    Run a SELECT sql statement
    """

    if params is None:
        params = {}

    encoded_conn_str = urllib.parse.quote_plus(conn_string)

    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={encoded_conn_str}")

    try:
        with engine.begin() as conn:
            df = pd.read_sql(text(query), conn, params=params)

        return df

    except Exception as e:
        print()
        print("SQL error:", e)
        print()

        raise


def execute_sql(query: str, params: dict, conn_string: str) -> int:
    """
    Run an INSERT/UPDATE/DELETE sql statement
    """

    encoded_conn_str = urllib.parse.quote_plus(conn_string)

    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={encoded_conn_str}")

    try:
        with engine.begin() as conn:

            result = conn.execute(text(query), params)

        return result.rowcount

    except Exception as e:
        print()
        print("SQL error:", e)
        print()

        raise
