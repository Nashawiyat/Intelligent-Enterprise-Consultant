"""
Seed realistic time-series anomaly data into the enterprise databases.

Creates daily summary tables in both DBs so the LangGraph agent can detect
meaningful cross-silo anomalies (revenue declines, rising costs, lead
conversion drops, delivery delays, staff turnover, etc.).

Run once:  python seed_anomaly_data.py
"""

import sqlite3
import os

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ERP_DB = os.path.join(BACKEND_DIR, "trieerp1.db")
CRM_DB = os.path.join(BACKEND_DIR, "triecrm1.db")

# ─────────────────────────────────────────────
# ERP summary tables
# ─────────────────────────────────────────────

def seed_erp():
    conn = sqlite3.connect(ERP_DB)
    c = conn.cursor()

    # ── DailySalesSummary ──
    c.execute("DROP TABLE IF EXISTS DailySalesSummary")
    c.execute("""
        CREATE TABLE DailySalesSummary (
            report_date   DATE PRIMARY KEY,
            total_revenue DECIMAL(15,2),
            total_orders  INTEGER,
            avg_order_value DECIMAL(10,2),
            total_profit  DECIMAL(15,2),
            cancellation_rate DECIMAL(5,2)
        )
    """)
    sales_rows = [
        ("2026-02-08", 285000, 52, 5480.77, 95000,  3.8),
        ("2026-02-09", 278000, 50, 5560.00, 92000,  4.0),
        ("2026-02-10", 265000, 48, 5520.83, 88000,  5.2),
        ("2026-02-11", 240000, 43, 5581.40, 76000,  7.0),
        ("2026-02-12", 210000, 37, 5675.68, 62000,  9.5),
        ("2026-02-13", 185000, 32, 5781.25, 48000, 12.1),
        ("2026-02-14", 168000, 28, 6000.00, 38000, 14.3),
    ]
    c.executemany(
        "INSERT INTO DailySalesSummary VALUES (?,?,?,?,?,?)", sales_rows
    )

    # ── DailyFinancialSummary ──
    c.execute("DROP TABLE IF EXISTS DailyFinancialSummary")
    c.execute("""
        CREATE TABLE DailyFinancialSummary (
            report_date             DATE PRIMARY KEY,
            total_income            DECIMAL(15,2),
            total_expenses          DECIMAL(15,2),
            net_cash_flow           DECIMAL(15,2),
            outstanding_receivables DECIMAL(15,2),
            expenditure             DECIMAL(15,2)
        )
    """)
    fin_rows = [
        ("2026-02-08", 285000, 190000,  95000, 120000, 190000),
        ("2026-02-09", 278000, 195000,  83000, 135000, 195000),
        ("2026-02-10", 265000, 205000,  60000, 158000, 205000),
        ("2026-02-11", 240000, 215000,  25000, 185000, 215000),
        ("2026-02-12", 210000, 225000, -15000, 210000, 225000),
        ("2026-02-13", 185000, 235000, -50000, 242000, 235000),
        ("2026-02-14", 168000, 248000, -80000, 278000, 248000),
    ]
    c.executemany(
        "INSERT INTO DailyFinancialSummary VALUES (?,?,?,?,?,?)", fin_rows
    )

    # ── DailyOperationsSummary ──
    c.execute("DROP TABLE IF EXISTS DailyOperationsSummary")
    c.execute("""
        CREATE TABLE DailyOperationsSummary (
            report_date           DATE PRIMARY KEY,
            production_orders     INTEGER,
            components_used       INTEGER,
            avg_delivery_days     DECIMAL(5,2),
            defect_rate           DECIMAL(5,2),
            on_time_delivery_pct  DECIMAL(5,2)
        )
    """)
    ops_rows = [
        ("2026-02-08", 15, 450, 3.2, 1.5, 96.0),
        ("2026-02-09", 14, 430, 3.5, 1.8, 94.5),
        ("2026-02-10", 12, 380, 4.1, 2.5, 91.0),
        ("2026-02-11", 10, 320, 5.0, 3.8, 85.0),
        ("2026-02-12",  8, 260, 5.8, 4.5, 79.0),
        ("2026-02-13",  7, 220, 6.5, 5.2, 72.5),
        ("2026-02-14",  6, 190, 7.2, 6.0, 68.0),
    ]
    c.executemany(
        "INSERT INTO DailyOperationsSummary VALUES (?,?,?,?,?,?)", ops_rows
    )

    # ── DailyHRSummary ──
    c.execute("DROP TABLE IF EXISTS DailyHRSummary")
    c.execute("""
        CREATE TABLE DailyHRSummary (
            report_date      DATE PRIMARY KEY,
            total_headcount  INTEGER,
            active_employees INTEGER,
            total_payroll    DECIMAL(15,2),
            avg_salary       DECIMAL(10,2),
            turnover_rate    DECIMAL(5,2)
        )
    """)
    hr_rows = [
        ("2026-02-08", 60, 58, 325000, 5417,  2.0),
        ("2026-02-09", 60, 57, 325000, 5417,  3.3),
        ("2026-02-10", 59, 55, 322000, 5458,  5.1),
        ("2026-02-11", 58, 53, 318000, 5483,  8.6),
        ("2026-02-12", 56, 51, 310000, 5536, 10.7),
        ("2026-02-13", 55, 49, 305000, 5545, 12.7),
        ("2026-02-14", 53, 47, 298000, 5623, 13.2),
    ]
    c.executemany(
        "INSERT INTO DailyHRSummary VALUES (?,?,?,?,?,?)", hr_rows
    )

    conn.commit()
    conn.close()
    print(f"[OK] Seeded ERP anomaly summary tables in {ERP_DB}")


# ─────────────────────────────────────────────
# CRM summary tables
# ─────────────────────────────────────────────

def seed_crm():
    conn = sqlite3.connect(CRM_DB)
    c = conn.cursor()

    # ── DailyCRMSummary ──
    c.execute("DROP TABLE IF EXISTS DailyCRMSummary")
    c.execute("""
        CREATE TABLE DailyCRMSummary (
            report_date        DATE PRIMARY KEY,
            new_leads          INTEGER,
            converted_leads    INTEGER,
            lost_leads         INTEGER,
            total_interactions INTEGER,
            follow_ups_pending INTEGER,
            satisfaction_score DECIMAL(3,1)
        )
    """)
    crm_rows = [
        ("2026-02-08", 18, 12,  2, 45,  8, 8.5),
        ("2026-02-09", 16, 10,  3, 42, 12, 8.2),
        ("2026-02-10", 15,  8,  5, 38, 18, 7.8),
        ("2026-02-11", 12,  6,  6, 35, 24, 7.2),
        ("2026-02-12", 10,  4,  8, 30, 30, 6.5),
        ("2026-02-13",  8,  3,  9, 28, 35, 5.8),
        ("2026-02-14",  7,  2, 10, 25, 38, 5.2),
    ]
    c.executemany(
        "INSERT INTO DailyCRMSummary VALUES (?,?,?,?,?,?,?)", crm_rows
    )

    conn.commit()
    conn.close()
    print(f"[OK] Seeded CRM anomaly summary tables in {CRM_DB}")


if __name__ == "__main__":
    seed_erp()
    seed_crm()
    print("\nDone. Summary tables with 7-day anomaly trends created.")
