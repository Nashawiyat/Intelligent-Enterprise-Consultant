import os
import sqlite3

def create_database(sql_file_path: str, db_file_path: str) -> None:
    if not os.path.exists(sql_file_path):
        raise FileNotFoundError(f"SQL file not found: {sql_file_path}")

    with open(sql_file_path, "r", encoding="utf-8") as sql_file:
        sql_script = sql_file.read()

    conn = sqlite3.connect(db_file_path)
    try:
        conn.executescript(sql_script)
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sql_path = os.path.join(base_dir, "onedatabase.db")
    db_path = os.path.join(base_dir, "big_enterprise_data.db")
    create_database(sql_path, db_path)
    print("Database created.")
