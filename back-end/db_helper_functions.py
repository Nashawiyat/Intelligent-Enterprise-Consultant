import sqlite3
from datetime import datatime

insights_conn = None
cursor = None
def init_db_insights():
    global insights_conn
    global cursor
    insights_conn = sqlite3.connect("./db\ Insights")
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

def getLatestInsightRecordFromDB():
    result = cursor.execute("SELECT json, doman FROM Insights ORDER BY savedAt DESC LIMIT 1")
    return result.fetchone()

"""
CREATE TABLE Insights (
  insightID INTEGER PRIMARY KEY NOT NULL AUTOINCREMENT,
  json TEXT,
  domain TEXT,
  savedAt DATETIME DEFAULT CURRENT_TIMESTAMP
  -- id, timestamp, domain(sales/hr/etc.) and json (or simply text) fields.
);
"""