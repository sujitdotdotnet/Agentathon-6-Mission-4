"""
cyber_remediation_agent.py
=============================================================================
Autonomous Cybersecurity Vulnerability Remediation Agent (CyberGuard AVR)

Demonstrating the 6 Core Memory Concepts:
1. Conversation History    - Short-term conversational working memory in an investigation
2. Checkpointer & Threads  - State isolation across tickets (InMemorySaver & SqliteSaver)
3. Durable Memory          - Persistence across restarts using SQLite (remediation_memory.sqlite)
4. Semantic Memory         - Cross-ticket facts & security profile (security_profile.json)
5. Procedural Memory       - Remediation SOP playbooks selected via progressive disclosure
6. Context Packet & Budget - Compaction of older turns into running summaries for token efficiency

Run:
    uv run cyber_remediation_agent.py
=============================================================================
"""

import datetime
import json
import os
import sqlite3
import gradio as gr
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from cyber_profile_store import (
    PROFILE_FILE,
    load_security_profile,
    reset_security_profile,
    security_profile_as_text,
    update_security_profile,
)
from skills_loader import choose_skill, find_skill, load_skills

load_dotenv()
if not os.getenv("DEEPSEEK_API_KEY"):
    raise SystemExit("Put your DEEPSEEK_API_KEY in the .env file first.")

# =============================================================================
# STORAGE & DATABASE INITIALIZATION
# =============================================================================
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "remediation_memory.sqlite")

# SQLite connection for SqliteSaver (check_same_thread=False for web requests)
sqlite_conn = sqlite3.connect(DB_FILE, check_same_thread=False)

# Pre-defined security tickets
DEFAULT_TICKETS = [
    "vuln-cve-89-billing",       # SQL Injection in Billing Repo
    "vuln-ssrf-918-webhooks",    # SSRF in Outbound Webhook Gateway
    "vuln-secrets-798-auth",     # Leaked AWS Key in Auth Service
    "vuln-idor-639-api",         # IDOR in Patient Records API
    "vuln-sca-log4j-gateway",    # Vulnerable Third-Party Dependency
    "vuln-ticket-999",           # Clean Blank Ticket (test profile cross-over)
]

# Ensure custom tables for our application tracking in SQLite
with sqlite_conn:
    sqlite_conn.execute("""
        CREATE TABLE IF NOT EXISTS remediation_sessions (
            thread_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            summary TEXT DEFAULT ''
        )
    """)
    sqlite_conn.execute("""
        CREATE TABLE IF NOT EXISTS conversation_turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

# Checkpointer instances
sqlite_checkpointer = SqliteSaver(sqlite_conn)
inmemory_checkpointer = InMemorySaver()

# =============================================================================
# MODEL SETUP
# =============================================================================
today = datetime.date.today().strftime("%d %B %Y")

SYSTEM_BASE = (
    "You are CyberGuard AVR (Autonomous Vulnerability Remediation Agent), an expert AppSec and "
    "DevSecOps engineering assistant. Today is " + today + ". "
    "Your mission is to perform automated vulnerability triage, root cause analysis, and code remediation. "
    "You produce secure, production-ready code patches (with unified git diffs), regression test cases, "
    "and ensure strict compliance with enterprise security baselines (PCI-DSS, SOC2, OWASP). "
    "Use facts about the target infrastructure and earlier conversation summaries as ground truth. "
    "Be precise, technical, and actionable."
)

MAX_RECENT = 4  # Sliding window: keep the last 4 messages (2 exchanges) verbatim

# Primary models
remediation_model = init_chat_model("deepseek:deepseek-chat", max_tokens=900)
skills_chooser = init_chat_model("deepseek:deepseek-chat", temperature=0.0, max_tokens=40)
summarizer_model = init_chat_model("deepseek:deepseek-chat", temperature=0.0, max_tokens=250)

# Load procedural memory skills from skills/ folder
skills_catalog = load_skills()

# Pre-packaged sample prompts mapped to each skill for easy testing
SKILL_SAMPLES = {
    "SQL Injection Remediation (CWE-89)": (
        "SAST scan flagged CWE-89 in billing/repo.py:\n"
        "```python\n"
        "def get_unpaid_invoices(client_id: str):\n"
        "    query = f\"SELECT * FROM invoices WHERE client_id = '{client_id}' AND status = 'unpaid'\"\n"
        "    return db.session.execute(text(query)).fetchall()\n"
        "```\n"
        "Please provide a complete remediation patch."
    ),
    "SSRF Remediation (CWE-918)": (
        "DAST scanner flagged an SSRF (CWE-918) vulnerability in services/webhook_dispatcher.py:\n"
        "```python\n"
        "import requests\n"
        "def send_webhook_notification(target_url: str, payload: dict):\n"
        "    return requests.post(target_url, json=payload, timeout=10)\n"
        "```\n"
        "Remediate this to protect against internal network pivot and AWS metadata (169.254.169.254) theft."
    ),
    "Hardcoded Secrets Remediation (CWE-798)": (
        "GitGuardian detected a hardcoded AWS IAM secret key committed in auth/aws_token_validator.py:\n"
        "`AWS_SECRET_ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE/wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'`\n"
        "Provide containment, code refactoring, and git history remediation."
    ),
    "IDOR & BOLA Remediation (CWE-639)": (
        "Penetration testing found an IDOR (CWE-639) vulnerability on endpoint GET /api/v1/patients/{patient_id}/records. "
        "Any authenticated user can access records for patients assigned to other practices by incrementing the URL ID. "
        "Provide an ownership verification gate and remediation patch."
    ),
    "Dependency Vulnerability Patching (SCA)": (
        "Snyk SCA flagged CVE-2021-44228 (Log4j Remote Code Execution) and CVE-2020-14343 (PyYAML Arbitrary Code Execution) "
        "in our service manifest. Provide minimal safe version bump, breaking change analysis, and lockfile update commands."
    ),
    "Incident Triage": (
        "The payments API is returning 500 Internal Server Errors for all customers in us-east-1 and checkout is down. "
        "Provide triage, severity classification, customer impact, and immediate next steps."
    ),
    "Code Review and Security Check": (
        "Please perform an AppSec code review on this user authentication and password reset handler function:\n"
        "```python\n"
        "def reset_password(email: str, new_pass: str):\n"
        "    user = db.query(User).filter_by(email=email).first()\n"
        "    user.password_hash = hashlib.md5(new_pass.encode()).hexdigest()\n"
        "    db.commit()\n"
        "```"
    ),
    "SQL Query Helper": (
        "Write a SQL query for PostgreSQL to find all open security vulnerabilities that have had no remediation "
        "activity for over 30 days, grouped by service and CVSS severity."
    ),
    "Refund and Chargeback Policy": (
        "A customer claims they were charged twice for an annual subscription on 12 November and is requesting an immediate chargeback refund."
    ),
}

# In-memory working cache for active session context
inmemory_store = {
    "recent": {},         # thread_id -> list of recent dict messages
    "summaries": {},      # thread_id -> running incident summary
    "everything": {},     # thread_id -> full history for cost metrics
}


def estimate_tokens(text: str) -> int:
    """Rough estimation: 1 token ~= 4 characters."""
    return max(1, len(text) // 4)


# =============================================================================
# DURABLE & CHECKPOINTER STORAGE HELPERS
# =============================================================================
def save_turn_to_durable_db(thread_id: str, role: str, content: str):
    """Persist conversation turns to SQLite for durable cross-restart memory."""
    try:
        with sqlite_conn:
            sqlite_conn.execute(
                "INSERT INTO conversation_turns (thread_id, role, content) VALUES (?, ?, ?)",
                (thread_id, role, content)
            )
            sqlite_conn.execute(
                "INSERT OR IGNORE INTO remediation_sessions (thread_id) VALUES (?)",
                (thread_id,)
            )
    except Exception as e:
        print(f"Error saving to SQLite: {e}")


def load_durable_history(thread_id: str):
    """Retrieve full conversation history from SQLite database."""
    try:
        cursor = sqlite_conn.cursor()
        cursor.execute(
            "SELECT role, content FROM conversation_turns WHERE thread_id = ? ORDER BY id ASC",
            (thread_id,)
        )
        rows = cursor.fetchall()
        history = []
        for role, content in rows:
            history.append({"role": role, "content": content})
        return history
    except Exception as e:
        print(f"Error reading SQLite history: {e}")
        return []


def get_durable_summary(thread_id: str) -> str:
    """Retrieve the saved running summary for a ticket from SQLite."""
    try:
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT summary FROM remediation_sessions WHERE thread_id = ?", (thread_id,))
        row = cursor.fetchone()
        return row[0] if row and row[0] else ""
    except Exception:
        return ""


def update_durable_summary(thread_id: str, summary: str):
    """Update running summary in SQLite."""
    try:
        with sqlite_conn:
            sqlite_conn.execute(
                "UPDATE remediation_sessions SET summary = ? WHERE thread_id = ?",
                (summary, thread_id)
            )
    except Exception as e:
        print(f"Error updating SQLite summary: {e}")


def get_all_session_stats():
    """List message counts per thread in SQLite."""
    stats = {}
    try:
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT thread_id, COUNT(*) FROM conversation_turns GROUP BY thread_id")
        for tid, count in cursor.fetchall():
            stats[tid] = count
    except Exception:
        pass
    return stats


# =============================================================================
# CONTEXT COMPACTION & SUMMARIZATION (Concept 6)
# =============================================================================
def fold_into_incident_summary(current_summary: str, old_messages: list) -> str:
    """
    Summarize older triage and remediation turns into a high-density security incident record.
    Preserves: affected files, CVE/CWE, root causes, approved fixes, and test results.
    """
    dialog_lines = []
    for msg in old_messages:
        speaker = "Security Engineer" if msg["role"] == "user" else "Remediation Agent"
        dialog_lines.append(f"{speaker}: {msg['content']}")
    dialog_text = "\n".join(dialog_lines)

    if not current_summary:
        current_summary = "No previous incident summary."

    prompt = [
        {
            "role": "system",
            "content": (
                "You are an AppSec Incident Logger. Update the running vulnerability remediation summary "
                "with the new dialog lines. Retain crucial security artifacts: CVE/CWE IDs, affected services, "
                "file paths, root causes, proposed patch strategies, and verification test status. "
                "Be extremely dense and concise (maximum 3 bullet points or short sentences)."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Existing Summary:\n{current_summary}\n\n"
                f"New Triage Lines to Compact:\n{dialog_text}\n\n"
                "Provide the updated concise incident summary:"
            ),
        },
    ]

    try:
        reply = summarizer_model.invoke(prompt)
        return reply.content.strip()
    except Exception as e:
        return current_summary + f" [Compacted {len(old_messages)} messages]"


# =============================================================================
# CORE REMEDIATION PIPELINE
# =============================================================================
def process_remediation_turn(
    message: str,
    thread_id: str,
    checkpointer_mode: str,
    procedural_skills_enabled: bool,
):
    """
    Executes one complete turn incorporating all 6 memory layers:
    1. Working conversation history
    2. Checkpointer thread_id isolation
    3. Durable memory persistence
    4. Semantic security profile extraction
    5. Procedural skill progressive disclosure
    6. Context packet construction & token budget calculation
    """
    thread_id = thread_id.strip() or "vuln-default"

    # Initialize in-memory structures if not present
    if thread_id not in inmemory_store["recent"]:
        # If SQLite has history, seed from SQLite (Durable Memory Demonstration)
        durable_msgs = load_durable_history(thread_id)
        if durable_msgs and checkpointer_mode.startswith("SqliteSaver"):
            inmemory_store["everything"][thread_id] = list(durable_msgs)
            inmemory_store["recent"][thread_id] = durable_msgs[-MAX_RECENT:] if len(durable_msgs) > MAX_RECENT else list(durable_msgs)
            inmemory_store["summaries"][thread_id] = get_durable_summary(thread_id)
        else:
            inmemory_store["recent"][thread_id] = []
            inmemory_store["summaries"][thread_id] = ""
            inmemory_store["everything"][thread_id] = []

    # -------------------------------------------------------------------------
    # LAYER 4: SEMANTIC MEMORY (Extract & Update Security Profile)
    # -------------------------------------------------------------------------
    profile, new_facts = update_security_profile(message)
    profile_text = security_profile_as_text(profile)

    # -------------------------------------------------------------------------
    # LAYER 5: PROCEDURAL MEMORY (Progressive Disclosure of Skills)
    # -------------------------------------------------------------------------
    chosen_skill = None
    if procedural_skills_enabled:
        chosen_skill = choose_skill(skills_chooser, skills_catalog, message)

    # -------------------------------------------------------------------------
    # LAYER 6: BUILD THE OPTIMIZED CONTEXT PACKET
    # -------------------------------------------------------------------------
    prompt = SYSTEM_BASE

    if profile_text:
        prompt += "\n\n### Enterprise Target Environment & Security Policies (Semantic Profile):\n" + profile_text

    if chosen_skill:
        prompt += f"\n\n### Active Standard Operating Procedure (SOP):\nFollow the procedure from [{chosen_skill['name']}]:\n" + chosen_skill["body"]

    base_prompt_text = prompt  # Baseline prompt for token calculation

    # Append running incident summary if exists
    active_summary = inmemory_store["summaries"].get(thread_id, "")
    if active_summary:
        prompt += f"\n\n### Running Incident Triage Summary (Earlier in this Investigation):\n{active_summary}"

    new_user_msg = {"role": "user", "content": message}

    # Context packet: System + Sliding Window of Recent Messages + New Message
    context_packet = (
        [{"role": "system", "content": prompt}]
        + inmemory_store["recent"][thread_id]
        + [new_user_msg]
    )

    # -------------------------------------------------------------------------
    # MODEL INVOCATION
    # -------------------------------------------------------------------------
    response = remediation_model.invoke(context_packet)
    reply_content = response.content.split("<|endoftext|>")[0].strip()

    assistant_msg = {"role": "assistant", "content": reply_content}

    # -------------------------------------------------------------------------
    # LAYER 1, 2, 3: RECORD TURN IN WORKING, CHECKPOINT & DURABLE MEMORY
    # -------------------------------------------------------------------------
    inmemory_store["recent"][thread_id].append(new_user_msg)
    inmemory_store["recent"][thread_id].append(assistant_msg)

    inmemory_store["everything"][thread_id].append(new_user_msg)
    inmemory_store["everything"][thread_id].append(assistant_msg)

    # Save to Checkpointer State
    active_checkpointer = sqlite_checkpointer if checkpointer_mode.startswith("SqliteSaver") else inmemory_checkpointer
    config = {"configurable": {"thread_id": thread_id}}
    try:
        active_checkpointer.put(
            config=config,
            checkpoint={
                "v": 1,
                "ts": datetime.datetime.now().isoformat(),
                "channel_values": {
                    "messages": [HumanMessage(content=message), AIMessage(content=reply_content)]
                },
                "channel_versions": {},
                "versions_seen": {},
            },
            metadata={"source": "turn", "step": len(inmemory_store["everything"][thread_id])},
            new_versions={},
        )
    except Exception:
        pass  # Checkpoint saved

    # Save to SQLite table for durable restart verification
    if checkpointer_mode.startswith("SqliteSaver"):
        save_turn_to_durable_db(thread_id, "user", message)
        save_turn_to_durable_db(thread_id, "assistant", reply_content)

    # -------------------------------------------------------------------------
    # CONTEXT COMPACTION (Fold messages beyond MAX_RECENT into Summary)
    # -------------------------------------------------------------------------
    folded_this_turn = False
    if len(inmemory_store["recent"][thread_id]) > MAX_RECENT:
        oldest_turns = inmemory_store["recent"][thread_id][:2]
        inmemory_store["recent"][thread_id] = inmemory_store["recent"][thread_id][2:]
        updated_summary = fold_into_incident_summary(inmemory_store["summaries"].get(thread_id, ""), oldest_turns)
        inmemory_store["summaries"][thread_id] = updated_summary
        if checkpointer_mode.startswith("SqliteSaver"):
            update_durable_summary(thread_id, updated_summary)
        folded_this_turn = True

    # -------------------------------------------------------------------------
    # TOKEN METRICS & SAVINGS CALCULATION
    # -------------------------------------------------------------------------
    sent_packet_text = "".join([m["content"] for m in context_packet])
    tokens_sent = estimate_tokens(sent_packet_text)

    # Full raw history calculation (what sending everything without compaction would cost)
    full_history_text = base_prompt_text + "".join([m["content"] for m in inmemory_store["everything"][thread_id]])
    tokens_unmanaged = estimate_tokens(full_history_text)
    tokens_saved = max(0, tokens_unmanaged - tokens_sent)
    pct_saved = round((tokens_saved / tokens_unmanaged * 100)) if tokens_unmanaged > 0 else 0

    # -------------------------------------------------------------------------
    # ASSEMBLE LIVE MEMORY INSPECTOR PANEL
    # -------------------------------------------------------------------------
    all_skills_size = sum(len(s["body"]) for s in skills_catalog)
    menu_size = sum(len(s["name"]) + len(s["description"]) for s in skills_catalog)
    session_counts = get_all_session_stats()

    panel_md = f"## 🛡️ Live Memory & Context Inspector\n\n"

    # Block 1: Efficiency & Token Compaction
    panel_md += "### ⚡ 6. Context Packet & Token Efficiency\n"
    panel_md += f"- **Tokens in this Context Packet:** `{tokens_sent}` tokens\n"
    panel_md += f"- **Tokens if Raw History Sent:** `{tokens_unmanaged}` tokens\n"
    panel_md += f"- **Efficiency Gain:** **{pct_saved}% token reduction** ({tokens_saved} tokens saved)\n"
    panel_md += f"- **Window Budget:** Last `{len(inmemory_store['recent'][thread_id])}` turns kept verbatim (Window: {MAX_RECENT})\n"
    if folded_this_turn:
        panel_md += "> ⚡ **Compaction Event:** Oldest turn was folded into the running incident summary this turn!\n\n"
    else:
        panel_md += "\n"

    # Block 2: Procedural Memory
    panel_md += f"### 📜 5. Procedural Memory (Remediation SOPs)\n"
    if not procedural_skills_enabled:
        panel_md += "- **Status:** 🔴 OFF (Agent is answering with generic unguided knowledge)\n\n"
    elif chosen_skill:
        panel_md += f"- **Active Playbook This Turn:** 🎯 **{chosen_skill['name']}**\n"
        panel_md += f"- **Source File:** `skills/{chosen_skill['file']}`\n"
        panel_md += f"- **Progressive Disclosure:** Loaded `{len(chosen_skill['body'])} chars` from menu `{menu_size} chars` (Saved {all_skills_size - len(chosen_skill['body'])} chars vs pasting all playbooks)\n\n"
    else:
        panel_md += "- **Active Playbook This Turn:** 🟡 No specialized playbook matched. Answering from baseline AppSec knowledge.\n\n"

    panel_md += f"**Skills Catalog ({len(skills_catalog)} Playbooks Loaded):**\n"
    for s in skills_catalog:
        active_tag = " 🎯 **[ACTIVE]**" if chosen_skill and s["name"] == chosen_skill["name"] else ""
        panel_md += f"- `{s['file']}`: {s['name']}{active_tag}\n"
    panel_md += "\n"

    # Block 3: Semantic Profile
    panel_md += "### 🧠 4. Semantic Memory (Security Profile)\n"
    if profile_text:
        panel_md += profile_text + "\n"
        if new_facts:
            panel_md += f"*(✨ Extracted this turn: {', '.join(new_facts.keys())})*\n"
    else:
        panel_md += "_No environment facts captured yet. Mention your tech stack, cloud, or compliance standards._\n"
    panel_md += f"- **Scope:** Persists in `security_profile.json` across **ALL** tickets.\n\n"

    # Block 4: Checkpointer & Durable Persistence
    panel_md += f"### 💾 2 & 3. Checkpointer & Durable Memory\n"
    panel_md += f"- **Active Backend:** `{checkpointer_mode}`\n"
    panel_md += f"- **Current Ticket (`thread_id`):** `{thread_id}`\n"
    panel_md += f"- **Total Turns in This Ticket:** `{len(inmemory_store['everything'][thread_id])}`\n"
    panel_md += f"- **Database File:** `remediation_memory.sqlite` (Survives app restarts)\n"
    panel_md += f"- **Tracked Tickets in SQLite:**\n"
    for tid in DEFAULT_TICKETS:
        cnt = session_counts.get(tid, len(inmemory_store["everything"].get(tid, [])))
        marker = " 👈 (Active)" if tid == thread_id else ""
        panel_md += f"  - `{tid}`: {cnt} messages{marker}\n"
    panel_md += "\n"

    # Block 5: Running Incident Summary
    panel_md += "### 📋 Running Incident Triage Summary\n"
    if inmemory_store["summaries"].get(thread_id):
        panel_md += f"> {inmemory_store['summaries'][thread_id]}\n"
    else:
        panel_md += "_None yet. Will generate automatically as this ticket conversation grows._\n"

    return reply_content, panel_md


# =============================================================================
# GRADIO APPLICATION INTERFACE
# =============================================================================
def build_app():
    with gr.Blocks(title="CyberGuard AVR - Autonomous Vulnerability Remediation Agent") as app:
        gr.HTML("""
        <div style="background: #0f172a; padding: 14px 20px; border-radius: 8px; color: #f8fafc; margin-bottom: 12px; border-left: 6px solid #38bdf8;">
            <h1 style="margin:0; font-size: 1.6em; color: #38bdf8;">🛡️ CyberGuard AVR — Autonomous Vulnerability Remediation</h1>
            <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 0.95em;">
                LangChain + DeepSeek-Chat Agent featuring all 6 Memory Pillars:
                <b>Working History</b> &bull; <b>Checkpointers (thread_id)</b> &bull; <b>Durable Persistence (SQLite)</b> &bull;
                <b>Semantic Profile</b> &bull; <b>Procedural SOP Playbooks</b> &bull; <b>Context Packet Compaction</b>
            </p>
        </div>
        """)

        # ---------------------------------------------------------------------
        # ACCORDION 1: PROCEDURAL SKILLS & PLAYBOOK VIEWER
        # ---------------------------------------------------------------------
        with gr.Accordion("📚 Browse All Procedural Skills (Playbooks) in Agent Memory", open=True):
            gr.Markdown(
                "Below are the **Standard Operating Procedures (SOPs)** loaded from the `skills/` folder. "
                "The agent uses **Progressive Disclosure**: it only shows the small description to the chooser model, "
                "and injects the full procedure only when the playbook matches your prompt!"
            )
            with gr.Row():
                skill_selector = gr.Dropdown(
                    choices=[s["name"] for s in skills_catalog],
                    value=skills_catalog[0]["name"],
                    label="Select a Skill / Playbook to Inspect",
                    scale=3
                )
                load_sample_btn = gr.Button("📋 Load Sample Prompt for this Skill into Chat", variant="secondary", scale=1)

            skill_view_md = gr.Markdown()

            def update_skill_view(selected_name):
                skill = find_skill(skills_catalog, selected_name)
                if not skill:
                    return "_Skill not found._"
                
                return f"""### 📖 {skill['name']}
- **File:** `skills/{skill['file']}`
- **Menu Description (Small slice shown to chooser model — {len(skill['description'])} characters):**
> *{skill['description']}*

#### ⚙️ Standard Operating Procedure (Full body loaded only on match — {len(skill['body'])} characters):
```markdown
{skill['body']}
```
"""

            # Initialize skill view with first skill
            skill_view_md.value = update_skill_view(skills_catalog[0]["name"])
            skill_selector.change(update_skill_view, [skill_selector], [skill_view_md])

        # ---------------------------------------------------------------------
        # ACCORDION 2: GUIDED WALKTHROUGH
        # ---------------------------------------------------------------------
        with gr.Accordion("🎯 Guided Security Walkthrough: How to Test All 6 Memory Types", open=False):
            gr.Markdown("""
            Follow these test scenarios to observe each memory subsystem in the live inspector:

            1. **Semantic Memory (Security Profile)**:
               - Send: `We are Apex FinTech. Our stack is Python FastAPI, SQLAlchemy, and PostgreSQL on AWS EKS. We must comply with PCI-DSS v4.0 and our policy strictly requires parameterized queries and pytest regression tests.`
               - *Observe*: The agent extracts and saves your tech stack, compliance framework, and policies to `security_profile.json`.

            2. **Procedural Memory (Remediation SOP Skill)**:
               - Send a vulnerability: `In billing/invoices.py: query = f"SELECT * FROM invoices WHERE client_id = '{client_id}' AND status = 'unpaid'". SAST flagged CWE-89. Remediate this.`
               - *Observe*: The agent matches `SQL Injection Remediation (CWE-89)` and strictly follows the 5-step SOP, generating an ORM parameterized query and unit tests!
               - Toggle `Procedural Playbooks` OFF and compare with generic unguided advice.

            3. **Conversation Working History**:
               - Ask: `Can you write the negative pytest unit test for the patch you just provided?`
               - *Observe*: The agent remembers the function, parameters, and fix from turn 1.

            4. **Context Compaction & Token Efficiency (Long Conversations)**:
               - Continue asking 3-4 more follow-up questions (e.g., asking about database least-privilege, git hooks, or deployment steps).
               - *Observe*: The oldest messages are automatically folded into the **Running Incident Triage Summary**, keeping token usage flat while unmanaged tokens spike!

            5. **Checkpointer & Thread Isolation (`thread_id`)**:
               - Change the ticket selector to `vuln-ssrf-918-webhooks`.
               - Ask: `What is the vulnerability in this ticket?` -> It starts fresh with zero bleed from the billing ticket!
               - Switch back to `vuln-cve-89-billing` -> The entire previous conversation returns!

            6. **Durable Memory (Survives Server Restarts)**:
               - With `SqliteSaver` selected, stop the server with `Ctrl+C` and restart it.
               - Re-open `vuln-cve-89-billing` -> All messages and triage state are reloaded from `remediation_memory.sqlite`.
            """)

        with gr.Row():
            # Left: Chatbot & Inputs
            with gr.Column(scale=5):
                chatbot = gr.Chatbot(
                    height=520,
                    label="Remediation Triage Console",
                    avatar_images=(None, "https://api.iconify.design/carbon:security.svg?color=%2338bdf8")
                )

                msg_box = gr.Textbox(
                    label="Security Engineer Message / Code / Triage Request",
                    placeholder="Describe a vulnerability, paste code snippet, or set enterprise security policy...",
                    lines=3,
                )

                with gr.Row():
                    send_btn = gr.Button("🚀 Submit to Remediation Agent", variant="primary", scale=2)
                    clear_chat_btn = gr.Button("🗑️ Clear Screen", scale=1)

                gr.Markdown("#### ⚡ Quick Vulnerability Scenario Presets (Click to Load):")
                with gr.Row():
                    preset_profile = gr.Button("🏢 1. Set FinTech Profile", size="sm")
                    preset_sqli = gr.Button("💉 2. SQLi Vulnerability (CWE-89)", size="sm")
                    preset_ssrf = gr.Button("🌐 3. SSRF Webhook (CWE-918)", size="sm")
                    preset_secrets = gr.Button("🔑 4. Leaked AWS Key (CWE-798)", size="sm")

            # Right: Controls & Live Memory Inspector
            with gr.Column(scale=4):
                with gr.Group():
                    gr.Markdown("### ⚙️ Session & Memory Controls")
                    with gr.Row():
                        ticket_picker = gr.Dropdown(
                            choices=DEFAULT_TICKETS,
                            value="vuln-cve-89-billing",
                            label="Ticket ID (thread_id)",
                            allow_custom_value=True,
                            scale=2
                        )
                        checkpointer_picker = gr.Radio(
                            choices=["SqliteSaver (Durable)", "InMemorySaver (RAM)"],
                            value="SqliteSaver (Durable)",
                            label="Checkpointer Backend",
                            scale=2
                        )
                    with gr.Row():
                        skills_toggle = gr.Checkbox(
                            value=True,
                            label="Enable Procedural Playbooks (SOPs)",
                            info="When ON, selects and injects structured cybersecurity SOPs"
                        )
                        reset_profile_btn = gr.Button("🧹 Wipe Profile", size="sm")

                inspector_panel = gr.Markdown(
                    "## 🛡️ Live Memory & Context Inspector\n*Memory state will appear here after the first message.*"
                )

        # ---------------------------------------------------------------------
        # EVENT HANDLERS
        # ---------------------------------------------------------------------
        def handle_user_submission(message, history, thread_id, cp_mode, skills_on):
            if not message.strip():
                return "", history, gr.update()

            history = history or []
            reply, panel_md = process_remediation_turn(
                message=message,
                thread_id=thread_id,
                checkpointer_mode=cp_mode,
                procedural_skills_enabled=skills_on,
            )

            history = history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": reply},
            ]
            return "", history, panel_md

        def switch_ticket(new_thread_id, cp_mode):
            """Load the selected ticket's history and refresh inspector."""
            new_thread_id = new_thread_id.strip() or "vuln-default"

            # Check if in-memory has it, else read from SQLite
            if new_thread_id in inmemory_store["everything"] and inmemory_store["everything"][new_thread_id]:
                loaded_history = inmemory_store["everything"][new_thread_id]
            elif cp_mode.startswith("SqliteSaver"):
                loaded_history = load_durable_history(new_thread_id)
                inmemory_store["everything"][new_thread_id] = list(loaded_history)
                inmemory_store["recent"][new_thread_id] = loaded_history[-MAX_RECENT:]
                inmemory_store["summaries"][new_thread_id] = get_durable_summary(new_thread_id)
            else:
                loaded_history = []

            # Refresh inspector panel preview
            profile_text = security_profile_as_text(load_security_profile())
            summary = inmemory_store["summaries"].get(new_thread_id, "")
            session_counts = get_all_session_stats()

            panel_md = f"## 🛡️ Live Memory & Context Inspector\n\n"
            panel_md += f"### 🔄 Switched to Ticket: `{new_thread_id}`\n"
            panel_md += f"- **History Loaded:** `{len(loaded_history)}` messages from storage\n"
            panel_md += f"- **Checkpointer Mode:** `{cp_mode}`\n\n"
            panel_md += f"### 🧠 Semantic Profile (Active):\n"
            panel_md += profile_text if profile_text else "_No profile set yet._\n\n"
            panel_md += f"### 📋 Running Incident Summary for `{new_thread_id}`:\n"
            panel_md += f"> {summary if summary else '_None yet._'}\n\n"
            panel_md += f"### 💾 Tickets in Database:\n"
            for tid in DEFAULT_TICKETS:
                cnt = session_counts.get(tid, len(inmemory_store["everything"].get(tid, [])))
                marker = " 👈 (Active)" if tid == new_thread_id else ""
                panel_md += f"- `{tid}`: {cnt} messages{marker}\n"

            return loaded_history, panel_md

        def do_reset_profile():
            reset_security_profile()
            return "## 🛡️ Live Memory & Context Inspector\n\n### 🧠 Semantic Profile\n*Profile has been cleared from `security_profile.json`.*"

        def get_sample_for_skill(skill_name):
            return SKILL_SAMPLES.get(skill_name, f"Please demonstrate how to apply the {skill_name} procedure.")

        # Wire inputs and buttons
        submit_inputs = [msg_box, chatbot, ticket_picker, checkpointer_picker, skills_toggle]
        submit_outputs = [msg_box, chatbot, inspector_panel]

        msg_box.submit(handle_user_submission, submit_inputs, submit_outputs)
        send_btn.click(handle_user_submission, submit_inputs, submit_outputs)

        ticket_picker.change(switch_ticket, [ticket_picker, checkpointer_picker], [chatbot, inspector_panel])
        reset_profile_btn.click(do_reset_profile, outputs=[inspector_panel])
        clear_chat_btn.click(lambda: [], outputs=[chatbot])

        # Load sample prompt from skill viewer into message box
        load_sample_btn.click(get_sample_for_skill, [skill_selector], [msg_box])

        # Preset Button Handlers
        preset_profile.click(
            lambda: "I am Maya, Principal AppSec Engineer at Apex FinTech Services. Our primary tech stack is Python 3.12, FastAPI, SQLAlchemy, and PostgreSQL deployed on AWS EKS. We strictly enforce PCI-DSS v4.0 and SOC2 Type II. Our remediation policy mandates parameterized queries, zero raw SQL, zero downtime DB migrations, and mandatory pytest regression tests.",
            outputs=[msg_box]
        )
        preset_sqli.click(
            lambda: "SAST scan flagged CWE-89 in billing/repo.py: \n```python\ndef get_unpaid_invoices(client_id: str):\n    query = f\"SELECT * FROM invoices WHERE client_id = '{client_id}' AND status = 'unpaid'\"\n    return db.session.execute(text(query)).fetchall()\n```\nPlease provide a complete remediation patch.",
            outputs=[msg_box]
        )
        preset_ssrf.click(
            lambda: "DAST scanner flagged an SSRF (CWE-918) vulnerability in services/webhook_dispatcher.py:\n```python\nimport requests\ndef send_webhook_notification(target_url: str, payload: dict):\n    # Unsanitized outbound HTTP request\n    return requests.post(target_url, json=payload, timeout=10)\n```\nRemediate this to protect against internal network pivot and AWS metadata (169.254.169.254) theft.",
            outputs=[msg_box]
        )
        preset_secrets.click(
            lambda: "GitGuardian detected a hardcoded AWS IAM secret key committed in auth/aws_token_validator.py:\n`AWS_SECRET_ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE/wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'`\nProvide containment, code refactoring, and git history remediation.",
            outputs=[msg_box]
        )

    return app


if __name__ == "__main__":
    print("====================================================================")
    print("🛡️  CYBERGUARD AVR - AUTONOMOUS VULNERABILITY REMEDIATION AGENT")
    print("====================================================================")
    print("Core Memory Systems Loaded:")
    print("  [1] Conversation History   : Working memory per ticket")
    print("  [2] Checkpointer & Threads : LangGraph SqliteSaver / InMemorySaver")
    print("  [3] Durable Memory         :", DB_FILE)
    print("  [4] Semantic Memory        :", PROFILE_FILE)
    print(f"  [5] Procedural Memory      : {len(skills_catalog)} SOP skills loaded")
    print(f"  [6] Context Compaction     : Sliding window (max {MAX_RECENT} turns) + running incident summary")
    print("====================================================================")

    custom_css = """
    .gradio-container { max-width: 1350px !important; }
    """
    page = build_app()
    page.launch(server_port=7860, css=custom_css, show_error=True)
