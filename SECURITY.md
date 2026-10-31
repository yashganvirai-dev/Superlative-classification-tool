# Security Policy

## Supported version

Security fixes are applied to the `main` branch.

## Reporting a vulnerability

Do not disclose a vulnerability in a public GitHub issue, discussion, or pull request. If this repository has **Report a vulnerability** enabled, use GitHub's private security-advisory form. Otherwise, contact the repository owner through a private channel and include:

- affected file or component;
- steps to reproduce;
- expected and observed behavior;
- impact and any suggested mitigation.

Please allow time for a fix before public disclosure. No response-time guarantee is provided.

## Credential handling

- Never include API keys, access tokens, passwords, private URLs, or personal data in a report.
- If a credential may be exposed, revoke or rotate it immediately.
- Treat Git history, forks, caches, and CI logs as potentially retaining removed secrets.

## Testing scope

Only test against systems and accounts you own or are explicitly authorized to test. Do not use leaked credentials or disrupt third-party services.
