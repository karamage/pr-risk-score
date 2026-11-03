# Contributing

Thanks for helping make PR triage less painful.

## Development

```bash
python3 -m unittest discover -s tests -v       # no dependencies to install
python3 skills/pr-risk-score/scripts/pr_risk.py owner/repo#123   # try it on a real PR
```

The scorer must stay **stdlib-only and Python 3.8 compatible**. That's what lets it run in any CI image and any agent sandbox without setup.

## Adding or changing a rule

1. Add or edit the entry in `RULES` or `SENSITIVE_CATEGORIES` in `skills/pr-risk-score/scripts/pr_risk.py`.
2. Add a test for a true positive **and** a likely false positive (see `test_regex_exec_is_not_eval`).
3. Regenerate the docs table: `python3 skills/pr-risk-score/scripts/pr_risk.py --list-rules` and paste it into `references/scoring-model.md` §3 (a test fails if they drift).
4. In the PR, include a real public PR where the change makes the score better.

## What makes a good rule

- **High precision over high recall.** A noisy rule trains people to ignore the score. The semantic layer exists for the subtle cases.
- **One line, added code only.** Rules see added lines one at a time, so anything that needs multi-line context belongs in `references/semantic-review.md`.
- **Explain the risk, not the syntax.** The `msg` is shown to reviewers.

## Weights

Weight changes are welcome when they come with evidence: before-and-after scores on a set of real PRs, ideally including ones that later caused incidents or reverts.
