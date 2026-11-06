"""One-time migration: add new columns to existing SQLite DB."""
from app import create_app, db
from sqlalchemy import text

app = create_app('development')

migrations = [
    ("orders", "amount_paid",        "FLOAT DEFAULT 0.0"),
    ("orders", "payment_status",     "VARCHAR(30) DEFAULT 'Unpaid'"),
    ("orders", "created_by_admin",   "BOOLEAN DEFAULT 0"),
    ("payments", "payment_method",   "VARCHAR(50) DEFAULT 'Cash'"),
    ("payments", "note",             "VARCHAR(255)"),
    ("payments", "recorded_by_id",   "INTEGER"),
]

with app.app_context():
    with db.engine.connect() as conn:
        for table, col, col_def in migrations:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"))
                print(f"  + {table}.{col}")
            except Exception as e:
                print(f"  ~ {table}.{col}: {e}")
        conn.commit()
    print("Migration complete!")
