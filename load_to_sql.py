"""
Load Processed Olist E-Commerce Datasets to MySQL Database
==========================================================
This script connects to a local MySQL instance, creates the target database 
if it does not exist, and loads all cleaned CSV datasets from data/processed/ 
into individual SQL tables with appropriate data types.
"""

import os
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus
import pandas as pd
from sqlalchemy import create_engine, text

# ==========================================
# Database Configuration
# ==========================================
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "NewPassword@123")
DB_NAME = os.getenv("DB_NAME", "olist_analytics")

# Dataset definitions and datetime columns to parse
PROCESSED_DIR = Path("data/processed")

TABLE_DEFINITIONS = [
    {
        "file": "category_translation.csv",
        "table": "category_translation",
        "date_cols": []
    },
    {
        "file": "customers.csv",
        "table": "customers",
        "date_cols": []
    },
    {
        "file": "sellers.csv",
        "table": "sellers",
        "date_cols": []
    },
    {
        "file": "products.csv",
        "table": "products",
        "date_cols": []
    },
    {
        "file": "orders.csv",
        "table": "orders",
        "date_cols": [
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date"
        ]
    },
    {
        "file": "order_items.csv",
        "table": "order_items",
        "date_cols": [
            "shipping_limit_date"
        ]
    },
    {
        "file": "payments.csv",
        "table": "payments",
        "date_cols": []
    },
    {
        "file": "reviews.csv",
        "table": "reviews",
        "date_cols": [
            "review_creation_date",
            "review_answer_timestamp"
        ]
    }
]


def get_server_engine():
    """Create an engine connected to MySQL server without specifying a database."""
    encoded_pass = quote_plus(DB_PASS)
    connection_url = f"mysql+pymysql://{DB_USER}:{encoded_pass}@{DB_HOST}:{DB_PORT}/"
    return create_engine(connection_url, isolation_level="AUTOCOMMIT")


def get_db_engine():
    """Create an engine connected to the target database."""
    encoded_pass = quote_plus(DB_PASS)
    connection_url = f"mysql+pymysql://{DB_USER}:{encoded_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    return create_engine(connection_url)


def ensure_database_exists():
    """Create the target database if it doesn't exist."""
    print(f"Connecting to MySQL server at {DB_HOST}:{DB_PORT} as '{DB_USER}'...")
    server_engine = get_server_engine()
    with server_engine.connect() as conn:
        conn.execute(text(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        ))
    server_engine.dispose()
    print(f"[OK] Database '{DB_NAME}' is ready.\n")


def load_datasets():
    """Load all processed CSV files into MySQL tables."""
    if not PROCESSED_DIR.exists():
        print(f"[ERROR] Directory not found: {PROCESSED_DIR}")
        sys.exit(1)

    ensure_database_exists()
    db_engine = get_db_engine()

    summary_stats = []
    total_start_time = time.time()

    print(f"{'='*60}")
    print(f"Loading datasets into database: {DB_NAME}")
    print(f"{'='*60}")

    for item in TABLE_DEFINITIONS:
        file_path = PROCESSED_DIR / item["file"]
        table_name = item["table"]
        date_cols = item["date_cols"]

        if not file_path.exists():
            print(f"[SKIP] File not found: {file_path}")
            continue

        print(f"\nProcessing '{item['file']}' -> table '{table_name}'...")
        start_time = time.time()

        # Read CSV
        df = pd.read_csv(file_path)
        csv_rows = len(df)

        # Convert date columns to datetime
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        # Write to MySQL
        df.to_sql(
            name=table_name,
            con=db_engine,
            if_exists="replace",
            index=False,
            chunksize=2000,
            method="multi"
        )

        elapsed = time.time() - start_time

        # Verify inserted row count
        with db_engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
            sql_rows = result.scalar()

        status = "[SUCCESS]" if csv_rows == sql_rows else "[WARN-MISMATCH]"
        print(f"  {status} Loaded {sql_rows:,} rows in {elapsed:.2f}s ({len(df.columns)} columns)")

        summary_stats.append({
            "table": table_name,
            "csv_rows": csv_rows,
            "sql_rows": sql_rows,
            "columns": len(df.columns),
            "time_sec": round(elapsed, 2)
        })

    db_engine.dispose()
    total_elapsed = time.time() - total_start_time

    # Print summary table
    print(f"\n{'='*60}")
    print("MIGRATION SUMMARY")
    print(f"{'='*60}")
    print(f"{'Table Name':<25} | {'CSV Rows':<10} | {'SQL Rows':<10} | {'Columns':<8} | {'Time (s)':<8}")
    print(f"{'-'*25}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}-+-{'-'*8}")
    
    total_rows = 0
    for s in summary_stats:
        total_rows += s["sql_rows"]
        print(f"{s['table']:<25} | {s['csv_rows']:<10} | {s['sql_rows']:<10} | {s['columns']:<8} | {s['time_sec']:<8}")

    print(f"{'-'*25}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}-+-{'-'*8}")
    print(f"Total Rows Loaded: {total_rows:,}")
    print(f"Total Time: {total_elapsed:.2f}s")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    load_datasets()
