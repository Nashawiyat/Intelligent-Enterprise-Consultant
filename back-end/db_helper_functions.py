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
    if not cursor:
        raise Exception("Cursor not initialised")
    
    return cursor.execute("SELECT hash FROM Users WHERE username = ?", (username,)).fetchone()
    
def getUserDetails(username):
    if not cursor:
        raise Exception("Cursor not initialised")
    
    result = cursor.execute("SELECT display_name, mode, department, role FROM Users WHERE username = ?", (username,)).fetchone()
    
    if result is None:
        return Exception("User not found")

    return {
        "username": username,
        "display_name": result[0],
        "role": result[1],
        "department": result[2],
        "title": result[3]
    }

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
    if result is None:
        raise Exception(f"Mode not found for username. Does {username} exist?")

    return result[0] == "admin"
    