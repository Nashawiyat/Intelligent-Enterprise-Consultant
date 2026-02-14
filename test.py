import sqlite3

def create_test_db():
    # Use absolute path if necessary to ensure the agent finds it
    conn = sqlite3.connect("enterprise_data2.db")
    cursor = conn.cursor()

    # 1. CRM (Marketing/Customer Sentiment)
    # Scenario: Customer satisfaction drops as technical issues rise
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crm (
            date TEXT, 
            customer_satisfaction_score REAL, 
            active_leads INT, 
            churn_rate REAL
        )
    """)
    cursor.execute("DELETE FROM crm") # Clear old data
    cursor.execute("INSERT INTO crm VALUES ('2026-02-01', 9.2, 1200, 0.02)")
    cursor.execute("INSERT INTO crm VALUES ('2026-02-07', 6.5, 950, 0.12)")

    # 2. ERP Accounting (Finance)
    # Scenario: Revenue drops significantly over one week
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS erp_accounting (
            date TEXT, 
            revenue REAL, 
            margin REAL, 
            expenditure REAL
        )
    """)
    cursor.execute("DELETE FROM erp_accounting")
    cursor.execute("INSERT INTO erp_accounting VALUES ('2026-02-01', 50000, 0.25, 37500)")
    cursor.execute("INSERT INTO erp_accounting VALUES ('2026-02-07', 42000, 0.20, 33600)")

    # 3. ERP HR (Human Resources)
    # Scenario: High utilization/overtime during the crisis
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS erp_hr (
            date TEXT, 
            headcount INT, 
            payroll_expenditure REAL, 
            productivity_index REAL
        )
    """)
    cursor.execute("DELETE FROM erp_hr")
    cursor.execute("INSERT INTO erp_hr VALUES ('2026-02-01', 150, 450000, 0.95)")
    cursor.execute("INSERT INTO erp_hr VALUES ('2026-02-07', 150, 450000, 0.78)")

    # 4. ERP Operations (Technical Performance)
    # Scenario: The "Smoking Gun" - Latency spikes and success rate drops
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS erp_operations (
            date TEXT, 
            latency_ms INT, 
            success_rate REAL, 
            uptime_pct REAL
        )
    """)
    cursor.execute("DELETE FROM erp_operations")
    cursor.execute("INSERT INTO erp_operations VALUES ('2026-02-01', 45, 0.99, 99.9)")
    cursor.execute("INSERT INTO erp_operations VALUES ('2026-02-07', 310, 0.88, 94.2)")

    # 5. ERP Sales (Pipeline)
    # Scenario: Deal closing velocity slows down
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS erp_sales (
            date TEXT, 
            deals_closed INT, 
            pipeline_value REAL, 
            avg_deal_size REAL
        )
    """)
    cursor.execute("DELETE FROM erp_sales")
    cursor.execute("INSERT INTO erp_sales VALUES ('2026-02-01', 45, 1200000, 26000)")
    cursor.execute("INSERT INTO erp_sales VALUES ('2026-02-07', 28, 900000, 32000)")

    conn.commit()
    conn.close()
    print("🚀 Round 2 Test Database Created with 5 correlated silos.")

if __name__ == "__main__":
    create_test_db()