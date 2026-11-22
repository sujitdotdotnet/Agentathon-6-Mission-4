name: SQL Injection Remediation (CWE-89)
description: Use when remediating SQL injection (SQLi) vulnerabilities in database queries, ORM calls, dynamic SQL construction, or unsanitized user inputs reaching a SQL sink.

Procedure:
1. Vulnerability Isolation: Pinpoint the exact line, parameter, and function where untrusted user input is formatted or concatenated into a SQL statement.
2. Remediation Strategy:
   - For raw SQL: Replace dynamic string interpolation with parameterized queries and bind variables (:param, $1, or %s according to the driver).
   - For ORMs (SQLAlchemy, Django, Prisma): Replace raw text clauses (such as text() or raw()) with type-safe ORM query filters (filter(), filter_by(), select().where()).
   - For dynamic identifiers (table/column names): Parameterization cannot bind identifiers. Validate against a strict static Python enum or allowlist set.
3. Code Remediation Patch:
   - Provide a clean unified Git Diff or clear Before/After code block.
   - Enforce strong input validation and type checking (e.g., Pydantic schema validation).
4. Automated Regression & Negative Security Test:
   - Provide a pytest unit test demonstrating that SQL injection payloads (e.g., "' OR '1'='1", "'; DROP TABLE users; --", time-based blind sleep injections) are safely treated as literal data and return 0 unauthorized records or raise validation errors.
5. Defense-in-Depth & Compliance:
   - Ensure the database connection uses least-privilege credentials.
   - Map fix to PCI-DSS v4.0 Requirement 6.4 and OWASP Top 10 (A03:2021 Injection).
