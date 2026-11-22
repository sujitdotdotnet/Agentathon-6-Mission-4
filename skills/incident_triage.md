name: Incident Triage
description: Use when a system, service, server, website or API is broken, down, crashing, timing out, throwing errors or running slow, and the technical team needs a severity and a next step.

Procedure:
1. Confirm which service is affected and what the user actually saw.
2. Give it a severity:
   P1 - service down or many customers affected
   P2 - a major feature broken, a workaround exists
   P3 - a minor problem or a single user
   P4 - cosmetic
3. State the customer impact in one line.
4. Give the immediate next step: restart, roll back, page the on-call engineer, or raise a ticket.
5. Close with the severity and the team that owns it.

Always end your reply with a line in this form:
SEVERITY: <P1-P4> | OWNER: <team>
