# Scoring Model

How `scripts/pr_risk.py` turns a diff into a number. Read this when someone asks "why did this PR score X?" or wants to tune the model.

## Contents
1. Design principles
2. Factors (what adds points)
3. Sensitive categories and pattern rules
4. Caps and floors
5. Levels and decision
6. Why these signals
7. Known limitations

---

## 1. Design principles

- **Explainable over clever.** Each point comes from a named factor, with the files or lines that triggered it. A reviewer can disagree with a reason; nobody can disagree with an embedding.
- **Deterministic baseline.** The same diff and config always give the same score, so CI gates are stable and can be audited later.
- **Asymmetric errors.** A false "needs human" wastes minutes. A false "safe" can ship an incident. When signals conflict, the model leans toward review.
- **Can't be argued down by the PR.** Config comes from the base branch, floors can't be lowered by semantic adjustment, and text that addresses AI reviewers is itself a risk signal.

## 2. Factors

Total = sum of factor points (each capped), then capped at 100, then caps and floors are applied.

| Factor | Max | How points are earned |
|---|---:|---|
| Change size | 20 | Effective lines changed (additions + deletions, excluding lockfiles, generated, vendored, and ignored files; documentation lines count 1/5): ≤10 → 0, ≤50 → 3, ≤150 → 6, ≤300 → 10, ≤600 → 14, ≤1000 → 17, more → 20 |
| Change spread | 10 | Effective files: ≤3 → 0, ≤10 → 2, ≤20 → 4, ≤40 → 6, more → 8; +2 if 4 or more top-level directories |
| Sensitive areas | 40 | Sum of each sensitive category hit (once per category, see §3); lockfile-only dependency updates +3 |
| Risky code patterns | 30 | Sum of each distinct rule that fires on **added** lines (once per rule, see §3) |
| Test coverage gap | 20 | ≥20 code lines and no test changes: 6 / 10 / 15 by size (<100 / <300 / more). Tests <10% of ≥100 code lines: 5. Untested change to security/payments/migrations: +5. Tests deleted or net-shrunk: +5 |
| Change shape | 10 | Deleted source files (+2 each, max 6), binary files +2, any single file >500 lines +3, ≥5 renames +2, heavy rewrite +1 |
| Author & context | 10 | First-time/external contributor +5, empty description on a >50-line change +3, rushed title (hotfix/urgent/revert) +3, draft/WIP +2 |

The factor maxima add up to 140 on purpose. Hitting several factors at once should saturate at 100 rather than needing every factor maxed out.

## 3. Sensitive categories and pattern rules

Paths are matched case-insensitively. Test files are skipped for most categories (a test *about* login isn't a login change), except `infrastructure` and `governance`. Documentation and translation files are never sensitive, with one exception: files that steer reviewers or AI agents (`CODEOWNERS`, `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, `.github/skills/`, `.cursor/rules/`, ...) count as `governance`. Editing them can change how every future PR gets reviewed.

| Category | Points | Covers |
|---|---:|---|
| `security` | 20 | authentication / authorization / crypto |
| `payments` | 20 | payments / billing / money |
| `data_migration` | 18 | database migrations / schema |
| `infrastructure` | 10 | infrastructure / CI / deployment |
| `public_api` | 8 | public API / contracts |
| `governance` | 8 | repo governance / review rules / AI-agent instructions |
| `config` | 6 | runtime configuration / feature flags |
| `dependencies` | 6 | dependency manifests |

| Rule id | Severity | Points | Scope | Detects |
|---|---|---:|---|---|
| `secret-aws-key` | critical | 30 | all | AWS access key committed |
| `secret-github-token` | critical | 30 | all | GitHub token committed |
| `secret-google-api-key` | critical | 30 | all | Google API key committed |
| `secret-openai-anthropic` | critical | 30 | all | LLM API key committed |
| `secret-private-key` | critical | 30 | all | Private key committed |
| `secret-slack-token` | critical | 30 | all | Slack token committed |
| `secret-stripe-live` | critical | 30 | all | Stripe live secret key committed |
| `auth-check-disabled` | high | 10 | code | Authentication / CSRF / CORS protection relaxed |
| `destructive-sql` | high | 12 | nondoc | Destructive data operation (DROP/TRUNCATE/DELETE without WHERE) |
| `dynamic-eval` | high | 10 | code | Dynamic code execution (eval/exec) |
| `hardcoded-credential` | high | 10 | code | Hard-coded credential-looking literal |
| `insecure-permissions` | high | 8 | nondoc | Dangerous filesystem/privilege operation |
| `prompt-injection` | high | 10 | all | Text that tries to instruct an AI reviewer (possible prompt injection) |
| `shell-injection` | high | 10 | code | Shell command execution (injection risk) |
| `tls-verification-disabled` | high | 10 | code | TLS certificate verification disabled |
| `unsafe-deserialization` | high | 10 | code | Unsafe deserialization |
| `workflow-pull-request-target` | high | 10 | workflow | Privileged workflow trigger (pull_request_target / workflow_run) |
| `workflow-write-permissions` | high | 8 | workflow | Workflow gains write permissions / interpolates untrusted input |
| `xss-sink` | high | 8 | code | Unescaped HTML sink (XSS risk) |
| `check-suppression` | medium | 3 | code | Type-check / lint / security check suppressed |
| `concurrency` | medium | 3 | code | Concurrency primitives (race-condition risk) |
| `debug-leftover` | medium | 4 | code | Debugger statement left in code |
| `force-push-or-skip-hooks` | medium | 4 | nondoc | Force push / skipped verification |
| `raw-sql-interpolation` | medium | 8 | code | SQL built by string interpolation (injection risk) |
| `swallowed-error` | medium | 5 | code | Error silently swallowed |
| `unsafe-code` | medium | 5 | code | Memory-unsafe construct |
| `todo-marker` | low | 2 | code | TODO/FIXME/HACK marker added |

Scopes: `all` = every file, including tests and docs (secrets leak from fixtures too). `nondoc` = everything except docs and tests (code, Dockerfiles, scripts, SQL), so `sudo` in a README or `DROP TABLE` in a test fixture doesn't count. `code` = source files only, excluding tests, docs, and generated code. `workflow` = `.github/workflows/*` and `.github/actions/*`. The PR description is also checked for `prompt-injection`.

Secret snippets are redacted in the output so the report doesn't re-leak them.

Regenerate these tables with `python3 scripts/pr_risk.py --list-rules`. A unit test fails if this file drifts from the code.

## 4. Caps and floors

**Caps** (only when no secret or injection is present):
- Documentation/translation-only change → at most **10**
- Tests and docs only → at most **20**

**Floors** (the score can't go below these, and semantic adjustment can't lower them):

| Condition | Floor | Why |
|---|---:|---|
| Secret or credential in the diff | 90 | It's already leaked; the fix is rotation, and someone must own that |
| Destructive SQL in a migration | 75 | Data loss is irreversible |
| First-time contributor modifies CI workflows | 75 | Classic supply-chain path (secrets exfiltration via workflows) |
| `pull_request_target` / `workflow_run` added | 60 | Privileged triggers that run with secrets |
| Prompt-injection text detected | 60 | An AI gate must never be steerable by the thing it gates |
| PR edits `.pr-risk.json` | 50 | Changes to the gate's own policy need a human |

## 5. Levels and decision

| Score | Level |
|---|---|
| 0–24 | 🟢 LOW |
| 25–49 | 🟡 MEDIUM |
| 50–74 | 🟠 HIGH |
| 75–100 | 🔴 CRITICAL |

`needs_human_review = score >= threshold (default 50) OR the PR touches an always_human_review_paths glob`.

## 6. Why these signals

- **Size and churn** are the most consistently replicated predictors of defects. Code churn measures predict defect density (Nagappan & Ball, ICSE 2005), and review effectiveness falls sharply once a change exceeds a few hundred lines (SmartBear/Cisco code review study). Size is stepped rather than linear so a 2,000-line PR doesn't dwarf every other signal.
- **Sensitive paths** carry the *cost* side of risk: a bug in billing or auth costs more than a bug in a tooltip. Weights reflect typical incident severity, not likelihood.
- **Pattern rules** catch well-known vulnerability classes (OWASP Top 10: injection, XSS, insecure deserialization, security misconfiguration) and operational foot-guns.
- **Test gap** is a proxy for "how would we know if this broke?". It isn't a coverage measurement.
- **Author context** isn't about trust in people. External contributors don't know the system's implicit invariants, and CI workflows are an active attack vector against open-source repos.

## 7. Known limitations

- Path heuristics produce false positives (`tokenizer.py` isn't auth). The `tokens?` match requires a word boundary, but tune with `category_points` or rely on the semantic layer's −5 to −10 "name-only match".
- Regexes see one added line at a time. Multi-line constructs and *removed* safeguards are left to the semantic layer.
- GitHub omits patches for very large files (`stats.patch_missing`).
- The weights are informed defaults, not fitted to your history. If you have incident data, the right move is to tune `category_points` and the threshold against your own past PRs.
