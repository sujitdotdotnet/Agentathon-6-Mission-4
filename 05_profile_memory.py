"""
05 - A profile that follows the person

LESSON: conversation memory belongs to ONE conversation. Open a new ticket and it is gone.
But some facts should follow the person everywhere: their name, role, account type, how
they like to be answered. That is a PROFILE.

    thread_id = WHICH conversation   (changes with every ticket)
    profile   = WHOSE memory         (stays with the customer)

Every turn does three small steps:
    1. READ    ask the model what this message tells us about the customer
    2. SAVE    merge any new facts into profile.json
    3. ANSWER  put the saved profile into the prompt, so the model can use it

The profile code is in profile_store.py. Open it, it is short.

The file has two blocks. Read block 1. The chat page (block 2) is the same in every lab.

Run:  uv run 05_profile_memory.py      then open http://127.0.0.1:7860
Try:  1. I am Asha, a relationship manager. I hold a Premium account and prefer short answers.
      2. Change the Session box to ticket-999 (a brand new conversation)
      3. Ask: Who am I and what account do I have?    -> it knows
"""

import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

from chat_ui import build_chat
from profile_store import PROFILE_FILE, profile_as_text, update_profile

load_dotenv()
if not os.getenv("DEEPSEEK_API_KEY"):
    raise SystemExit("Put your DEEPSEEK_API_KEY in the .env file first.")


# =============================================================================
# 1. THE MEMORY  -  conversation (checkpointer) plus profile (file)
# =============================================================================
SYSTEM = (
    "You are a support assistant for SecureBank. The customer is already signed in and verified. "
    "If facts about the customer are listed below, treat them as true and use them directly. "
    "Reply in plain text, with no markdown symbols."
)

model = init_chat_model("deepseek:deepseek-chat", max_tokens=250)

# One checkpointer for the whole program, so the conversation keeps building up.
checkpointer = InMemorySaver()


def respond(message, session_id):
    # 1 + 2. READ the message for facts, SAVE them to the profile file.
    profile, new_facts = update_profile(message)

    # 3. ANSWER. The prompt changes when the profile changes, so we build the agent each turn.
    prompt = SYSTEM
    facts_text = profile_as_text(profile)
    if facts_text != "":
        prompt = prompt + "\n\nWhat you know about this customer:\n" + facts_text

    agent = create_agent(model=model, tools=[], system_prompt=prompt, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": session_id}}
    result = agent.invoke({"messages": [{"role": "user", "content": message}]}, config)

    panel = "**The profile (saved in profile.json)**\n\n"
    if facts_text == "":
        panel = panel + "- nothing known yet\n"
    else:
        panel = panel + facts_text
    if len(new_facts) > 0:
        panel = panel + "\nSaved this turn: " + ", ".join(new_facts.keys()) + "\n"
    panel = panel + "\nThread `" + session_id + "` can change. The profile stays."
    return result["messages"][-1].content.strip(), panel


print("Profile file:", PROFILE_FILE)


# =============================================================================
# 2. THE CHAT PAGE (Gradio)  -  the same in every lab. Skip it on your first read.
# =============================================================================
page = build_chat(
    respond,
    "05 - A profile that follows the person",
    "Facts about the customer are saved in a file, outside any one conversation.",
    steps=[
        "Say: **I am Asha, a relationship manager. I hold a Premium account and I prefer short answers.**",
        "Watch the panel on the right: the model pulled four fields out of your sentence and saved them.",
        "Change the Session box to **ticket-999**, a conversation that never existed before.",
        "Ask: **Who am I and what account do I have?** It knows. The thread changed, the profile did not.",
        "Stop the program and run it again, then ask once more. Still there, because it is saved in "
        "**profile.json**. Delete that file to wipe the profile.",
    ],
)
page.launch()
