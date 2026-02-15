"""
Seed the admin_db.db with demo users matching frontend DEFAULT_USERS.
Run: python seed_db.py
"""

import sqlite3
import bcrypt

DB_PATH = "./admin_db.db"

DEMO_USERS = [
    # (username,  password,  display_name,  mode,  department,  role / title)
    ("admin",    "admin",   "System Admin",   "admin", "IT",          "Admin"),
    ("user",     "user",    "Alex Morgan",    "user",  "Executive",   "CEO"),
    ("cfo",      "cfo",     "Jordan Lee",     "user",  "Finance",     "CFO"),
    ("cto",      "cto",     "Sam Rivera",     "user",  "Engineering", "CTO"),
]


def hash_pw(plain: str) -> bytes:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt())


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Clear existing users (safe for dev/demo)
    cur.execute("DELETE FROM Users")

    for username, password, display_name, mode, department, role in DEMO_USERS:
        hashed = hash_pw(password)
        cur.execute(
            "INSERT INTO Users (username, hash, display_name, mode, department, role) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (username, hashed, display_name, mode, department, role),
        )
        print(f"  ✓ {username} / {password}  (mode={mode}, role={role})")

    conn.commit()
    conn.close()
    print(f"\nSeeded {len(DEMO_USERS)} users into {DB_PATH}")


if __name__ == "__main__":
    main()
