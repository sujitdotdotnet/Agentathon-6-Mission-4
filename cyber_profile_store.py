"""
cyber_profile_store.py - Semantic Memory for Cybersecurity Vulnerability Remediation.

Semantic memory represents facts and knowledge that persist across conversations:
- The organization/client being protected
- The target tech stack (languages, frameworks, ORMs, cloud)
- Compliance frameworks (PCI-DSS, HIPAA, SOC2, OWASP)
- Enterprise remediation policies (no raw SQL, zero downtime migrations, mandatory unit tests)
- The security engineer interacting with the agent

Unlike conversation history (which is tied to a specific vulnerability ticket thread_id),
this profile follows the security engineer across ALL vulnerability tickets.
"""

import json
import os
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

PROFILE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "security_profile.json")

FIELDS = [
    "organization",
    "security_engineer",
    "primary_tech_stack",
    "target_environment",
    "compliance_framework",
    "remediation_policy",
]


class SecurityProfile(BaseModel):
    """Structured extraction model for enterprise cybersecurity attributes."""
    organization: str = Field(default="", description="The company, project, or department name, if stated.")
    security_engineer: str = Field(default="", description="The security engineer's name and/or role, if stated.")
    primary_tech_stack: str = Field(default="", description="Languages, frameworks, ORMs, or databases used (e.g. FastAPI, SQLAlchemy, PostgreSQL).")
    target_environment: str = Field(default="", description="Deployment environment (e.g. AWS EKS, GCP Cloud Run, On-Premise Docker).")
    compliance_framework: str = Field(default="", description="Security/compliance standards (e.g. PCI-DSS v4.0, SOC2, HIPAA, OWASP).")
    remediation_policy: str = Field(default="", description="Engineering/security remediation policies or constraints (e.g. zero-downtime, no raw SQL, mandatory unit tests).")


def load_security_profile():
    """Load the saved security profile from JSON, returning defaults if not found."""
    profile = {field: "" for field in FIELDS}
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for field in FIELDS:
                profile[field] = saved.get(field, "")
        except Exception:
            pass
    return profile


def save_security_profile(profile):
    """Save the profile dictionary to security_profile.json."""
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)


def reset_security_profile():
    """Clear all semantic profile memory."""
    profile = {field: "" for field in FIELDS}
    save_security_profile(profile)
    return profile


def find_new_security_facts(message):
    """
    Extract security and environment facts from the engineer's message using structured output.
    Returns only non-empty fields that were clearly stated.
    """
    model = init_chat_model("deepseek:deepseek-chat", temperature=0.0, max_tokens=200)
    extractor = model.with_structured_output(SecurityProfile)
    try:
        result = extractor.invoke([
            {
                "role": "system",
                "content": (
                    "You are a cybersecurity context extractor. Read the security engineer's message. "
                    "Extract ONLY facts they clearly state about their organization, role, tech stack, "
                    "target cloud/deployment environment, compliance standards (PCI-DSS, SOC2, HIPAA, etc.), "
                    "or remediation policies (e.g. no raw SQL, zero downtime, pytest requirements). "
                    "Leave every other field as empty string. Never invent or hallucinate facts."
                ),
            },
            {"role": "user", "content": message},
        ])
    except Exception:
        return {}

    found = {}
    if result is None:
        return found
    for field in FIELDS:
        value = getattr(result, field, "").strip()
        if value:
            found[field] = value
    return found


def update_security_profile(message):
    """
    Extract facts from the message and merge them into the saved security profile.
    Returns (profile, new_facts).
    """
    new_facts = find_new_security_facts(message)
    profile = load_security_profile()
    for field, value in new_facts.items():
        profile[field] = value
    if new_facts:
        save_security_profile(profile)
    return profile, new_facts


def security_profile_as_text(profile):
    """Convert the profile dictionary to formatted text for system prompt injection."""
    labels = {
        "organization": "Organization",
        "security_engineer": "Security Engineer",
        "primary_tech_stack": "Primary Tech Stack",
        "target_environment": "Target Environment",
        "compliance_framework": "Compliance Framework",
        "remediation_policy": "Remediation Policies",
    }
    lines = []
    for field in FIELDS:
        val = profile.get(field, "")
        if val:
            lines.append(f"- **{labels.get(field, field)}**: {val}")
    return "\n".join(lines)
