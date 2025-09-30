# Security Policy

## Reporting Security Issues

We take the security of our project seriously. If you believe you have found a security vulnerability, please report it to us privately. **Please do not report security vulnerabilities through public GitHub issues, discussions, or pull requests.**

### How to Report

- [Open a private GitHub Security Advisory draft](https://github.com/Significant-Gravitas/AutoGPT/security/advisories/new)
- If you cannot access GitHub Security Advisories, please reach out to the maintainers through the contact options listed in the repository README to arrange a private disclosure channel.

> **Important Note**: Any code within the `classic/` folder is considered legacy, unsupported, and out of scope for security reports. We will not address security vulnerabilities in this deprecated code.

### What to Include

When reporting an issue, please share the following details so we can triage and address it quickly:

1. A clear description of the vulnerability, including the affected area of the codebase and the potential impact.
2. Step-by-step reproduction instructions, including any scripts, payloads, or configuration changes that are required.
3. The commit hash, tag, or release version where the issue was observed.
4. Any suggested mitigations, workarounds, or patches (if available).

### Our Process

1. **Acknowledgement** – We will confirm receipt of your report within 14 business days.
2. **Investigation** – The team will reproduce and evaluate the impact and severity of the issue.
3. **Resolution Planning** – We will determine remediation steps, develop a fix, and prepare release notes.
4. **Coordinated Disclosure** – We will keep you updated as we publish patches and advisories, and coordinate a disclosure timeline.

### Coordinated Disclosure Policy

- Please allow us a 90-day security fix window before public disclosure.
- After the patch is released, please allow an additional 30 days for users to update (for a total maximum of 120 days between report and public disclosure).
- We may request more time if a complex remediation effort is required and we will keep you informed throughout the process.
- Share any potential mitigations or workarounds if known.

## Supported Versions

Only the following versions are eligible for security updates:

| Version | Supported |
|---------|-----------|
| Latest release on master branch | ✅ |
| Development commits (pre-master) | ✅ |
| Classic folder (deprecated) | ❌ |
| All other versions | ❌ |

We aim to backport critical fixes when feasible, but in some cases the resolution may require upgrading to the latest supported release.

## Security Best Practices

When using this project:

1. Always use the latest stable version.
2. Review security advisories before updating.
3. Follow our security documentation and guidelines.
4. Keep your dependencies up to date.
5. Do not use code from the `classic/` folder as it is deprecated and unsupported.
6. Rotate API keys, credentials, and other secrets regularly.
7. Deploy AutoGPT components in isolated environments with least-privilege access controls.

## Severity Classification

We follow the [Common Vulnerability Scoring System (CVSS)](https://www.first.org/cvss/) to assess the severity of reported issues. This classification helps us prioritize fixes and communicate impact levels clearly.

| Severity | Description | Target response |
|----------|-------------|-----------------|
| Critical | Active exploitation likely or leading to remote code execution or credential compromise. | Immediate investigation and out-of-band patch if necessary. |
| High | Significant impact requiring authenticated access or complex preconditions. | Prioritized for the next scheduled release or an expedited patch. |
| Medium | Limited impact, partial mitigation available, or affects non-default configurations. | Addressed in an upcoming release cycle. |
| Low | Minor impact or requires unusual environmental assumptions. | Tracked for future updates as capacity allows. |

## Past Security Advisories
For a list of past security advisories, please visit our [Security Advisory Page](https://github.com/Significant-Gravitas/AutoGPT/security/advisories) and [Huntr Disclosures Page](https://huntr.com/repos/significant-gravitas/autogpt).

---
Last updated: November 2024
