name: SSRF Remediation (CWE-918)
description: Use when remediating Server-Side Request Forgery (SSRF) vulnerabilities where the application fetches remote URLs, webhooks, avatars, or external APIs based on user-supplied URLs.

Procedure:
1. Vulnerability Isolation: Identify the endpoint and HTTP client invocation (requests.get, httpx.AsyncClient, urllib) consuming the user-provided URL.
2. Scheme & Protocol Allowlisting:
   - Restrict allowed schemes strictly to 'https://' (reject http://, file://, gopher://, dict://, ftp://).
3. Network Egress Filtering & DNS Rebinding Protection:
   - Resolve the target hostname to IP addresses synchronously prior to connection.
   - Filter and reject private, loopback, link-local, and reserved CIDR ranges:
     - 127.0.0.0/8 (Loopback)
     - 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 (RFC 1918 Private networks)
     - 169.254.169.254 (Cloud IMDS / AWS Instance Metadata)
     - 0.0.0.0/8, 224.0.0.0/4 (Multicast), ::1, fe80::/10 (IPv6 equivalents)
   - Pin the validated IP address for the actual HTTP connection to prevent Time-of-Check to Time-of-Use (TOCTOU) DNS rebinding.
4. HTTP Client Hardening:
   - Disable automatic HTTP redirects (allow_redirects=False) or re-evaluate the target address of every redirect hop against the IP filter.
   - Set aggressive connect and read timeouts (maximum 3-5 seconds).
5. Code Remediation Patch & Verification Test:
   - Provide the hardened SafeURLFetcher wrapper class or function.
   - Provide a pytest unit test verifying that calls to http://169.254.169.254 and http://127.0.0.1:8000 raise an SSRFSecurityException.
