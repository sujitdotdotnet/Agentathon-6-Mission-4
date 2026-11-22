"""
profile_store - a small, structured profile of the customer, saved in a file.

Conversation memory belongs to one conversation. A PROFILE belongs to the person:
their name, role, account type and how they like to be answered. It should follow
them into every new conversation.

We keep it as a plain dictionary saved to profile.json. To fill it, we ask the model
to read the customer's message and return a Pydantic object with fixed fields.
(Same idea as structured output in Mission 1.)

In a real app you would keep one profile per user id, in a database.
Here there is one demo customer, so there is one file.

You do not run this file. Labs 05 and 06 import it.
"""

import json
import os

from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

PROFILE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile.json")
FIELDS = ["name", "role", "account_type", "preference"]


class Profile(BaseModel):
    """The fields we want the model to fill in. An empty string means 'not stated'."""

    name: str = Field(default="", description="The customer's first name, if they said it.")
    role: str = Field(default="", description="The customer's job or role, if they said it.")
    account_type: str = Field(default="", description="Their bank account type, for example Premium or Savings.")
    preference: str = Field(default="", description="How they like to be answered, for example short answers.")


def load_profile():
    """Read the saved profile. If there is none yet, return an empty one."""
    profile = {}
    for field in FIELDS:
        profile[field] = ""
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r", encoding="utf-8") as file:
            saved = json.load(file)
        for field in FIELDS:
            profile[field] = saved.get(field, "")
    return profile


def save_profile(profile):
    with open(PROFILE_FILE, "w", encoding="utf-8") as file:
        json.dump(profile, file, indent=2)


def find_new_facts(message):
    """Ask the model what this message tells us about the customer. Returns only the fields it found."""
    model = init_chat_model("deepseek:deepseek-chat", temperature=0.0, max_tokens=150)
    extractor = model.with_structured_output(Profile)
    result = extractor.invoke([
        {"role": "system", "content": "Read the customer's message. Fill in only what they clearly state "
                                      "about themselves. Leave every other field empty. Never guess."},
        {"role": "user", "content": message},
    ])
    found = {}
    if result is None:
        return found
    for field in FIELDS:
        value = getattr(result, field).strip()
        if value != "":
            found[field] = value
    return found


def update_profile(message):
    """Read the message, merge any new facts into the saved profile. Returns (profile, new_facts)."""
    new_facts = find_new_facts(message)
    profile = load_profile()
    for field in new_facts:
        profile[field] = new_facts[field]
    if len(new_facts) > 0:
        save_profile(profile)
    return profile, new_facts


def profile_as_text(profile):
    """The profile as bullet lines, ready to put into a prompt. Empty string if nothing is known."""
    lines = ""
    for field in FIELDS:
        if profile[field] != "":
            lines = lines + "- " + field + ": " + profile[field] + "\n"
    return lines
