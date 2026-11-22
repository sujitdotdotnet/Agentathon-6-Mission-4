"""
07 - Capstone: build the context packet yourself

LESSON: memory is everything you STORE. Context is the small slice you choose to SEND.

A long conversation costs money, because the whole list is sent again on every turn. So each
turn we build a "context packet" instead of sending everything:

    1. the system prompt
    2. the customer's profile                    (lab 05)
    3. the playbook that fits this message       (lab 06)
    4. a short summary of the OLD messages       (so the gist is not lost)
    5. only the last few messages, word for word
    6. the new message

When the recent list gets longer than MAX_RECENT, the oldest messages are folded into the
summary. The panel on the right shows how many tokens this saves compared with sending
everything. (A token is about 4 characters. This is an estimate, not a bill.)

The file has two blocks. Read block 1. The chat page (block 2) is the same in every lab.

Run:  uv run 07_context_packet.py      then open http://127.0.0.1:7860
Try:  Chat for 5 or 6 turns, then ask about something you said at the very start.
"""

import datetime
import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from chat_ui import build_chat
from profile_store import profile_as_text, update_profile
from skills_loader import choose_skill, load_skills

load_dotenv()
if not os.getenv("DEEPSEEK_API_KEY"):
    raise SystemExit("Put your DEEPSEEK_API_KEY in the .env file first.")


# =============================================================================
# 1. THE MEMORY AND THE PACKET
# =============================================================================
# The model has no clock, so we tell it today's date. Some playbooks need it (refunds: within 30 days?).
today = datetime.date.today().strftime("%d %B %Y")

SYSTEM = (
    "You are a support assistant for SecureBank. Today is " + today + ". The customer is already signed in and verified. "
    "Use the facts and the earlier summary below as true. Be brief. "
    "Reply in plain text, with no markdown symbols."
)

MAX_RECENT = 4   # how many recent messages we send word for word (2 exchanges)

model = init_chat_model("deepseek:deepseek-chat", max_tokens=250)

# Procedural memory (lab 06): the playbooks, and a small cheap model that picks one.
skills = load_skills()
chooser = init_chat_model("deepseek:deepseek-chat", temperature=0.0, max_tokens=30)

# For each session we keep three things:
recent = {}        # the last few messages, word for word
summaries = {}     # one short summary of everything older
everything = {}    # the full history, kept ONLY so we can show what it would have cost


def estimate_tokens(text):
    return len(text) // 4


def fold_into_summary(summary, old_messages):
    """Ask the model to fold some old messages into the running summary."""
    lines = ""
    for old in old_messages:
        who = "Customer"
        if old["role"] != "user":
            who = "Agent"
        lines = lines + who + ": " + old["content"] + "\n"
    if summary == "":
        summary = "none yet"
    reply = model.invoke([
        {"role": "system", "content": "You keep a running summary of a support conversation. Update the "
                                      "summary with the new lines. Keep names, amounts and ticket numbers. "
                                      "Three short sentences at most."},
        {"role": "user", "content": "Summary so far: " + summary + "\n\nNew lines:\n" + lines},
    ])
    return reply.content.strip()


def respond(message, session_id):
    if session_id not in recent:
        recent[session_id] = []
        summaries[session_id] = ""
        everything[session_id] = []

    # Read the message for facts about the customer and save them (lab 05).
    profile, new_facts = update_profile(message)

    # BUILD THE PACKET.
    prompt = SYSTEM
    facts_text = profile_as_text(profile)
    if facts_text != "":
        prompt = prompt + "\n\nWhat you know about this customer:\n" + facts_text
    skill = choose_skill(chooser, skills, message)
    if skill is not None:
        prompt = prompt + "\nFollow this procedure exactly:\n\n" + skill["body"] + "\n"
    base_prompt = prompt   # everything above is needed whichever way we handle the history
    if summaries[session_id] != "":
        prompt = prompt + "\nEarlier in this conversation: " + summaries[session_id] + "\n"

    new_message = {"role": "user", "content": message}
    packet = [{"role": "system", "content": prompt}] + recent[session_id] + [new_message]

    # SEND IT.
    reply = model.invoke(packet)
    answer = reply.content.strip()

    # KEEP THE TURN.
    recent[session_id].append(new_message)
    recent[session_id].append({"role": "assistant", "content": answer})
    everything[session_id].append(new_message)
    everything[session_id].append({"role": "assistant", "content": answer})

    # If the recent list is too long, fold the oldest two messages into the summary.
    folded = False
    while len(recent[session_id]) > MAX_RECENT:
        oldest = recent[session_id][:2]
        recent[session_id] = recent[session_id][2:]
        summaries[session_id] = fold_into_summary(summaries[session_id], oldest)
        folded = True

    # SHOW THE COST. Compare what we sent with what sending everything would have cost.
    sent_text = ""
    for item in packet:
        sent_text = sent_text + item["content"]
    full_text = base_prompt
    for item in everything[session_id][:-2]:
        full_text = full_text + item["content"]
    full_text = full_text + message

    panel = "### The context packet this turn\n\n"
    panel = panel + "**1. System prompt** and **2. Profile** (" + str(len(new_facts)) + " new fact(s) saved)\n\n"
    panel = panel + "**3. Playbook (procedural memory):** "
    if skill is None:
        panel = panel + "none fitted\n\n"
    else:
        panel = panel + skill["name"] + "\n\n"
    panel = panel + "**4. Summary of older messages**\n\n"
    if summaries[session_id] == "":
        panel = panel + "- none yet (the conversation is still short)\n\n"
    else:
        panel = panel + "- " + summaries[session_id] + "\n\n"
    panel = panel + "**5. Recent messages sent word for word:** " + str(len(packet) - 2) + "\n\n"
    panel = panel + "---\n\n"
    panel = panel + "Messages so far in this session: **" + str(len(everything[session_id])) + "**\n\n"
    panel = panel + "Tokens in this packet: **about " + str(estimate_tokens(sent_text)) + "**\n\n"
    panel = panel + "Tokens if we sent EVERYTHING: **about " + str(estimate_tokens(full_text)) + "**\n\n"
    if folded:
        panel = panel + "Old messages were folded into the summary this turn.\n"
    return answer, panel


# =============================================================================
# 2. THE CHAT PAGE (Gradio)  -  the same in every lab. Skip it on your first read.
# =============================================================================
page = build_chat(
    respond,
    "07 - Capstone: build the context packet yourself",
    "Memory is what you store. Context is the slice you send.",
    steps=[
        "Say: **I am Asha, a Premium customer. My UPI payment of 12500 was debited twice on 12 November. "
        "The transaction reference is TXN99120.** Look at the panel: the Refund playbook was chosen.",
        "Chat for four or five more turns about anything: how long the refund takes, an SMS update, "
        "or a different problem such as **The mobile app is down for all users.** (a different playbook).",
        "Watch the panel. Once the chat gets long, the oldest messages are folded into a short summary, "
        "and the token count of the packet stops growing as fast as the full history would.",
        "Now ask: **What was my transaction reference and how much was it for?** It still knows, because "
        "the summary and the profile carried it forward.",
        "Change the Session box to **ticket-999** and ask: **What account type do I have?** "
        "A new conversation, but the profile still knows you.",
    ],
)
page.launch()
