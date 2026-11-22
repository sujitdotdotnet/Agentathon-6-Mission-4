name: Dependency Vulnerability Patching (SCA)
description: Use when remediating vulnerable open-source dependencies, third-party libraries, or supply chain CVEs found in package manifests (pyproject.toml, requirements.txt) or lockfiles.

Procedure:
1. Vulnerability & Threat Assessment:
   - Identify the affected package name, current installed version, CVE ID, CVSS score, and whether an active exploit (EPSS > 0.1) exists.
2. Determine Minimal Safe Upgrade Version:
   - Identify the minimum patched version specified in the vendor advisory that satisfies semantic versioning (prefer patch/minor bumps over major to minimize regression risk).
3. Transitive Dependency Triage:
   - If the vulnerability resides in an indirect dependency, check if a top-level parent update pulls in the patched version, or specify lockfile / package manager constraint overrides.
4. Breaking Change & Compatibility Analysis:
   - Check upstream changelogs for breaking API changes, renamed symbols, or dropped Python version support.
5. Lockfile Update & Verification:
   - Provide the exact package manager command (e.g. `uv lock --upgrade-package <pkg>` or `pip install --upgrade <pkg>`).
   - Run the project test suite and verify lockfile hashes are pinned.
