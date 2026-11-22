"""
04 - Memory that survives a restart

LESSON: lab 03 forgot everything when the program stopped, because InMemorySaver keeps the
conversation inside the running program. Change ONE line, use a SqliteSaver, and every turn
is written to a file on disk. Now the conversation survives a restart.

One database file holds MANY conversations. The thread_id says which one you are in, so
tickets never leak into each other.

    refresh the page   -> the program is still running, memory was never lost
    restart the program -> only memory written to disk can survive this

The file has two blocks. Read block 1. The chat page (block 2) is the same in every lab.

Run:  uv run 04_durable_sessions.py      then open http://127.0.0.1:7860
Try:  1. On ticket-101 say: I was double charged 12500 rupees yesterday.
      2. Stop the program (Ctrl+C) and run it again.
      3. Open ticket-101 again and ask: What is my problem?   -> it still knows
"""

import os
import sqlite3

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.sqlite import SqliteSaver

from chat_ui import build_chat

load_dotenv()
if not os.getenv("DEEPSEEK_API_KEY"):
    raise SystemExit("Put your DEEPSEEK_API_KEY in the .env file first.")


# =============================================================================
# 1. THE AGENT  -  the only change from lab 03 is the checkpointer line
# =============================================================================
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conversations.sqlite")
TICKETS = ["ticket-101", "ticket-102", "ticket-103"]

SYSTEM = "You are a support assistant for SecureBank. Reply in plain text, with no markdown symbols."

# One connection for the whole program. check_same_thread=False because the web page
# answers requests on different threads.
connection = sqlite3.connect(DB_FILE, check_same_thread=False)

agent = create_agent(
    model=init_chat_model("deepseek:deepseek-chat", max_tokens=250),
    tools=[],
    system_prompt=SYSTEM,
    checkpointer=SqliteSaver(connection),   # <- was InMemorySaver() in lab 03
)


def load_history(session_id):
    """Read a saved conversation back from the file, so it can be shown on screen."""
    config = {"configurable": {"thread_id": session_id}}
    snapshot = agent.get_state(config)
    shown = []
    for message in snapshot.values.get("messages", []):
        role = "assistant"
        if message.type == "human":
            role = "user"
        if message.content != "":
            shown.append({"role": role, "content": message.content})
    return shown


def respond(message, session_id):
    config = {"configurable": {"thread_id": session_id}}
    result = agent.invoke({"messages": [{"role": "user", "content": message}]}, config)

    panel = "**One file, many conversations**\n\n"
    panel = panel + "File: `conversations.sqlite`\n\n"
    for ticket in TICKETS:
        marker = ""
        if ticket == session_id:
            marker = "  <- you are here"
        panel = panel + "- `" + ticket + "`: " + str(len(load_history(ticket))) + " messages" + marker + "\n"
    panel = panel + "\nEach thread_id is its own memory. Nothing crosses over."
    return result["messages"][-1].content.strip(), panel


# =============================================================================
# 2. THE CHAT PAGE (Gradio)  -  the same in every lab. Skip it on your first read.
# =============================================================================
page = build_chat(
    respond,
    "04 - Memory that survives a restart",
    "Every turn is saved to a file. The thread_id picks the conversation.",
    steps=[
        "On **ticket-101** say: **I was double charged 12500 rupees yesterday.**",
        "Switch the dropdown to **ticket-102** and ask: **What is my problem?** It knows nothing. "
        "That is correct: a different ticket is a different memory.",
        "Switch back to **ticket-101**. The old chat comes back on screen and it remembers the double charge.",
        "Now the real test. Press **Ctrl+C** in the terminal, then start the lab again. Open **ticket-101** "
        "and ask what your problem was. It still knows, because it was read back from the file.",
        "To wipe everything and start clean, delete the file **conversations.sqlite**.",
    ],
    sessions=TICKETS,
    on_session_change=load_history,
)
page.launch()
