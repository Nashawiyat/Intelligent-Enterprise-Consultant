import asyncio
import os
import json
import sys
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()

# Pre-flight check
if not os.getenv("GROQ_API_KEY"):
    print("❌ ERROR: GROQ_API_KEY not found in .env")
    exit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "back-end")
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

from agent import enterprise_agent
from agent.nodes import insight_filter_node

def print_plotly_traces(insight: dict) -> None:
    visuals = insight.get("visuals", {}) if isinstance(insight, dict) else {}
    plotly_data = visuals.get("plotly_data", {}) if isinstance(visuals, dict) else {}
    traces = plotly_data.get("data", []) if isinstance(plotly_data, dict) else []
    print(f"\n📈 VISUAL TRACES ({len(traces)}):")
    for idx, trace in enumerate(traces, start=1):
        name = trace.get("name", "Unnamed") if isinstance(trace, dict) else "Unknown"
        print(f"  Trace {idx}: {name} -> x={trace.get('x')} y={trace.get('y')}")

async def run_test(test_name, inputs):
    print(f"\n{'='*30}\n{test_name}\n{'='*30}")
    final_state = await enterprise_agent.ainvoke(inputs)
    insight = final_state.get("final_insight", {})
    reasoning_steps = final_state.get("reasoning_steps", [])

    if reasoning_steps:
        print("\n🧭 REASONING STEPS:")
        for step in reasoning_steps:
            print(f"  - {step}")

    if insight is None:
        print("\n🔕 Filter Active: No material change detected. Insight suppressed.")
        return

    chat_response = insight.get("chat_response") if isinstance(insight, dict) else None
    if chat_response:
        print(f"\n💬 AI CHAT REPLY:\n{chat_response}")
        return

    if "content" in insight:
        print(f"\n📢 HEADLINE: {insight['content']['headline']}")
        print(f"📊 METRICS: Urgency: {insight['meta']['urgency_score']} | Confidence: {insight['meta']['confidence_score']}")
        print(f"🏢 SILOS AFFECTED: {insight.get('target_silos', 'General')}")
        
        print("\n🧐 THE WHY (Layman Analysis):")
        print(f"  {insight['content']['reasoning_detailed']}")

        print("\n🧠 THE HOW (AI Chain of Thought):")
        for step in insight.get("reasoning_chain", []):
            print(f"  Step {step['step']} [{step['agent']}]: {step['thought']}")

        print("\n💡 ACTION PLAN:")
        for rec in insight['content'].get('recommendations', []):
            print(f"  ✅ {rec['action']}: {rec['detail']}")
            print(f"     Impact: {rec['expected_impact']}")

        print_plotly_traces(insight)
    else:
        print(f"❌ FAILED: {insight.get('error')}")

async def test_cross_silo_chat():
    print(f"\n{'='*30}\nCROSS-SILO CHAT TEST\n{'='*30}")
    # Simulate a user asking a follow-up about the previous latency issue
    inputs = {
        "messages": [
            ("user", "Perform a health check."),
            ("user", "Why exactly is the latency affecting revenue? Give me the breakdown.")
        ],
        "role": "CEO",
        "is_simulation": False
    }
    final_state = await enterprise_agent.ainvoke(inputs)
    chat_output = final_state.get("final_insight", {}).get("chat_response")
    
    if chat_output:
        print(f"\n💬 AI CHAT REPLY:\n{chat_output}")
    else:
        print("❌ Chat mode failed.")

def test_insight_filter_negative():
    print(f"\n{'='*30}\nNEGATIVE FILTER TEST\n{'='*30}")
    state = {
        "fact_sheet": {
            "tables": {
                "finance": {
                    "baseline_date": "2026-02-01",
                    "current_date": "2026-02-07",
                    "fields": {
                        "revenue": {"baseline": 100.0, "current": 103.0, "delta_pct": 3.0}
                    }
                }
            }
        },
        "is_simulation": False
    }
    output = insight_filter_node(state)
    if output.get("end_early"):
        print("🔕 Filter Active: No material change detected. Insight suppressed.")
    else:
        print("❌ Filter did not suppress as expected.")

async def main():
    # --- Test Case 1: Proactive Health Check ---
    proactive_inputs = {
        "messages": [("user", "Perform a cross-domain health check. Look for anomalies.")],
        "role": "CEO",
        "is_simulation": False,
        "current_silo": "Finance/Operations" # Initializing to avoid KeyErrors
    }
    await run_test("PROACTIVE INSIGHT TEST", proactive_inputs)
    await test_cross_silo_chat()

    # --- Test Case 1b: Sales Manager Proactive Test ---
    sales_inputs = {
        "messages": [("user", "What is the current state of our silos?")],
        "role": "Sales Manager",
        "is_simulation": False,
        "current_silo": "Sales"
    }
    await run_test("SALES MANAGER PROACTIVE TEST", sales_inputs)

    # --- Test Case 2: Simulation Logic ---
    sim_inputs = {
        "messages": [("user", "Simulate a price drop.")],
        "role": "Sales Manager",
        "is_simulation": True,
        "simulation_inputs": {"price_change": -15, "ops_latency": 200},
        "current_silo": "Sales"
    }
    await run_test("SIMULATION SANDBOX TEST", sim_inputs)

    # --- Test Case 3: Negative Filter ---
    test_insight_filter_negative()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest cancelled by user.")