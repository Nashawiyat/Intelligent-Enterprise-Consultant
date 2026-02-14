# NOTE: NO LONGER BEING USED; KEPT FOR FUTURE IMPROVEMENT

import sqlite3

conn = None
cursor = None
def init_db():
    global conn
    global cursor
    conn = sqlite3.connect("./admin_db.db")
    cursor = conn.cursor()

def close_db():
    conn.commit()
    conn.close()

def recordInsight(json: str, domain: str):
    if not cursor:
        raise Exception("Cursor not initialised")
    
    data = (json, domain)
    cursor.execute("INSERT INTO Insights (json, domain) VALUES (?, ?)", data)
    conn.commit()

def getLatestInsightRecordFromDB(domain: str):
    result = cursor.execute("SELECT json FROM Insights WHERE domain = ? ORDER BY savedAt DESC LIMIT 1", (domain,))
    return result.fetchone()

def createUser(username, hash, display_name, mode, department, role):
    data = (username, hash, display_name, mode, department, role)
    cursor.execute(
        "INSERT INTO Users " \
        "(username, hash, display_name, mode, department, role)" \
        "(?, ?, ?, ?, ?, ?)", data)
    conn.commit()

def getUserHash(username):
    return cursor.execute("SELECT hash FROM Users WHERE username = ?", (username,)).fetchone()
    
def getUserDetails(username):
    result = cursor.execute("SELECT display_name, mode, department, role FROM Users WHERE username = ?", (username,)).fetchone()

    return {
        "username": username,
        "display_name": result[0],
        "role": result[1],
        "department": result[2],
        "title": result[3]
    }

def loginUser(username, token):
    cursor.execute("INSERT INTO SessionTokens VALUES (?, ?)", (username, token))
    conn.commit()