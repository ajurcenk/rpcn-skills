# Evals

## Trigger suite for `rpcn-test` (R12, AD-13)

These cases measure whether Claude picks the `rpcn-test` skill from the ways
developers actually phrase requests, and whether it stays quiet on requests
that sound related but belong elsewhere. Each case only checks whether the
Skill tool was called for `rpcn-test`. Nothing else is graded.

| Cases | Name | Grader | Passes when |
|---|---|---|---|
| 8 positives | `rpcn-test__trigger_<slug>/` | `graders/fired.md` | `Skill` is called with `rpcn-test` |
| 6 near-miss negatives | `rpcn-test__miss_<slug>/` | `graders/not-fired.md` (`min: 0`, `max: 0`, `arm: both`) | `rpcn-test` is never called |

Every case sets `max_turns: 2` and `allowed_tools: [Skill]`, plus
`tags: [trigger, positive]` or `tags: [trigger, negative]`. A run that stops
with "Reached maximum number of turns (2)" is normal: the Skill call (or its
absence) is already in the transcript.

Some positives echo the description's quoted phrases and some are new
phrasings, so read the results with that in mind:

| Case | Relation to the description |
|---|---|
| `trigger_test_pipeline` | contains "test my pipeline" verbatim |
| `trigger_check_yaml_errors` | close paraphrase of "check this Redpanda Connect config" |
| `trigger_rpk_version` | close paraphrase of "which rpk connect version do I have" |
| `trigger_installed` | close paraphrase of "is Redpanda Connect installed" |
| `trigger_lint_fails` | close paraphrase of "why does my pipeline fail lint" |
| `trigger_lint_pipeline` | new phrasing ("run a lint over …") |
| `trigger_config_valid` | new phrasing ("is this config valid") |
| `trigger_inline_broken` | new phrasing: a broken config pasted inline, with no trigger phrase |

## Run it

From the repo root (the plugin root), with a logged-in Claude Code >= 2.1.269:

```
claude plugin eval . --ablation none --runs 3 --tag trigger --no-publish --trust-plugin --json <out>.json
uv run tools/eval_gate.py <out>.json
```

- `--ablation none` runs only the with-plugin arm, so the `tool_used: Skill`
  graders count toward the score instead of being a with-only indicator.
- `--no-publish` keeps the HTML report local; nothing goes to claude.ai.
- `--runs 3` is the AD-13 minimum.
- `claude plugin eval` also writes `evals/results/<timestamp>/`. Those
  timestamped folders are gitignored (`evals/results/*/`); the eval-record
  files `evals/results/<date>-<skills-hash>.json` (AD-14) are not, because
  they are committed with the change.

To try a single case, add `--case 'rpcn-test__trigger_lint_pipeline' --runs 1`.
The gate rejects such a file (exit 2), because it needs the full suite.

## The gate

`tools/eval_gate.py <aggregate-result.json> [--min-accuracy 0.9] [--min-runs 3]` counts every
run of every `rpcn-test__trigger_*` and `rpcn-test__miss_*` case (the eval
output has no tags, so the name prefix decides). A run is correct when its
trigger grader passed and its `error` does not start with `API`.

| Exit | Meaning |
|---|---|
| 0 | accuracy >= 0.9 and no negative run fired the skill |
| 1 | accuracy below the minimum, or any negative run fired; see `failed_runs` |
| 2 | missing or unreadable file, `schemaVersion` not the integer 1, no trigger cases, an incomplete suite (no positive or no negative case, or a case with fewer than `--min-runs` runs), or a partial run |

When the gate fails, `failed_runs` lists the phrasings to address. Fixing them
means changing the `rpcn-test` description, which is a separate decision.

## Cost

About $0.07 and 7 s per run, so roughly $3 for the full 14 cases x 3 runs.
These evals run locally only, never in CI (CI holds no Claude credentials).
