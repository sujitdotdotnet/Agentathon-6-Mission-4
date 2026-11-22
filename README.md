# Mission 4 - Memory and Context

A language model remembers nothing. Every call starts from zero.

So how do ChatGPT and Claude seem to remember you? Someone built a memory layer around the
model. In this mission you build that layer yourself, one small piece at a time, and watch it
work in your browser. Every lab is a Gradio chat page with a panel that shows what the model
was actually sent.

## Setup (do once)

```bash
uv sync
```

Copy `.env.example` to `.env` and put your DeepSeek key in it:

```text
DEEPSEEK_API_KEY=your-deepseek-key-here
```

Then run the check. Do not start the labs until it prints ALL GOOD.

```bash
uv run 00_setup_check.py
```

## The labs (run in order)

Each lab opens a chat page. Run it, then open http://127.0.0.1:7860. Stop it with **Ctrl+C**
before you start the next one. Every page has a **How to use this lab** box with the steps.

| File | The one idea it teaches |
|---|---|
| `01_agent_forgets.py` | The model is stateless. It forgets everything between turns. |
| `02_message_list.py` | A conversation is a list. Keep it yourself and send all of it every turn. |
| `03_checkpointer.py` | A LangGraph checkpointer keeps the list for you. `thread_id` names the conversation. |
| `04_durable_sessions.py` | Save it to SQLite and the memory survives a restart. Many conversations, one file. |
| `05_profile_memory.py` | A profile of the customer follows them into every new conversation. |
| `06_skills.py` | Procedural memory. A markdown playbook changes how the agent works, and the model picks the right one. |
| `07_context_packet.py` | Capstone. Memory is what you store, context is what you send. Build the packet yourself. |

```bash
uv run 01_agent_forgets.py
```

## The kinds of memory you build

| Kind | Plain meaning | Where it lives here |
|---|---|---|
| Conversation | what we just said | a list, then a checkpointer, then SQLite (labs 02 to 04) |
| Profile | facts about the person | `profile.json` (lab 05) |
| Procedural | how to do the job properly | markdown files in `skills/` (lab 06) |

## The files you do not run

| File | What it is for |
|---|---|
| `chat_ui.py` | The Gradio chat page every lab uses. All the Gradio code is here, so each lab shows only memory. |
| `profile_store.py` | Reads facts out of a message into a fixed set of fields and saves them in `profile.json`. |
| `skills_loader.py` | Reads the playbooks in `skills/` and lets the model choose one from a menu. |
| `skills/*.md` | Four playbooks: incident triage, refund policy, SQL helper, code review. Open one, it is plain English. |

## Start clean

Delete `conversations.sqlite` and `profile.json`. They are recreated on the next run.

## Troubleshooting

**`uv` is not recognised.** Install it (`pip install uv`), then reopen the terminal.

**`No pyproject.toml found`.** You are in the wrong folder. Go to the folder that holds these files.

**Nothing works and the key looks fine.** Check that `.env` is in this folder, next to the lab files.

**Port 7860 is busy.** The previous lab is still running. Press Ctrl+C in its terminal.
