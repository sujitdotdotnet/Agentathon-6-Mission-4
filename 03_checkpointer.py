"""
03 - A checkpointer keeps the list for you

LESSON: in lab 02 you kept the message list yourself. LangGraph can do that job for you.
Give the agent a CHECKPOINTER and it saves the conversation after every turn, then loads
it back on the next one. You send only the NEW message.

Two words to learn:
    checkpointer  - the thing that keeps the conversation
    thread_id     - the name of one conversation (the same idea as the session id in lab 02)

InMemorySaver keeps everything in the running program, so a restart still forgets.
Lab 04 changes that.

The file has two blocks. Read block 1. The chat page (block 2) is the same in every lab.

Run:  uv run 03_checkpointer.py      then open http://127.0.0.1:7860
Try:  1. My name is Asha and I work at SecureBank.
      2. What is my name?                  -> it knows
      3. Change the Session box to ticket-999 -> a new thread_id, a new conversation
"""

import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

from chat_ui import build_chat

load_dotenv()
if not os.getenv("DEEPSEEK_API_KEY"):
    raise SystemExit("Put your DEEPSEEK_API_KEY in the .env file first.")


# =============================================================================
# 1. THE AGENT  -  the same agent as before, plus ONE new line: checkpointer
# =============================================================================
SYSTEM = "You are a support assistant for SecureBank. Reply in plain text, with no markdown symbols."

agent = create_agent(
    model=init_chat_model("deepseek:deepseek-chat", max_tokens=250),
    tools=[],
    system_prompt=SYSTEM,
    checkpointer=InMemorySaver(),   # <- this line is the memory
)


def respond(message, session_id):
    # thread_id tells the checkpointer WHICH conversation this message belongs to.
    config = {"configurable": {"thread_id": session_id}}

    # We send only the new message. The checkpointer adds the history for us.
    result = agent.invoke({"messages": [{"role": "user", "content": message}]}, config)

    panel = "**What the model was sent this turn**\n\n"
    panel = panel + "- the system prompt\n"
    panel = panel + "- the whole conversation so far (added by the checkpointer)\n"
    panel = panel + "- your latest message\n\n"
    panel = panel + "Messages held for thread `" + session_id + "`: **" + str(len(result["messages"])) + "**\n\n"
    panel = panel + "In your code you passed 1 message. The checkpointer supplied the rest."
    return result["messages"][-1].content.strip(), panel


# =============================================================================
# 2. THE CHAT PAGE (Gradio)  -  the same in every lab. Skip it on your first read.
# =============================================================================
page = build_chat(
    respond,
    "03 - A checkpointer keeps the list for you",
    "The framework now stores the conversation. We send only the new message.",
    steps=[
        "Say: **My name is Asha and I work at SecureBank.**",
        "Ask: **What is my name?** It knows.",
        "**Refresh this browser page** and ask again. It STILL knows. The memory lives in the "
        "running program, not in the web page.",
        "Change the Session box to **ticket-999** and ask again. It does not know. "
        "A different thread_id is a different conversation.",
        "Stop the program with **Ctrl+C** and run it again. It has forgotten. Lab 04 fixes that.",
    ],
)
page.launch()
