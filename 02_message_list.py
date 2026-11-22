"""
02 - Memory is a list you keep

LESSON: a conversation is just an ordered list of messages. The model has no memory, so
we keep the list ourselves and send ALL of it every turn. That is the whole trick.
You can see it here with no framework: a Python list, and a loop that adds to it.

Each conversation gets its own list. The name of the conversation is the session id
(called thread_id in LangGraph, which you meet in lab 03).

The file has two blocks. Read block 1. The chat page (block 2) is the same in every lab.

Run:  uv run 02_message_list.py      then open http://127.0.0.1:7860
Try:  1. My name is Asha and I work at SecureBank.
      2. What is my name?                  -> now it knows
      3. Change the Session box to ticket-999 and ask again -> it does not know
      4. Stop the program (Ctrl+C) and run it again -> it has forgotten everything
"""

import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from chat_ui import build_chat

load_dotenv()
if not os.getenv("DEEPSEEK_API_KEY"):
    raise SystemExit("Put your DEEPSEEK_API_KEY in the .env file first.")


# =============================================================================
# 1. THE MEMORY  -  a dictionary of lists. One list per conversation.
# =============================================================================
SYSTEM = "You are a support assistant for SecureBank. Reply in plain text, with no markdown symbols."

model = init_chat_model("deepseek:deepseek-chat", max_tokens=250)

# Session name -> the list of messages in that conversation.
conversations = {}


def respond(message, session_id):
    # Find this conversation's list. Start an empty one if it is new.
    if session_id not in conversations:
        conversations[session_id] = []
    history = conversations[session_id]

    # Add what the customer just said.
    history.append({"role": "user", "content": message})

    # Send the system prompt plus the WHOLE list.
    messages = [{"role": "system", "content": SYSTEM}] + history
    reply = model.invoke(messages)
    answer = reply.content.strip()

    # Keep the answer too, so the next turn can see it.
    history.append({"role": "assistant", "content": answer})

    panel = "**What the model was sent this turn**\n\n"
    panel = panel + "- the system prompt\n"
    panel = panel + "- the whole conversation so far\n\n"
    panel = panel + "Messages sent: **" + str(len(messages)) + "**\n\n"
    panel = panel + "It grows by 2 every turn, because we send everything again each time."
    return answer, panel


# =============================================================================
# 2. THE CHAT PAGE (Gradio)  -  the same in every lab. Skip it on your first read.
# =============================================================================
page = build_chat(
    respond,
    "02 - Memory is a list you keep",
    "We store the messages in a Python list and send all of them every turn.",
    steps=[
        "Say: **My name is Asha and I work at SecureBank.**",
        "Ask: **What is my name?** This time it knows. Watch the panel: the message count grows.",
        "Change the Session box to **ticket-999** and ask the same thing. It does not know. "
        "A different session id is a different list.",
        "Stop the program with **Ctrl+C** and run it again. Everything is gone, because the list "
        "lived only inside the running program. Lab 04 fixes that.",
    ],
)
page.launch()
