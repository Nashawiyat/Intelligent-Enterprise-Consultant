import sqlite3

insights_conn = None
cursor = None
def init_db_insights():
    global insights_conn
    global cursor
    insights_conn = sqlite3.connect("./db Insights")
    cursor = insights_conn.cursor()


def close_db_insights():
    insights_conn.commit()
    insights_conn.close()

def recordInsight(json: str, domain: str):
    if not cursor:
        raise "Cursor not initialised"
    
    data = (json, domain)
    cursor.execute("INSERT INTO Insights (json, domain) VALUES (?, ?)", data)
    insights_conn.commit()

def getLatestInsightRecordFromDB(domain: str):
    result = cursor.execute("SELECT json FROM Insights WHERE domain = ? ORDER BY savedAt DESC LIMIT 1", domain)
    return result.fetchone()