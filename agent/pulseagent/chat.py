"""Interactive terminal chat with the HR agent.

    python -m pulseagent.chat                  # read-only: the agent can look things up
    python -m pulseagent.chat --allow-writes   # also lets it approve leave / update tasks (each needs your y/n)
"""
import argparse
import asyncio
import os
import sys
import uuid

from langgraph.checkpoint.memory import MemorySaver
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from pulseagent.agent import ask, build_agent, load_hr_tools, make_model, resume


def describe(action: dict) -> str:
    args = ", ".join(f"{k}={v!r}" for k, v in action["args"].items())
    return f"{action['tool']}({args})"


async def run_chat(model, allow_writes: bool, read_input=input, write=print, callbacks=None) -> None:
    env = {**os.environ, "HR_MCP_READ_ONLY": "0" if allow_writes else "1"}
    params = StdioServerParameters(command=sys.executable, args=["-m", "pulseagent.mcp_server"], env=env)
    with open(os.devnull, "w") as quiet:  # hide the MCP server's request logs
        async with stdio_client(params, errlog=quiet) as (r, w), ClientSession(r, w) as session:
            await session.initialize()
            tools = await load_hr_tools(session)
            agent = build_agent(model, tools, MemorySaver(), callbacks=callbacks)
            thread = uuid.uuid4().hex
            write(f"PulseAgent ready ({len(tools)} tools, {'writes enabled' if allow_writes else 'read-only'}). Type 'exit' to quit.")
            while True:
                try:
                    question = read_input("\nYou: ").strip()
                except (EOFError, KeyboardInterrupt):
                    return
                if question.lower() in {"exit", "quit"}:
                    return
                if not question:
                    continue
                try:
                    out = await ask(agent, question, thread)
                    while out["pending_approval"]:  # the agent paused: a human must approve data changes
                        actions = out["pending_approval"]["actions"]
                        write("\nApproval needed:\n" + "\n".join(f"  - {describe(a)}" for a in actions))
                        approve = read_input("Approve? [y/N]: ").strip().lower() == "y"
                        out = await resume(agent, thread, approve)
                    write(f"\nAgent: {out['answer']}")
                except Exception as exc:  # noqa: BLE001  keep the chat alive on API/model errors
                    write(f"\n[error] {type(exc).__name__}: {str(exc)[:300]}")


def main() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-writes", action="store_true")
    args = parser.parse_args()
    missing = [k for k in ("GOOGLE_API_KEY", "HR_API_EMAIL", "HR_API_PASSWORD") if not os.environ.get(k)]
    if missing:
        sys.exit(f"Missing environment variables: {', '.join(missing)}. Copy .env.example to .env and fill them in.")
    asyncio.run(run_chat(make_model(), args.allow_writes))


if __name__ == "__main__":
    main()
