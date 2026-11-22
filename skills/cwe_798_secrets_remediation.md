name: Hardcoded Secrets Remediation (CWE-798)
description: Use when API keys, passwords, database credentials, AWS tokens, private keys, or certificates are committed to source code or git history.

Procedure:
1. Immediate Containment & Invalidation:
   - Identify the leaked credential type and immediately revoke or cycle the active key in the provider console (AWS IAM, Stripe, SendGrid, GitHub).
   - Generate a replacement secret before altering codebase files.
2. Codebase Refactoring:
   - Remove plaintext secret literals from all source files immediately.
   - Refactor code to load secrets from environment variables (e.g., pydantic-settings, os.environ) or programmatically via AWS Secrets Manager / HashiCorp Vault.
3. Git History Sanitization:
   - Explain that a standard git commit leaves the secret permanently exposed in the repository commit log.
   - Provide the git-filter-repo command to scrub the token from commit history:
     git filter-repo --replace-text <(echo "LEAKED_KEY==>REDACTED_SECRET")
4. CI/CD Shift-Left Guardrail:
   - Configure a pre-commit hook with Gitleaks or TruffleHog to block future accidental credential commits.
   - Add a CI pipeline step (e.g. GitHub Actions) scanning all pull requests for high-entropy tokens.
5. Verification & Safe Default Test:
   - Provide a unit test ensuring the application fails safely with a clear configuration error if the required environment secret is omitted, rather than falling back to an insecure default.
