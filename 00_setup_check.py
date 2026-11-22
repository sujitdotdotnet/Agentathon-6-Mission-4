"""
00 - Setup Check  (RUN THIS FIRST)

Proves your machine is ready before the labs: Python, the packages, your key,
and one real call to the model. If something is wrong, it tells you what to fix.

Run:  uv run 00_setup_check.py
"""

import os
import sys

print("====================================================================")
print("MISSION 4 - SETUP CHECK")
print("====================================================================")

problems = []

# 1. Python version
if sys.version_info < (3, 11):
    problems.append("Python 3.11 or newer is needed. You have " + sys.version.split()[0] + ".")
    print("[!!] Python", sys.version.split()[0], "is too old.")
else:
    print("[OK] Python version is fine.")

# 2. Packages
try:
    from dotenv import load_dotenv
    import gradio
    import langchain
    import langgraph
    import pydantic
    from langgraph.checkpoint.sqlite import SqliteSaver
    print("[OK] Packages are installed.")
except Exception as error:
    print("[!!] Packages are missing:", error)
    print("Run  uv sync  in this folder, then run this file again.")
    raise SystemExit()

load_dotenv()

# 3. The .env file and the key
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    print("[OK] Found the .env file in this folder.")
else:
    problems.append("No .env file in this folder. Copy .env.example to .env.")
    print("[!!] No .env file in this folder.")

key = os.getenv("DEEPSEEK_API_KEY", "").strip()
if key != "" and key != "your-deepseek-key-here":
    print("[OK] DEEPSEEK_API_KEY found.")
else:
    problems.append("DEEPSEEK_API_KEY is missing. Put your key in the .env file.")
    print("[!!] DEEPSEEK_API_KEY is missing.")

# 4. One real call to the model
if len(problems) == 0:
    print("[..] Sending one small message to DeepSeek ...")
    try:
        from langchain.chat_models import init_chat_model
        model = init_chat_model("deepseek:deepseek-chat", max_tokens=5)
        reply = model.invoke("Reply with exactly: ready")
        print("[OK] DeepSeek replied:", reply.content.strip())
    except Exception as error:
        problems.append("The call to DeepSeek failed: " + str(error))
        print("[!!] The call to DeepSeek failed.")

print("====================================================================")
if len(problems) == 0:
    print("ALL GOOD - you are ready. Open 01_agent_forgets.py next.")
else:
    print("PLEASE FIX THESE:")
    number = 1
    for problem in problems:
        print("  " + str(number) + ". " + problem)
        number = number + 1
print("====================================================================")
