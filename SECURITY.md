# Security Policy

## Reporting a vulnerability

Please **don't open a public issue** for security problems. Use GitHub's private reporting instead: **Security → Report a vulnerability** on this repository. You'll get an acknowledgement within 5 business days.

These are in scope, and we especially want to hear about them:

- A way for PR content to **lower** its score, bypass a floor, or avoid escalation
- Prompt-injection paths that influence the result beyond the documented ±20 (upward-only in CI)
- Markdown or HTML injection into the bot comment (mentions, links, spoofed reports)
- Anything that makes the action execute PR code or leak a token
- Catastrophic regex backtracking (ReDoS) on crafted diffs

## Supported versions

Only the latest release receives fixes. Pin the action to a full commit SHA, and update on releases.

## Design notes

See "Security model" in the [README](README.md#-security-model) and the threat-related tests in `tests/test_pr_risk.py` (`TestSecurityHardening`, `TestSemantic`, `TestPromptInjection`, `TestSupplyChain`).
