"""
06 - Procedural memory: teach the agent HOW to work

LESSON: facts are what is true. Procedural memory is HOW TO BEHAVE: your playbook, your
policy, your standard operating procedure.

The nice part is that it is just a text file. Open skills/incident_triage.md and read it.
That is the whole skill. We load it into the system prompt, and the agent starts working
to your company's process instead of giving generic advice. Nothing is retrained.

Real teams have many playbooks, and you cannot paste them all into the prompt. So we show
the model a MENU (only the name and one-line description of each skill), let it pick one,
and load only that one in full. That is called progressive disclosure.

The skill code is in skills_loader.py. Open it, it is short.

The file has two blocks. Read block 1. The chat page (block 2) is the same in every lab.

Run:  uv run 06_skills.py      then open http://127.0.0.1:7860
Try:  Ask each question with the switch OFF, then ON:
        The payments API is returning 500 errors for all customers.
        I was charged twice, I want my money back.
        How many customers signed up last month?
        Is this login code safe to ship?
"""

import datetime
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

from chat_ui import build_chat
from skills_loader import choose_skill, load_skills

load_dotenv()
if not os.getenv("DEEPSEEK_API_KEY"):
    raise SystemExit("Put your DEEPSEEK_API_KEY in the .env file first.")


# =============================================================================
# 1. THE SKILLS  -  read the files, let the model choose one, load it
# =============================================================================
# The model has no clock, so we tell it today's date. Some playbooks need it (refunds: within 30 days?).
today = datetime.date.today().strftime("%d %B %Y")
SYSTEM = "You are a support assistant for SecureBank. Today is " + today + ". Reply in plain text, with no markdown symbols."

skills = load_skills()

# A small, cheap call that only has to name the winning skill.
chooser = init_chat_model("deepseek:deepseek-chat", temperature=0.0, max_tokens=30)
answerer = init_chat_model("deepseek:deepseek-chat", max_tokens=350)

checkpointer = InMemorySaver()


def respond(message, session_id, use_skills):
    # 1. CHOOSE. With the switch off, we skip this and the agent has no playbook.
    skill = None
    if use_skills is True:
        skill = choose_skill(chooser, skills, message)

    # 2. LOAD. Only the chosen skill's full procedure goes into the prompt.
    prompt = SYSTEM
    if skill is not None:
        prompt = prompt + "\n\nFollow this procedure exactly:\n\n" + skill["body"]

    # 3. ANSWER.
    agent = create_agent(model=answerer, tools=[], system_prompt=prompt, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": session_id}}
    result = agent.invoke({"messages": [{"role": "user", "content": message}]}, config)

    menu_size = 0
    all_bodies = 0
    for one in skills:
        menu_size = menu_size + len(one["name"]) + len(one["description"])
        all_bodies = all_bodies + len(one["body"])

    panel = "**Procedural memory (skill files)**\n\n"
    if use_skills is False:
        panel = panel + "Switch is OFF. No playbook was loaded.\n\nThe agent answered from general knowledge only."
    elif skill is None:
        panel = panel + "Switch is ON, but no skill fitted this message. Answering generally."
    else:
        panel = panel + "The model chose: **" + skill["name"] + "**\n\n"
        panel = panel + "File: `skills/" + skill["file"] + "`\n\n"
        panel = panel + "Loaded: **" + str(len(skill["body"])) + " characters** of procedure.\n\n"
        panel = panel + "---\n\n"
        panel = panel + "Skills available: **" + str(len(skills)) + "**\n\n"
        panel = panel + "The model saw only the menu: " + str(menu_size) + " characters.\n\n"
        panel = panel + "Pasting every procedure would have cost: " + str(all_bodies) + " characters."
    return result["messages"][-1].content.strip(), panel


print("Skills found:", ", ".join([one["name"] for one in skills]))


# =============================================================================
# 2. THE CHAT PAGE (Gradio)  -  the same in every lab. Skip it on your first read.
# =============================================================================
page = build_chat(
    respond,
    "06 - Procedural memory: teach the agent how to work",
    "A skill is a plain markdown file with your procedure in it. The agent picks the right one.",
    steps=[
        "Leave the switch **OFF**. Ask: **The payments API is returning 500 errors for all customers.** "
        "The answer is sensible, but it is generic advice.",
        "Turn the switch **ON** and ask the very same question again. Now you get a severity, an impact line, "
        "a next step and an owner, because it follows skills/incident_triage.md.",
        "Keep the switch ON and ask: **I was charged twice, I want my money back.** A different skill is chosen. "
        "Look at the panel: only ONE procedure was loaded.",
        "Try: **How many customers signed up last month?** and **Is this login code safe to ship?** "
        "Two more skills, picked automatically.",
        "Open **skills/incident_triage.md**, change a step, save, restart the lab and ask again. "
        "The behaviour changes with the file. No retraining. Add your own file to the skills folder and it joins the menu.",
    ],
    switch_label="Load skills (the model picks one)",
)
page.launch()
