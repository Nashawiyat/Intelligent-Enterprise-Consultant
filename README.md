# Intelligent-Enterprise-Consultant

DeriveHackathon 2026 - Unified AI agent delivering real-time insights, predictive simulations, and actionable recommendations and decision support across various enterprise domains.

Library installation:

```bash
pip install langgraph langchain langchain-core langchain-community langchain-groq tavily-python fastapi uvicorn pydantic streamlit plotly requests streamlit-autorefresh python-jose[cryptography] bcrypt slack_bolt
```

running back-end:

1. Go to /back-end/folder
2. Run `uvicorn main:app --reload`

running front-end:

1. In the root directory, run `streamlit run front-end/app.py`

running slack-bot:
1. Go to /back-end/folder
2. Run python `slack_bridge.py`
3. Tag the bot on Slack with any prompt you would like.
