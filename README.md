# AI Enterprise Consultant

**Unified AI Agentic System for Cross-Silo Forensic Analysis & Predictive Simulation**

Developed by a team of 5 students, the AI Enterprise Consultant allowed us to proceed for the 2nd Round of the Deriv AI Hackathon 2026. This system is not just a chatbot; it is a System of Reasoning that automates the investigative paths traditionally performed by business analysts and technical leads.

## The Problem

Enterprise data is traditionally trapped in fragmented "silos"—Operations logs, Accounting ledgers, and CRM records often don't talk to each other. When revenue drops, executives are forced to manually correlate data across multiple dashboards to find the root cause, leading to delayed decisions and "lost opportunity" costs.

## The Solution

The AI Enterprise Consultant sits on top of all enterprise silos to provide a unified intelligence loop:

* **Cross-Silo Triangulation:** Automatically correlates technical anomalies (e.g., a 50% latency spike in Operations) with financial outcomes (e.g., a 16% revenue drop in Accounting).
* **Causal Forensic Investigation:** Instead of black-box answers, the agent provides a "Reasoning Chain" detailing its investigative path from data acquisition to anomaly detection.
* **Predictive Simulation Sandbox:** Allows executives to run "What-If" scenarios, such as a 15% price drop, projected against current operational realities.
* **Executive Accessibility:** Delivers high-level "Layman Analysis", translating technical jargon into business-ready insights.

## Technical Architecture

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

**Test Credentials (VP of Sales role):** 
* **Username:** SalesGuy
* **Password:** sales123 

## Key Features

* **Proactive Alerts:** The system suppresses noise and only flags "material changes" exceeding a 5% threshold.
* **Context-Aware Memory:** The agent uses thread-based persistence to remember previous turn anomalies, allowing for follow-up questions like "Who is responsible for fixing this?".
* **Role-Based Personas:** Tailors reports for CEOs (executive synthesis) vs. Sales Managers (lead quality and pipeline health).

### Home Dashboard:
<img width="1917" height="910" alt="image" src="https://github.com/user-attachments/assets/582cace1-c51f-43eb-9a52-73f1d0340ffe" />

### Insight Casual Reasoning and Recommendations:
<img width="1236" height="692" alt="image" src="https://github.com/user-attachments/assets/026c08b5-0772-458b-8180-c4449fee9d8d" />

### Simulation Sandbox (Operations example):
<img width="1919" height="899" alt="image" src="https://github.com/user-attachments/assets/1a2e7de3-f99c-4682-b717-8b122126e457" />
<img width="1919" height="910" alt="image" src="https://github.com/user-attachments/assets/309e9872-48b7-4311-9cb4-e35ee59b6d91" />

### Slack Chat Feature:
<img width="1341" height="389" alt="image" src="https://github.com/user-attachments/assets/79016c7d-f9fa-412b-a6b4-91cf6b64ed8b" />


