"""
skills_loader - Read the skill files in the skills folder, and choose the right one

A skill file is PROCEDURAL memory written in plain markdown:

    name: Incident Triage
    description: Use when the user reports an outage ...
                                        <- blank line
    Procedure:
    1. ...

The name and the description are the SMALL part. They are all we show the model when it
is choosing a skill. The procedure underneath is the BIG part, and we load it only once a
skill has been chosen. That is progressive disclosure, and it is how coding assistants
load their skills too.

You do not run this file. Labs 06 and 07 import it.
"""

import os

SKILLS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills")


def read_skill(path):
    """Read one skill file. Returns a dictionary with name, description and body."""
    handle = open(path, "r", encoding="utf-8")
    lines = handle.readlines()
    handle.close()

    name = ""
    description = ""
    body_lines = []
    header_done = False

    for line in lines:
        if header_done is False and line.lower().startswith("name:"):
            name = line.split(":", 1)[1].strip()
        elif header_done is False and line.lower().startswith("description:"):
            description = line.split(":", 1)[1].strip()
        elif header_done is False and line.strip() == "" and name != "" and description != "":
            header_done = True
        else:
            if header_done is True:
                body_lines.append(line)

    return {"name": name, "description": description, "body": "".join(body_lines).strip(), "file": os.path.basename(path)}


def load_skills():
    """Read every skill file in the skills folder."""
    skills = []
    for filename in sorted(os.listdir(SKILLS_FOLDER)):
        if filename.endswith(".md"):
            skills.append(read_skill(os.path.join(SKILLS_FOLDER, filename)))
    return skills


def find_skill(skills, name):
    """Find a skill by its name. Returns None if there is no match."""
    wanted = name.strip().lower()
    for skill in skills:
        if skill["name"].lower() == wanted:
            return skill
    for skill in skills:
        if wanted != "" and wanted in skill["name"].lower():
            return skill
    return None


def choose_skill(model, skills, message):
    """
    Show the model a MENU (name and description of every skill, nothing more) and let it
    pick the one that fits the message. Returns the skill, or None if nothing fits.

    With four skills the menu is tiny. With hundreds you would first shortlist by meaning
    (embeddings), then let the model pick from the shortlist. The idea is the same.
    """
    menu = ""
    for skill in skills:
        menu = menu + "- " + skill["name"] + ": " + skill["description"] + "\n"

    reply = model.invoke([
        {"role": "system", "content": "You choose which playbook fits the user's message.\n"
                                      "Candidates, as name: when to use it.\n\n" + menu + "\n"
                                      "Reply with the NAME of the best one, exactly as written. "
                                      "If none of them fit, reply with exactly: NONE"},
        {"role": "user", "content": message},
    ])
    picked = reply.content.strip()
    if picked.upper().startswith("NONE"):
        return None
    return find_skill(skills, picked)
