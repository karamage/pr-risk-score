# Changelog

## 1.0.1 — 2026-11-03

### Fixed
- **Plugin failed to load after `/plugin install`** ("conflicting manifests: both plugin.json and marketplace entry specify components"). The marketplace entry no longer lists components; `plugin.json` is the single source of truth and `skills/` is auto-discovered. If you installed 1.0.0 through the plugin marketplace, run `/plugin marketplace update pr-risk-score`, reinstall the plugin, then `/reload-plugins`.

### Added
- Plugin icon and a README demo GIF built from real runs.

The GitHub Action, the skills CLI install, and the CLI were not affected.

## 1.0.0 — 2026-11-03

First release.

- Deterministic 0–100 risk score with 7 explainable factors, 8 sensitive-path categories, and 27 pattern rules
- Hard floors for leaked secrets, destructive migrations, CI edits by first-time contributors, privileged workflow triggers, and prompt injection
- Generated-code detection (paths and `DO NOT EDIT` headers, including files GitHub doesn't send a patch for)
- `.pr-risk.json` policy read from the base branch
- Claude Code skill with a bounded (±20) semantic review rubric
- Composite GitHub Action with sticky comment, labels, and gating outputs
- `--local` mode to score a branch before opening a PR
- `--render --semantic`: the script, not the model, applies semantic items (±15 per item, ±20 total, floors, escalation, optional no-decrease)
- Hardening: sanitized comment output, owner-checked sticky comment, URL-encoded API paths, regex/scan budgets against ReDoS, least-privilege workflows
