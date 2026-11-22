# 🛡️ CyberGuard AVR — Autonomous Vulnerability Remediation Agent
### *AI Agentathon Mission 4: Memory and Context in AI Agents*

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-1.3+-1C3C3C?logo=langchain&logoColor=white)](https://langchain.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2+-005571)](https://langchain-ai.github.io/langgraph/)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-Chat-4D6BFE)](https://deepseek.com)
[![Gradio](https://img.shields.io/badge/Gradio-6.25+-FF7C00?logo=gradio&logoColor=white)](https://gradio.app)

A language model is completely stateless—every call starts from scratch. **CyberGuard AVR** is a production-grade cybersecurity agent that wraps the LLM in **all 6 essential memory architectures**, demonstrating how intelligent agents conduct end-to-end vulnerability triage, root cause analysis, code patching (unified git diffs), negative security regression testing, and compliance enforcement.

---

## 📑 Table of Contents
- [What is CyberGuard AVR?](#-what-is-cyberguard-avr)
- [The 6 Core Memory Pillars](#-the-6-core-memory-pillars)
- [System Architecture](#-system-architecture)
- [Implemented Features & UI Guide](#-implemented-features--ui-guide)
- [Quick Start (Local)](#-quick-start-local)
- [Testing All 6 Memory Types (Walkthrough)](#-testing-all-6-memory-types-walkthrough)
- [Automated Verification Suite](#-automated-verification-suite)
- [Deploying to Production (Render.com)](#-deploying-to-production-rendercom)
- [Repository Structure](#-repository-structure)
- [Foundational Labs (Mission 4 Curriculum)](#-foundational-labs-mission-4-curriculum)

---

## 🎯 What is CyberGuard AVR?

In enterprise DevSecOps and AppSec, security engineers are overwhelmed by Static Application Security Testing (SAST), Dynamic Application Security Testing (DAST), Software Composition Analysis (SCA), and secret leak alerts.

**CyberGuard AVR** functions as an autonomous remediation assistant:
1. **Understands the Enterprise Environment**: Retains company tech stacks, cloud environments, and compliance standards (e.g., PCI-DSS v4.0, SOC2, HIPAA).
2. **Adheres to Standard Operating Procedures (SOPs)**: Executes strict 5-step security remediation runbooks for specific vulnerability classes (SQLi, SSRF, IDOR, Hardcoded Secrets, Vulnerable Dependencies).
3. **Isolates Incident Investigations**: Keeps independent tickets (`vuln-cve-89-billing`, `vuln-ssrf-918-webhooks`) completely separate.
4. **Survives Server Restarts**: Persists all triage history and checkpoints to durable storage.
5. **Optimizes Context Budgets**: Compresses long triage histories into concise summaries, cutting LLM token costs by **40% to 70%**.

---

## 🧠 The 6 Core Memory Pillars

| # | Memory Pillar | Plain Meaning | Implementation in CyberGuard AVR | Storage Target |
|---|---|---|---|---|
| **1** | **Conversation History** | Short-term working memory | Retains variables, vulnerable code lines, and patch context across turns in a ticket | In-memory message list |
| **2** | **Checkpointer & Threads** | Multi-conversation state isolation | LangGraph `SqliteSaver` & `InMemorySaver` keyed by `thread_id` (e.g. `vuln-cve-89-billing`) | LangGraph Checkpoint Store |
| **3** | **Durable Memory** | Cross-restart survival | Automatically commits turns and checkpoints to disk; reloads state on reboot | `remediation_memory.sqlite` |
| **4** | **Semantic Memory** | Cross-ticket environment knowledge | Extracts & retains organization, tech stack, compliance framework, and remediation policies | `security_profile.json` |
| **5** | **Procedural Memory** | Standard Operating Procedures (SOPs) | 9 markdown runbooks; model selects via **Progressive Disclosure** (only ~250 chars of menu seen) | `skills/*.md` |
| **6** | **Context Compaction** | Context efficiency & budget control | Sliding window (last 4 turns verbatim) + auto-compaction of older turns into high-density summaries | Dynamic Context Packet |

---

## 🏛️ System Architecture

```text
                                  USER TRIAGE REQUEST
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │    CyberGuard AVR Orchestration Core   │
                      └───────────────────┬───────────────────┘
                                          │
          ┌───────────────────────────────┼───────────────────────────────┐
          │                               │                               │
          ▼                               ▼                               ▼
┌──────────────────┐            ┌──────────────────┐            ┌──────────────────┐
│ 4. Semantic Mem  │            │ 5. Procedural    │            │ 6. Compaction    │
│ Pydantic Extract │            │ Progressive Menu │            │ Sliding Window & │
│ (Org, Stack,     │            │ (SOP Matcher)    │            │ Triage Summary   │
│  Compliance)     │            │                  │            │                  │
└─────────┬────────┘            └─────────┬────────┘            └─────────┬────────┘
          │                               │                               │
          └───────────────────────────────┼───────────────────────────────┘
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │    Assembled Context Packet           │
                      │  - Base Prompt + Security Role        │
                      │  - Semantic Security Profile          │
                      │  - Active Remediation SOP (1 Playbook)│
                      │  - Running Incident Summary           │
                      │  - Recent Verbatim Turns (Sliding W.) │
                      │  - Current User Message               │
                      └───────────────────┬───────────────────┘
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │        DeepSeek-Chat LLM Call         │
                      └───────────────────┬───────────────────┘
                                          │
                      ┌───────────────────┴───────────────────┐
                      │                                       │
                      ▼                                       ▼
          ┌───────────────────────┐               ┌───────────────────────┐
          │ 2 & 3. Durable Memory │               │ Live Inspector Panel  │
          │ LangGraph Checkpointer│               │ - Token Savings %     │
          │ (remediation_memory.  │               │ - Active SOP Matched  │
          │  sqlite)              │               │ - Active Profile      │
          └───────────────────────┘               │ - SQLite Ticket Stats │
                                                  └───────────────────────┘
```

---

## ✨ Implemented Features & UI Guide

### 1. Interactive Procedural Skills & SOP Browser (Top Accordion)
- **Playbook Dropdown**: Browse all 9 loaded remediation skills:
  - `SQL Injection Remediation (CWE-89)`
  - `SSRF Remediation (CWE-918)`
  - `Hardcoded Secrets Remediation (CWE-798)`
  - `IDOR & BOLA Remediation (CWE-639)`
  - `Dependency Vulnerability Patching (SCA)`
  - `Incident Triage`
  - `Code Review and Security Check`
  - `SQL Query Helper`
  - `Refund and Chargeback Policy`
- **Progressive Disclosure Inspector**: See the compact 1-line description the model sees (~200 chars) vs. the complete step-by-step SOP procedure (~1,200 chars).
- **"📋 Load Sample Prompt for this Skill into Chat"**: Loads a realistic, production-ready vulnerability report matching the selected playbook with one click.

### 2. Live Memory & Context Inspector (Right Column)
- **Context Packet & Token Efficiency**:
  - Live token count of the optimized Context Packet
  - Unmanaged tokens (cost if full raw history was resent)
  - **Live Efficiency Gain** (e.g. `47% token reduction` / `2,139 tokens saved`)
  - Compaction alert badges whenever turns fold into summary
- **Procedural Memory**: Active playbook name, source file, loaded character count, and the catalog status with `🎯 [ACTIVE]` markers.
- **Semantic Profile**: Live status of company, stack, and compliance frameworks stored in `security_profile.json`.
- **Checkpointer & Persistence**: Selected backend (`SqliteSaver` vs `InMemorySaver`), current `thread_id`, and ticket-by-ticket message counters in SQLite.
- **Running Incident Summary**: High-density distilled security triage notes automatically updated as the chat progresses.

### 3. Session & Checkpointer Controls
- **Ticket ID (`thread_id`)**: Switch between predefined tickets (`vuln-cve-89-billing`, `vuln-ssrf-918-webhooks`, `vuln-secrets-798-auth`, `vuln-ticket-999`) or type a custom ticket ID.
- **Checkpointer Backend**: Toggle between `SqliteSaver (Durable)` (persisted to disk) and `InMemorySaver (RAM)`.
- **Procedural Playbooks Switch**: Toggle SOPs ON or OFF to compare enterprise SOP execution vs. unstructured chatbot responses.
- **Wipe Profile Button**: Reset semantic profile to test extraction from scratch.

---

## 🚀 Quick Start (Local)

### 1. Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager (recommended) or standard `pip`

### 2. Installation & API Key Setup
```powershell
# Clone the repository and navigate into mission4
cd mission4

# Install dependencies using uv
uv sync

# Create .env and configure your DeepSeek API key
Copy-Item .env.example .env
```

Edit `.env`:
```text
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### 3. Run Setup Check
```powershell
uv run 00_setup_check.py
```
*Ensure it prints `ALL GOOD - you are ready.`*

### 4. Launch the Agent
```powershell
uv run cyber_remediation_agent.py
```

Open your browser at: **[http://127.0.0.1:7860](http://127.0.0.1:7860)**

---

## 🧪 Testing All 6 Memory Types (Walkthrough)

Follow this 5-minute interactive test in the UI:

### Step 1: Semantic Memory (Target Security Profile)
Click the quick preset button **"🏢 1. Set FinTech Profile"** (or send):
> *"I am Maya, Principal AppSec Engineer at Apex FinTech Services. Our primary tech stack is Python 3.12, FastAPI, SQLAlchemy, and PostgreSQL on AWS EKS. We strictly enforce PCI-DSS v4.0 and our policy requires parameterized queries, zero raw SQL, and mandatory pytest regression tests."*

👉 **Look at the Inspector (right side)**: Under **4. Semantic Memory**, the agent extracted and saved your organization, stack, and compliance standards into `security_profile.json`.

---

### Step 2: Procedural Memory (CWE-89 Remediation SOP)
Click **"💉 2. SQLi Vulnerability (CWE-89)"**:
> *SAST scan flagged CWE-89 in billing/repo.py:*
> ```python
> def get_unpaid_invoices(client_id: str):
>     query = f"SELECT * FROM invoices WHERE client_id = '{client_id}' AND status = 'unpaid'"
>     return db.session.execute(text(query)).fetchall()
> ```
> *Please provide a complete remediation patch.*

👉 **Look at the Inspector**: Under **5. Procedural Memory**, it dynamically matched `SQL Injection Remediation (CWE-89)`. The agent follows the 5-step SOP, generating an ORM parameterized query aligned with your stack (FastAPI/SQLAlchemy) and compliance baseline (PCI-DSS).

---

### Step 3: Working Conversation History
Send:
> *"Can you write the negative pytest unit test for the patch you just provided?"*

👉 **Observe**: The agent recalls the function name, parameters, and query from the previous turn and writes a pytest test verifying SQL injection payloads fail safely.

---

### Step 4: Context Compaction & Token Reduction
Ask two more follow-up questions:
1. *"What database least-privilege permissions should the billing user have?"*
2. *"How do we verify zero-downtime deployment for this database change?"*

👉 **Look at the Inspector**:
- The older turns are automatically folded into the **Running Incident Triage Summary**.
- **Token Efficiency** displays a live savings percentage (typically **40%–70% token reduction**).
- A compaction alert badge indicates older turns were compressed.

---

### Step 5: Checkpointer Thread Isolation vs. Semantic Memory Cross-Over
1. Change the **Ticket ID** dropdown to `vuln-ticket-999` (a brand-new ticket).
2. Ask: *"What tech stack and compliance standard do we follow for our services?"*

👉 **Observe**:
- The chat window for `vuln-ticket-999` has zero billing messages (thread isolation).
- Yet the agent knows you use Python 3.12, FastAPI, PostgreSQL, and PCI-DSS v4.0 (**Semantic Memory** persists globally!).

---

### Step 6: Durable Memory (Survives Server Restarts)
1. Ensure the backend is set to `SqliteSaver (Durable)`.
2. Stop the running terminal process with `Ctrl+C`.
3. Re-launch `uv run cyber_remediation_agent.py`.
4. Switch the dropdown to `vuln-cve-89-billing`.

👉 **Observe**: All messages, checkpoints, and triage history are restored directly from `remediation_memory.sqlite`.

---

## 🔬 Automated Verification Suite

Run the headless verification suite to test all memory subsystems programmatically:

```powershell
uv run test_cyber_agent.py
```

### Verification Results:
```text
====================================================================
TESTING CYBERGUARD AVR - ALL 6 MEMORY CONCEPTS
====================================================================

[TEST 1] Setting Semantic Security Profile...
  - Organization: Apex FinTech Services
  - Tech Stack  : Python 3.12, FastAPI, SQLAlchemy, PostgreSQL
  - Compliance  : PCI-DSS v4.0
  [OK] Semantic memory successfully extracted and saved to security_profile.json!

[TEST 2] Procedural Skill Selection (SQLi CWE-89)...
  - Active Playbook matched: SQL Injection Remediation (CWE-89)
  [OK] Procedural SOP dynamically chosen via progressive disclosure!

[TEST 3] Conversation Working History...
  [OK] Model used conversation history to write unit tests for the specific patch!

[TEST 4] Context Compaction on Long Conversations...
  - Token reduction: 47% token reduction (2,139 tokens saved)
  [OK] Context compaction successfully folded older turns and saved tokens!

[TEST 5 & 6] Checkpointer Thread Isolation + Semantic Memory Cross-over...
  - Reply on brand-new ticket-999: Model recalled FastAPI, PostgreSQL, PCI-DSS
  [OK] Thread-999 was completely isolated, yet semantic memory provided the organization profile!

[TEST 7] Verifying Durable Storage in SQLite...
  - Retrieved 10 messages from remediation_memory.sqlite for test-ticket-101
  [OK] SQLite durable checkpointer persisted all messages to disk!

====================================================================
ALL 6 MEMORY CONCEPTS VERIFIED AND WORKING PERFECTLY! 🛡️
====================================================================
```

---

## 🌐 Deploying to Production (Render.com)

To deploy CyberGuard AVR as a live web service on Render:

1. Push your repository to GitHub / GitLab.
2. In the **Render Dashboard**, click **New +** &rarr; **Web Service**.
3. Connect your repository and configure:

| Setting | Value |
|---|---|
| **Environment** | `Python` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python cyber_remediation_agent.py` |

4. In **Environment Variables**, add:
   - `DEEPSEEK_API_KEY`: `your_actual_deepseek_api_key_here`
   - `PYTHON_VERSION`: `3.12.0`

> **Note**: `cyber_remediation_agent.py` automatically binds to `0.0.0.0` and listens to `PORT` supplied by Render.

---

## 📂 Repository Structure

```text
mission4/
├── cyber_remediation_agent.py     # 🚀 Flagship application (LangChain + DeepSeek + Gradio)
├── cyber_profile_store.py         # 🧠 Semantic memory extractor & profile persistence
├── test_cyber_agent.py            # 🧪 Automated test suite for all 6 memory layers
├── remediation_memory.sqlite      # 💾 SQLite durable checkpointer database
├── security_profile.json          # 📋 Persistent semantic profile store
├── requirements.txt               # 📦 Cloud deployment dependency manifest
├── pyproject.toml                 # ⚙️ UV / Python project configuration
├── uv.lock                        # 🔒 Locked dependency tree
│
├── skills/                        # 📜 Procedural Memory (Playbooks & SOPs)
│   ├── cwe_89_sqli_remediation.md # CWE-89: SQL Injection SOP
│   ├── cwe_918_ssrf_remediation.md# CWE-918: SSRF & DNS Rebinding SOP
│   ├── cwe_798_secrets_remediation.md # CWE-798: Secret Revocation & History Scrubbing
│   ├── cwe_639_idor_remediation.md# CWE-639: IDOR & BOLA Authorization Gate SOP
│   ├── sca_dependency_patching.md # Dependency & Supply Chain Patching SOP
│   ├── incident_triage.md         # Production Outage Incident Triage SOP
│   ├── code_review.md             # Secure Code Review Checklist SOP
│   ├── sql_helper.md              # Safe SQL Query Authoring SOP
│   └── refund_policy.md           # Transaction Refund & Chargeback SOP
│
├── skills_loader.py               # 🔍 Skill parser & progressive disclosure chooser
├── chat_ui.py                     # 🖥️ Foundational workshop Gradio chat builder
│
└── [Foundational Labs]            # 📚 Step-by-step educational curriculum
    ├── 00_setup_check.py          # Environment, key, and DeepSeek connection check
    ├── 01_agent_forgets.py        # Baseline: proves the model is stateless
    ├── 02_message_list.py         # Working memory: managing message lists manually
    ├── 03_checkpointer.py         # LangGraph InMemorySaver & thread_id
    ├── 04_durable_sessions.py     # LangGraph SqliteSaver for disk persistence
    ├── 05_profile_memory.py       # Semantic profile store (Pydantic extraction)
    ├── 06_skills.py               # Procedural memory with progressive disclosure
    └── 07_context_packet.py       # Capstone: building context packets with summarization
```

---

## 📚 Foundational Labs (Mission 4 Curriculum)

If you are exploring the foundational concepts step-by-step before using the flagship agent, run the labs in order:

```powershell
uv run 01_agent_forgets.py      # Lab 1: Proves statelessness
uv run 02_message_list.py       # Lab 2: Manual message list memory
uv run 03_checkpointer.py       # Lab 3: LangGraph checkpointer & thread_id
uv run 04_durable_sessions.py   # Lab 4: SQLite durable checkpointer
uv run 05_profile_memory.py     # Lab 5: Profile memory (profile.json)
uv run 06_skills.py             # Lab 6: Procedural memory (skills/)
uv run 07_context_packet.py     # Lab 7: Custom context packet & compaction
```

---

## 🛡️ License & Acknowledgements
Built as part of **Agentathon Mission 4 — Memory and Context in AI Agents**. Powered by Google DeepMind Antigravity, LangChain, LangGraph, and DeepSeek.
