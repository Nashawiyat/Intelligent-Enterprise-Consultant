import os
from pathlib import Path
from dotenv import load_dotenv

# Load Environment Variables
ENV_PATH = Path(__file__).resolve().parent / "../.env"
load_dotenv(dotenv_path=ENV_PATH)

# Validate required vars before importing agent
required = ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "GROQ_API_KEY"]
missing = [k for k in required if not os.getenv(k)]
if missing:
    raise RuntimeError(f"Missing env vars in {ENV_PATH}: {', '.join(missing)}")

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from agent import enterprise_agent

# Pre-flight check
if not os.getenv("SLACK_BOT_TOKEN"):
    print("ERROR: SLACK_BOT_TOKEN not found in .env")
    exit(1)

if not os.getenv("SLACK_APP_TOKEN"):
    print("ERROR: SLACK_APP_TOKEN not found in .env")
    exit(1)

# Initialize Slack App
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

conversation_store = {}

def _truncate_for_slack(message: str) -> str:
    text = str(message or "")
    limit = 3000
    suffix = "... [Truncated for Slack. See full technical report on the dashboard]."
    if len(text) <= limit:
        return text
    cutoff = max(0, limit - len(suffix))
    return text[:cutoff].rstrip() + suffix

def _safe_say(say, message: str):
    say(_truncate_for_slack(message))

# Define the Message Handler
@app.event("app_mention")
def handle_app_mentions(event, say):
    user_query = event['text']
    user_id = event['user']
    thread_ts = event.get("thread_ts") or event.get("ts")
    thread_state = conversation_store.get(thread_ts, {"fact_sheet_history": [], "active_focus": None})
    prior_history = thread_state.get("fact_sheet_history", [])
    prior_focus = thread_state.get("active_focus")
    
    # Standard Inputs
    inputs = {
        "messages": [("user", user_query)],
        "is_simulation": False,
        "simulation_inputs": {},
        "active_focus": prior_focus,
        "role": "CEO",
        "sql_results": {},
        "fact_sheet_history": prior_history
    }
    
    # Invoke Agent
    response_state = enterprise_agent.invoke(inputs)
    insight = response_state.get("final_insight", {})
    interaction_mode = str(response_state.get("interaction_mode", "")).upper()
    current_focus = response_state.get("active_focus")
    response_history = response_state.get("fact_sheet_history", [])
    current_fact_sheet = response_state.get("fact_sheet", {})

    if isinstance(response_history, list) and response_history:
        resolved_history = [h for h in response_history if isinstance(h, dict)]
    else:
        resolved_history = list(prior_history) if isinstance(prior_history, list) else []
        if isinstance(current_fact_sheet, dict) and current_fact_sheet.get("tables"):
            resolved_history.append(current_fact_sheet)

    conversation_store[thread_ts] = {
        "fact_sheet_history": resolved_history[-6:],
        "active_focus": current_focus or prior_focus
    }

    chat_response = insight.get("chat_response") if isinstance(insight, dict) else None
    if chat_response:
        _safe_say(say, f"Hi <@{user_id}>! 👋\n\n{chat_response}")
        return

    if interaction_mode == "SOCIAL":
        _safe_say(say, "I’m here to help—ask me anything about the business and I’ll keep it conversational.")
        return

    if isinstance(insight, dict) and isinstance(insight.get("content"), dict):
        content = insight.get("content", {})
        headline = str(content.get("headline", "")).strip()
        summary = str(content.get("summary", "")).strip()
        reasoning = str(content.get("reasoning_detailed", "")).strip()

        is_follow_up = bool(event.get("thread_ts"))

        if headline or summary or reasoning:
            sections = []
            if headline:
                sections.append(f"*{headline}*")
            if summary:
                sections.append(summary)
            if reasoning:
                sections.append(f"_{reasoning}_")

            if is_follow_up:
                # Follow-ups skip the headline to be conversational
                followup_sections = []
                if summary:
                    followup_sections.append(summary)
                if reasoning:
                    followup_sections.append(f"_{reasoning}_")
                if not followup_sections and headline:
                    followup_sections.append(headline)
                _safe_say(say, f"Hi <@{user_id}>! 👋\n\n" + "\n\n".join(followup_sections))
                return

            _safe_say(say, f"Hi <@{user_id}>! 👋\n\n" + "\n\n".join(sections))
            return

    _safe_say(say, "I've analyzed the silos, but I'm having trouble phrasing the answer. Please ask me about a specific metric.")

# Start the Bridge
if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()