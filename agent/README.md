# PulseAgent

An agent that operates PeoplePulse through tools. HR staff ask in plain language ("who has pending leave?",
"approve Dev's sick leave"); the agent plans, calls tools, **asks a human before changing any data**, and answers.

```
terminal chat ─▶ LangGraph agent ─▶ MCP client ══stdio══▶ MCP server ─▶ PeoplePulse REST API ─▶ PostgreSQL
                 │  call_model → gate → tools → call_model …
                 │  step limit · tool retries · error recovery · context trimming · human approval
```

The agent never touches the database. It signs in to the API as a chosen user, so the backend's role checks
and business rules always apply (an employee account gets 403 on HR-only tools).

## What is built

| Piece | Where |
|---|---|
| MCP server with 7 read tools (+2 write tools only when `HR_MCP_READ_ONLY=0`, so they are not even discoverable otherwise) | `pulseagent/mcp_server.py` |
| API client with token handling and one automatic re-login | `pulseagent/hr_client.py` |
| LangGraph harness: step limit, retries with backoff for transient errors, tool errors returned to the model, output truncation, history trimming, **interrupt-based human approval** | `pulseagent/agent.py` |
| Resumable runs via a LangGraph checkpointer (in-memory for now) | `agent.py`, tested by restarting the agent |
| Terminal chat with approval prompts | `pulseagent/chat.py` |
| Scripted chat model for deterministic, free tests | `pulseagent/testing.py` |
| 24 tests (MCP server + agent behaviour) | `tests/` |

## Not built yet (be honest about this in interviews)

Tracing (Langfuse), the eval dataset and regression runner, RAG over policy documents, a Postgres checkpointer,
a web chat UI, Docker/CI. **The agent has not yet been run against a real LLM by me**: tests use a scripted model.
Tool schemas were checked to convert into Gemini function declarations offline, but real tool-calling quality is unmeasured until you run it.

## Setup

PeoplePulse backend must be running (`uvicorn app.main:app` in `backend/`) with the seed data loaded.

```bash
cd agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env      # then fill in GOOGLE_API_KEY (free key: https://aistudio.google.com/apikey)
pytest -q                 # 24 tests, no API key or network needed
python -m pulseagent.chat                  # read-only
python -m pulseagent.chat --allow-writes   # may propose approvals/updates; each needs your y
```

`GEMINI_MODEL` defaults to `gemini-2.5-flash`; if Google has renamed or retired it, set another model from AI Studio.
The free tier has request limits; the agent retries transient 429/503 errors a few times.

Try: *"How many employees are active?"*, *"Who has pending leave?"*, *"Show onboarding progress for the 3 least complete employees"*,
then with `--allow-writes`: *"Approve the oldest pending leave request"*. Log in as the employee demo account in `.env`
to see permission errors handled gracefully.

## Design notes

- **Approval gate** (`gate` node): any call to a write tool pauses the graph with `interrupt`. Nothing with side effects runs
  before the interrupt, so resuming is safe. Declined calls are reported to the model as "NOT performed".
- **Prompt injection**: tool results are data. The system prompt says so, and the gate means a hijacked model still cannot change anything unapproved (tested).
- **Retries** only for errors the API marks `(retryable)` (5xx/429/network); 4xx are returned to the model once so it can fix its arguments.
- **Why `handle_tool_errors=False`**: the MCP adapter otherwise converts failures to plain text, hiding them from the retry logic. A test caught this.
