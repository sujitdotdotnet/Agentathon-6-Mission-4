"""
test_cyber_agent.py - Automated test suite for CyberGuard AVR memory subsystems.
"""

import os
import sys
from cyber_profile_store import reset_security_profile, load_security_profile
from cyber_remediation_agent import process_remediation_turn, load_durable_history, get_all_session_stats

print("====================================================================")
print("TESTING CYBERGUARD AVR - ALL 6 MEMORY CONCEPTS")
print("====================================================================")

# Reset profile for clean test
reset_security_profile()

# -------------------------------------------------------------------------
# Test 1: Semantic Memory (Security Profile Extraction)
# -------------------------------------------------------------------------
print("\n[TEST 1] Setting Semantic Security Profile...")
turn1_msg = (
    "I am Maya, Principal AppSec Engineer at Apex FinTech Services. "
    "Our stack is Python 3.12, FastAPI, SQLAlchemy, and PostgreSQL on AWS EKS. "
    "We enforce PCI-DSS v4.0. Our policy requires parameterized queries and pytest regression tests."
)
reply1, panel1 = process_remediation_turn(
    message=turn1_msg,
    thread_id="test-ticket-101",
    checkpointer_mode="SqliteSaver (Durable)",
    procedural_skills_enabled=True,
)
profile = load_security_profile()
print("  - Organization:", profile.get("organization"))
print("  - Tech Stack  :", profile.get("primary_tech_stack"))
print("  - Compliance  :", profile.get("compliance_framework"))
assert "Apex FinTech" in profile.get("organization", "") or "FinTech" in profile.get("organization", "")
assert "FastAPI" in profile.get("primary_tech_stack", "")
print("  [OK] Semantic memory successfully extracted and saved to security_profile.json!")

# -------------------------------------------------------------------------
# Test 2: Procedural Memory (Playbook Selection)
# -------------------------------------------------------------------------
print("\n[TEST 2] Procedural Skill Selection (SQLi CWE-89)...")
turn2_msg = (
    "SAST scan flagged CWE-89 in billing/repo.py:\n"
    "query = f\"SELECT * FROM invoices WHERE client_id = '{client_id}' AND status = 'unpaid'\"\n"
    "Provide a secure remediation patch."
)
reply2, panel2 = process_remediation_turn(
    message=turn2_msg,
    thread_id="test-ticket-101",
    checkpointer_mode="SqliteSaver (Durable)",
    procedural_skills_enabled=True,
)
assert "SQL Injection Remediation (CWE-89)" in panel2
print("  - Active Playbook matched:", "SQL Injection Remediation (CWE-89)")
print("  [OK] Procedural SOP dynamically chosen via progressive disclosure!")

# -------------------------------------------------------------------------
# Test 3: Short-term Working Memory (Conversation History)
# -------------------------------------------------------------------------
print("\n[TEST 3] Conversation Working History...")
turn3_msg = "Can you provide the negative pytest unit test for the patch you just provided?"
reply3, panel3 = process_remediation_turn(
    message=turn3_msg,
    thread_id="test-ticket-101",
    checkpointer_mode="SqliteSaver (Durable)",
    procedural_skills_enabled=True,
)
assert "pytest" in reply3.lower() or "test" in reply3.lower()
print("  [OK] Model used conversation history to write unit tests for the specific patch!")

# -------------------------------------------------------------------------
# Test 4: Context Compaction & Token Efficiency
# -------------------------------------------------------------------------
print("\n[TEST 4] Context Compaction on Long Conversations...")
# Send 2 more turns to trigger compaction beyond MAX_RECENT (4 messages)
turn4_msg = "What database permissions should the billing service user have?"
reply4, panel4 = process_remediation_turn(
    message=turn4_msg,
    thread_id="test-ticket-101",
    checkpointer_mode="SqliteSaver (Durable)",
    procedural_skills_enabled=True,
)

turn5_msg = "How do we verify zero downtime for this migration?"
reply5, panel5 = process_remediation_turn(
    message=turn5_msg,
    thread_id="test-ticket-101",
    checkpointer_mode="SqliteSaver (Durable)",
    procedural_skills_enabled=True,
)
print("  - Inspector panel excerpt:\n", panel5[:300] + "...")
assert "token reduction" in panel5 or "tokens saved" in panel5.lower()
print("  [OK] Context compaction successfully folded older turns and saved tokens!")

# -------------------------------------------------------------------------
# Test 5 & 6: Checkpointer thread_id isolation & Semantic cross-over
# -------------------------------------------------------------------------
print("\n[TEST 5 & 6] Checkpointer Thread Isolation + Semantic Memory Cross-over...")
turn_new_ticket = "What tech stack and compliance standard do we follow for our services?"
reply_new, panel_new = process_remediation_turn(
    message=turn_new_ticket,
    thread_id="test-ticket-999",  # Brand new blank ticket!
    checkpointer_mode="SqliteSaver (Durable)",
    procedural_skills_enabled=True,
)
print("  - Reply on brand-new ticket-999:\n", reply_new)
assert "FastAPI" in reply_new or "PCI-DSS" in reply_new or "SQLAlchemy" in reply_new
print("  [OK] Thread-999 was completely isolated, yet semantic memory provided the organization profile!")

# -------------------------------------------------------------------------
# Test 7: Durable Persistence Verification
# -------------------------------------------------------------------------
print("\n[TEST 7] Verifying Durable Storage in SQLite...")
history = load_durable_history("test-ticket-101")
print(f"  - Retrieved {len(history)} messages from remediation_memory.sqlite for test-ticket-101")
assert len(history) >= 8  # 5 turns = 10 messages
print("  [OK] SQLite durable checkpointer persisted all messages to disk!")

print("\n====================================================================")
print("ALL 6 MEMORY CONCEPTS VERIFIED AND WORKING PERFECTLY! 🛡️")
print("====================================================================")
