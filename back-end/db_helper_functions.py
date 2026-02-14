import sqlite3
import json

conn = None
cursor = None
def init_db():
    global conn
    global cursor
    conn = sqlite3.connect("./admin_db.db", check_same_thread=False)
    cursor = conn.cursor()

def close_db():
    conn.commit()
    conn.close()

def recordInsight(json_result: str, domain: str):
    if not cursor:
        raise Exception("Cursor not initialised")
    
    json_string = json.dumps(json_result)
    data = (json_string, domain)
    cursor.execute("INSERT INTO Insights (json, domain) VALUES (?, ?)", data)
    conn.commit()

def getLatestInsightRecordFromDB(domain: str):
    if not cursor:
        raise Exception("Cursor not initialised")
    
    result = cursor.execute("SELECT json, savedAt FROM Insights WHERE domain = ? ORDER BY savedAt DESC LIMIT 4", (domain,))
    listed = []
    for (json_result, savedAt) in result:
        listed.append(
            {
                "timestamp": savedAt,
                "insight": json.loads(json_result) 
            }
        )

    return listed

def createUser(username, hashed, display_name, mode, department, role):
    if not cursor:
        raise Exception("Cursor not initialised")
    
    data = (username, hashed, display_name, mode, department, role)
    cursor.execute(
        "INSERT INTO Users (username, hash, display_name, mode, department, role) VALUES (?, ?, ?, ?, ?, ?)", data)
    conn.commit()

def getUserHash(username):
<<<<<<< HEAD
    # Case-insensitive lookup
    return cursor.execute(
        "SELECT hash FROM Users WHERE LOWER(username) = LOWER(?)", (username,)
    ).fetchone()

def getUserDetails(username):
    result = cursor.execute(
        "SELECT display_name, mode, department, role FROM Users WHERE LOWER(username) = LOWER(?)",
        (username,)
    ).fetchone()
    if result is None:
        return None
=======
    if not cursor:
        raise Exception("Cursor not initialised")
    
    return cursor.execute("SELECT hash FROM Users WHERE username = ?", (username,)).fetchone()
    
def getUserDetails(username):
    if not cursor:
        raise Exception("Cursor not initialised")
    
    result = cursor.execute("SELECT display_name, mode, department, role FROM Users WHERE username = ?", (username,)).fetchone()
    
    if result is None:
        return Exception("User not found")
>>>>>>> main

    return {
        "username": username,
        "display_name": result[0],
        "mode": result[1],
        "department": result[2],
        "role": result[3],
    }

<<<<<<< HEAD

def getUserByUsername(username):
    """Case-insensitive exact match. Returns user dict or None."""
    result = cursor.execute(
        "SELECT username, display_name, mode, department, role FROM Users WHERE LOWER(username) = LOWER(?)",
        (username,)
    ).fetchone()
    if result is None:
        return None
    return {
        "username": result[0],
        "display_name": result[1],
        "mode": result[2],
        "department": result[3],
        "role": result[4],
    }


def getAllUsers():
    """Return list of all users (without hashes)."""
    rows = cursor.execute(
        "SELECT username, display_name, mode, department, role FROM Users"
    ).fetchall()
    return [
        {
            "username": r[0],
            "display_name": r[1],
            "mode": r[2],
            "department": r[3],
            "role": r[4],
        }
        for r in rows
    ]


def updateUser(username, **fields):
    """
    Update user fields by username. Only fields present in `fields` are changed.
    Supported fields: display_name, mode, department, role, hash (for password).
    Returns True if a row was updated.
    """
    allowed = {"display_name", "mode", "department", "role", "hash"}
    to_set = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not to_set:
        return False
    set_clause = ", ".join(f"{col} = ?" for col in to_set)
    values = list(to_set.values()) + [username]
    cursor.execute(
        f"UPDATE Users SET {set_clause} WHERE LOWER(username) = LOWER(?)",
        values,
    )
    conn.commit()
    return cursor.rowcount > 0


def deleteUser(username):
    """Delete a user by username. Returns True if deleted."""
    cursor.execute(
        "DELETE FROM Users WHERE LOWER(username) = LOWER(?)", (username,)
    )
    conn.commit()
    return cursor.rowcount > 0


def countAdmins():
    """Return count of admin users."""
    result = cursor.execute(
        "SELECT COUNT(*) FROM Users WHERE mode = 'admin'"
    ).fetchone()
    return result[0] if result else 0


def isModeAdmin(username):
    result = cursor.execute(
        "SELECT mode FROM Users WHERE LOWER(username) = LOWER(?)", (username,)
    ).fetchone()
=======
def getAllUsersDetails():
    if not cursor:
        raise Exception("Cursor not initialised")

    result = cursor.execute("SELECT username, display_name, mode, department, role FROM Users ORDER BY department, username")
    result = result.fetchall()

    listed = []
    for (username, display_name, mode, department, role) in result:
        listed.append({
            "username": username,
            "display_name": display_name,
            "mode": mode,
            "department": department,
            "role": role
        })
    
    return listed

def isModeAdmin(username):
    if not cursor:
        raise Exception("Cursor not initialised")
    
    result = cursor.execute("SELECT mode FROM Users WHERE username = ?", (username,)).fetchone()
>>>>>>> main
    if result is None:
        raise Exception(f"Mode not found for username. Does {username} exist?")

    return result[0] == "admin"
