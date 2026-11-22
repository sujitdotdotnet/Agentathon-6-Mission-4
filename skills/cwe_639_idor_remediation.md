name: IDOR & BOLA Remediation (CWE-639)
description: Use when remediating Insecure Direct Object Reference (IDOR) or Broken Object-Level Authorization (BOLA) where users access or modify records by manipulating IDs in API routes or queries.

Procedure:
1. Identify Endpoint & Authorization Boundary:
   - Identify the API endpoint, the resource identifier passed in parameters, and the authenticated identity from the JWT/session.
2. Server-Side Ownership Enforcement:
   - Never trust client-supplied entity IDs or assume that knowing an ID implies permission.
   - Bind all data queries to the authenticated tenant/user ID:
     Example: SELECT * FROM documents WHERE id = :doc_id AND org_id = :authenticated_org_id
   - If the object does not belong to the user, return HTTP 404 (Not Found) rather than 403 to prevent object ID enumeration attacks.
3. Migrate to Non-Enumerable Identifiers:
   - Replace sequential integer auto-increment IDs with cryptographically secure UUIDv4 or NanoID for public facing APIs.
4. Authorize via Reusable Security Guardrail:
   - Implement a reusable authorization gate (e.g., FastAPI Depends(verify_resource_ownership)).
5. Unit Test Verification Matrix:
   - Provide test cases:
     a) Legitimate owner accessing own resource (HTTP 200).
     b) Attacker attempting to access another user's resource (HTTP 404 / Access Denied).
     c) Unauthenticated caller attempting access (HTTP 401).
