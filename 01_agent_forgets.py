"""
01 - The agent that forgets

LESSON: a language model is stateless. Every call starts from zero. Tell it your name,
and on the very next message it has no idea who you are. Nothing is broken. There is
no conversation inside the model. Memory is not something the model HAS. It is
something YOU build. That is this whole mission.

The file has two blocks. Read block 1. The chat page (block 2) is the same in every lab.

Run:  uv run 01_agent_forgets.py      then open http://127.0.0.1:7860
Try:  1. My name is Asha and I work at SecureBank.
      2. What is my name?
"""

import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from chat_ui import build_chat

load_dotenv()
if not os.getenv("DEEPSEEK_API_KEY"):
    raise SystemExit("Put your DEEPSEEK_API_KEY in the .env file first.")


# =============================================================================
# 1. THE MODEL CALL  -  we send ONLY the newest message. No history at all.
# =============================================================================
SYSTEM = "You are a support assistant for SecureBank. Reply in plain text, with no markdown symbols."

model = init_chat_model("deepseek:deepseek-chat", max_tokens=200)


def respond(message, session_id):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": message},
    ]
    reply = model.invoke(messages)

    panel = "**What the model was sent this turn**\n\n"
    panel = panel + "- the system prompt\n"
    panel = panel + "- your latest message\n\n"
    panel = panel + "That is all: **2 messages**. It will be 2 again next turn, however long you chat."
    return reply.content.strip(), panel


# =============================================================================
# 2. THE CHAT PAGE (Gradio)  -  the same in every lab. Skip it on your first read.
# =============================================================================
page = build_chat(
    respond,
    "01 - The agent that forgets",
    "A language model only sees the message you just sent.",
    steps=[
        "Say: **My name is Asha and I work at SecureBank.**",
        "Now ask: **What is my name?**",
        "It does not know. Look at the panel on the right: only 2 messages were sent, and that never grows.",
        "Nothing is broken. The model has no memory of its own. Lab 02 adds it.",
    ],
    show_session=False,
)
page.launch()
