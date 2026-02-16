# AI Enterprise Consultant

**Unified AI Agentic System for Cross-Silo Forensic Analysis & Predictive Simulation**

Developed for the **Deriv Hackathon 2026**, this AI powered software solution is not just a chatbot; it is a **System of Reasoning** that automates the investigative path usually performed by teams of business analysts.

## The Problem

Enterprise data is traditionally trapped in fragmented "silos"—Operations logs, Accounting ledgers, and CRM records often don't talk to each other. When revenue drops, executives are forced to manually correlate data across multiple dashboards to find the root cause, leading to delayed decisions and "lost opportunity" costs.

## The Solution

The AI Enterprise Consultant sits on top of all enterprise silos to provide a unified intelligence loop:

* **Cross-Silo Triangulation:** Automatically correlates technical anomalies (e.g., a 50% latency spike in Operations) with financial outcomes (e.g., a 16% revenue drop in Accounting).
* **Causal Forensic Investigation:** Instead of black-box answers, the agent provides a "Reasoning Chain" detailing its investigative path from data acquisition to anomaly detection.
* **Predictive Simulation Sandbox:** Allows executives to run "What-If" scenarios, such as a 15% price drop, projected against current operational realities.
* **Executive Accessibility:** Delivers high-level "Layman Analysis", translating technical jargon into business-ready insights.

## 🛠️ Technical Architecture

The AI Enterprise Consultant uses a **LangGraph-powered State Machine** to manage complex multi-turn investigations:

* **Orchestrator Node:** Performs real-time Intent Classification to route traffic between Social, Analytical, or Competitive Intelligence paths.
* **SQL Specialist:** Generates and executes dynamic queries across different silo databases and tables.
* **Quantitative Auditor:** Performs the manual math for delta calculations and identifies outliers.
* **Strategic Reasoner:** Synthesizes internal data with external market signals (via Tavily API) to produce actionable recommendations.

Software tech-stack:
* **Back-end:** FastAPI + SQLite
* **Front-end:** Streamlit
* **AI Agent:** LangGraph + Groq (Llama 3) LLM

## Getting Started

### Library Installation

```bash
pip install langgraph langchain langchain-core langchain-community langchain-groq tavily-python fastapi uvicorn pydantic streamlit plotly requests streamlit-autorefresh python-jose[cryptography] bcrypt slack_bolt

```

### Execution

1. **Back-End:** `cd back-end && uvicorn main:app --reload`
2. **Front-End Dashboard:** `streamlit run front-end/app.py`
3. **Slack Integration:** `cd back-end && python slack_bridge.py`

## Key Features

* **Proactive Alerts:** The system suppresses noise and only flags "material changes" exceeding a 5% threshold.
* **Context-Aware Memory:** The agent uses thread-based persistence to remember previous turn anomalies, allowing for follow-up questions like "Who is responsible for fixing this?".
* **Role-Based Personas:** Tailors reports for CEOs (executive synthesis) vs. Sales Managers (lead quality and pipeline health).
