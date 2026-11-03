# Semantic Review Rubric

The deterministic baseline sees *where* a PR changes things and *which tokens* it adds. It can't see *what the change means*. This rubric covers that gap. You produce two things:

- an **adjustment** between −20 and +20, built from the items below, each backed by a `file:line` citation
- zero or more **escalations**: confirmed critical mechanisms that send the PR to a human no matter how low the baseline is

## Contents
1. How to read the diff
2. Adjustments (+ and −)
3. Escalation
4. Combining, and handling uncertainty
5. Worked examples (fictional)

---

## 1. How to read the diff

Spend your attention where the risk is:

1. Files in `hotspots`. When no rule fired, these are the largest code changes.
2. Files with harmless names that do dangerous things. Look for calls that delete, charge, send, publish, grant, revoke, or overwrite, and for anything that changes who is allowed to do what.
3. Deleted lines, not just added ones. Removed checks, removed `WHERE` clauses, removed validation, and removed tests are where the regex layer is weakest.
4. The review discussion (`gh pr view --comments`). Concerns raised by bots or reviewers that the author dismissed are exactly the judgment calls a human should own.

Ask five questions of each hotspot:

- **Who can trigger it?** Logged-in owner only, any logged-in user, or anyone on the internet? Changes reachable without authentication deserve the most scrutiny.
- **Blast radius.** If this is wrong, who notices? One page, one tenant, every request, other services?
- **Reversibility.** Can a revert fully undo it? Data writes, deleted credentials, migrations, sent emails, published events, and external API calls can't be reverted.
- **Detectability.** Would a bug here fail loudly (crash, test failure) or quietly (wrong number, missing permission check)?
- **Evidence of care.** Are there tests that exercise *this* behavior, a feature flag, a staged rollout, or a clear description of how it was verified?

## 2. Adjustments

### Upward (+)

| Signal | Typical |
|---|---:|
| Authorization or validation removed or weakened | +8 to +15 |
| State change reachable by unauthenticated or less-privileged callers (see also §3) | +8 to +15 |
| Irreversible effect: data rewrite or delete, credential wipe, outbound side effect | +8 to +15 |
| Changed defaults or fallbacks that affect every caller | +5 to +10 |
| Contract change visible to other services or clients, without versioning | +5 to +10 |
| Concurrency, ordering, transaction-boundary, or idempotency change | +5 to +10 |
| Money, quotas, rate limits, or time arithmetic (time zones, rounding, currency) | +5 to +10 |
| Breaking change for scripts or automation (new required flag, changed exit code) | +3 to +5 |
| Error handling that turns failures into silent success | +3 to +8 |
| Hard to roll back (coupled deploy order, schema or cache version bump, mobile release) | +3 to +8 |
| Description doesn't match the diff, or its claims are unverified | +3 to +5 |
| A reviewer's or bot's concern about this area is unresolved or was dismissed | +3 to +5 |
| Too large or too opaque to review meaningfully in this pass | +5 |
| Security-relevant dependency major bump (crypto, auth, TLS, ORM, serializer) | +5 to +10 |

### Downward (−)

Only lower the score when you have **positive evidence** of safety, not just an absence of red flags. The baseline already gives low scores to boring changes.

| Signal | Typical |
|---|---:|
| Purely mechanical (rename, move, formatting), verified by the diff shape | −5 to −10 |
| Sensitive path matched by name only; the change itself is cosmetic | −5 to −10 |
| Behind a default-off feature flag, *and* tests cover both branches | −5 |
| Tests that directly exercise the risky behavior were added in this PR | −3 to −8 |
| Existing tests (from earlier PRs) demonstrably cover the changed behavior, and CI ran them green | −2 to −5 |
| Dependency patch or minor bump with no API change, from a bot, with green CI | −3 to −5 |
| Generated or vendored code that the baseline didn't recognize | −5 to −10 |

**Don't re-score what the baseline already counted.** Size, spread, path sensitivity, and the test gap are already in the baseline. Add points for them only with *new* information, such as "the only test mocks out the exact function that changed". One mechanism gets one item. A separate *process* signal about the same line (a dismissed bot finding, a description that contradicts the code) is different evidence and may be its own item.

Never go below a floor reported in `adjustments[]`. A leaked secret stays at 90+ even if the PR "only adds a test fixture". Rotating the key is the fix, not a lower score.

## 3. Escalation

The ±20 bound protects against a model talking a PR *down*. It shouldn't stop a concrete, serious finding from reaching a human. Mark an item as **escalation** when you can point at the line and explain the mechanism in one sentence, and it falls in one of these classes:

| Class | Example mechanism |
|---|---|
| Authorization bypass or privilege gain | a check moved after the action; `||` turned an AND into an OR |
| Unauthenticated (or cross-user) change to someone else's account, credentials, or data | a public endpoint wipes, resets, or links another user's credentials |
| Irreversible data loss at scale | a bulk delete or update with a missing or widened filter |
| Secret or personal data exposure | tokens logged, PII sent to a third party, a debug endpoint left open |
| Money moved incorrectly | double charge, refund without a check, rounding on stored amounts |

Escalate when the mechanism is **triggerable by someone other than the affected party** (another user, an anonymous caller, a background job acting on everyone), or when the harm **can't be undone**. A narrow, self-inflicted, easily recovered effect fits the class name without the impact, so don't escalate it. Give it a normal +5 to +12 item and a focus note instead. When in doubt, ask: "would the team want to know about this *before* merge, even if the answer turns out to be fine?" If yes, escalate.

Effect: `score = max(score, 60)` and the decision is **Human review required**. Still list the item with its ± points, so the number and the evidence stay consistent.

Don't escalate on a hunch. "This is auth code, so it might be risky" is what the baseline already scored. Escalation requires a specific mechanism you verified in the diff, or in the file at head when the diff alone is ambiguous.

## 4. Combining, and handling uncertainty

1. List the items, each as `±N — file:line — one sentence`, marking escalations.
2. Sum them and clamp the sum to [−20, +20].
3. `score = clamp(baseline + adjustment, lower = highest floor, upper = 100)`, then apply escalation.
4. If the final score lands within ±3 of the threshold, decide for human review and say that's what you did.

How to size an item depends on what you know:

- **Confirmed mechanism** (you traced it in the code): use the full range in the table, and consider escalation.
- **Plausible but unverified** (you couldn't see the caller, or the config that enables it): use the low end of the range, say what you couldn't verify, and put it in the reviewer focus list.
- **Pure speculation**: no points. Mention it only if it's cheap for a human to check.

Calibrating your instinct: a typical well-tested feature PR gets 0 to +5. Reserve +15 and above for a specific, cited mechanism that could cause an incident.

## 5. Worked examples (fictional)

These are made up on purpose, so they teach the reasoning without anchoring you to a real PR.

**A. "Add bulk archive to the projects API" (baseline 22, LOW)**
- +8 — `api/projects/archive.go:57` — archives every project matching the filter in one transaction; an empty filter archives the whole tenant.
- +3 — `api/projects/archive.go:31` — new endpoint, with no rate limit or per-request cap.
- −5 — `archive_test.go:12-140` — tests cover the empty filter (rejected with 400) and cross-tenant IDs (ignored).
→ +6 → **28 MEDIUM**. AI review is sufficient. Focus note: confirm that the 400 on an empty filter also covers `filter={}`.

**B. "Simplify session cleanup" (baseline 31, MEDIUM)**
- +15 — `jobs/expire_sessions.rb:27` — `Session.where(user_id: id).delete_all` became `Session.delete_all`, which logs out every user. **⚠ escalation: irreversible effect at scale.**
- +3 — the description says "no behavior change", but behavior changes.
→ +18 → 49, escalated → **60 HIGH, Human review required**.

**C. "Auto-link Google sign-in to existing accounts" (baseline 30, MEDIUM)**
- +12 — `auth/oauth/callback.ts:64` — a Google login is linked to any existing account with the same email, even when the provider reports `email_verified: false`. That's an account takeover for anyone who can register that address with the provider. **⚠ escalation: unauthenticated change to another user's credentials.**
- +3 — a bot review flagged this line and the author dismissed it without discussion.
- −4 — `callback.test.ts` — the tests cover the verified-email path only.
→ +11 → 41, escalated → **60 HIGH, Human review required**. Focus note: require `email_verified`, or require the user to log in to the existing account before linking.

**D. Dependabot bumps a crypto library, minor version (baseline 6, LOW)**
- +5 — `go.mod:12` — a security-relevant library, though minor versions are usually API-stable.
- −3 — bot-authored, no code changes, green CI.
→ +2 → **8 LOW**.
