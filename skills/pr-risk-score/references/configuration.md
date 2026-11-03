# Configuration: `.pr-risk.json`

Put a `.pr-risk.json` at the repository root. Every key is optional.

**The config is read from the PR's base commit, not from the PR itself.** A PR that edits `.pr-risk.json` is scored with the *old* policy and gets a floor of 50, so a pull request can't lower its own bar. In `--local` mode the file is read from the merge base (falling back to the working tree). `--config PATH` overrides both.

```jsonc
{
  // Score at or above which a human must review. Default 50 (HIGH).
  // 25 = cautious (every MEDIUM gets a human), 75 = only CRITICAL.
  "human_review_threshold": 50,

  // Paths excluded entirely (no size, no sensitivity, no pattern checks).
  // Gitignore-style globs: ** crosses directories, a pattern with no "/" matches at any depth.
  "ignore_paths": ["**/__snapshots__/**", "fixtures/large/**"],

  // Your own sensitive areas, added on top of the built-in categories.
  "sensitive_paths": [
    { "name": "pricing-engine", "label": "pricing engine", "patterns": ["services/pricing/**"], "points": 20 },
    { "name": "tenant-isolation", "patterns": ["**/tenancy/**", "**/row_level_security*"], "points": 25 }
  ],

  // Any PR touching these needs a human, whatever the score.
  "always_human_review_paths": ["infra/prod/**", "db/migrate/**"],

  // Re-weight or disable built-in categories (0 disables).
  // Keys: security, payments, data_migration, infrastructure, public_api, governance, config, dependencies
  "category_points": { "dependencies": 3, "config": 0 },

  // Turn off pattern rules by id (see scoring-model.md for the list).
  "disable_rules": ["todo-marker", "concurrency"],

  // Keep a rule on, but skip it for specific paths (e.g. docs that *quote* prompt injection).
  "rule_ignore_paths": { "prompt-injection": ["docs/security/**"], "concurrency": ["pkg/workerpool/**"] }
}
```

The file must be strict JSON. The comments above are for illustration only; `assets/pr-risk.example.json` is a copy-paste-ready version.

## Tuning recipes

| Goal | Change |
|---|---|
| Fewer humans on a mature, well-tested repo | `"human_review_threshold": 60` |
| Every DB change gets a DBA | `"always_human_review_paths": ["db/**", "**/migrations/**"]` |
| Monorepo: one team's code is critical | add a `sensitive_paths` entry with `points: 25` |
| Noisy rule in your codebase (e.g. heavy goroutine use) | `"disable_rules": ["concurrency"]` |
| Docs site repo where `config/` is harmless | `"category_points": {"config": 0}` |

## CLI overrides

`--threshold N` overrides `human_review_threshold`. `--config PATH` replaces the auto-loaded file. `--fail-above N` makes the CLI exit with code 3 at or above N, independent of the threshold, which is useful for a hard CI gate (e.g. block merges ≥ 90 until a secret is rotated).
