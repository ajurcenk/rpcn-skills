# Evals

## Trigger suites for `rpcn-test`, `rpcn-author` and `rpcn-design` (R12, AD-13)

These cases measure whether Claude picks the right skill from the ways
developers actually phrase requests, and whether it stays quiet on requests
that sound related but belong elsewhere. Each case only checks which skill the
Skill tool was called for. Nothing else is graded.

| Cases | Name | Grader | Passes when |
|---|---|---|---|
| 12 positives | `rpcn-test__trigger_<slug>/` | `graders/fired.md` | `Skill` is called with `rpcn-test` |
| 5 out-of-repo negatives | `rpcn-test__miss_<slug>/` | `graders/not-fired.md` (`min: 0`, `max: 0`, `arm: both`) | no `rpcn-*` skill is ever called |
| 2 sibling negatives | `rpcn-test__miss_{write_new_pipeline,apply_report}/` | `graders/not-fired.md` (same bounds) | `rpcn-test` is never called |
| 9 positives | `rpcn-author__trigger_<slug>/` | `graders/fired.md` | `Skill` is called with `rpcn-author` |
| 3 out-of-repo negatives | `rpcn-author__miss_{deploy_k8s,kafka_connect,python_consumer}/` | `graders/not-fired.md` (same bounds) | no `rpcn-*` skill is ever called |
| 1 sibling negative | `rpcn-author__miss_lint_pipeline/` | `graders/not-fired.md` (same bounds) | `rpcn-author` is never called |
| 4 positives | `rpcn-design__trigger_<slug>/` | `graders/fired.md` | `Skill` is called with `rpcn-design` |
| 1 out-of-repo negative | `rpcn-design__miss_kafka_streams/` | `graders/not-fired.md` (same bounds) | no `rpcn-*` skill is ever called |
| 2 sibling negatives | `rpcn-design__miss_{write_yaml,lint_pipeline}/` | `graders/not-fired.md` (same bounds) | `rpcn-design` is never called |

There are two kinds of near-miss negative (decision 2026-11-06):

- **Out-of-repo** near-misses (deploying, Kafka Connect, a Python consumer,
  broker health, ...) belong outside this repo, so a negative fails when
  **any** `rpcn-` skill fires
  (`input_match: '"skill"\s*:\s*"(?:[\w-]+:)?rpcn-[\w-]+"'`): a sibling
  skill picking one up is as wrong as the case's own skill doing so.
- **Sibling** near-misses are a request that belongs to the sibling: a write
  request or a request to apply a test report's proposed changes for
  `rpcn-test`, a lint request for `rpcn-author`, and a request for the
  pipeline YAML (`rpcn-author`'s) or a lint (`rpcn-test`'s) for `rpcn-design`. They assert only
  that their own skill stayed silent (`input_match` on that skill's name). The
  sibling firing is the right answer, and the sibling's own positives cover it.

Every case sets `max_turns: 2` and `allowed_tools: [Skill]`, plus
`tags: [trigger, positive]` or `tags: [trigger, negative]`. A run that stops
with "Reached maximum number of turns (2)" is normal: the Skill call (or its
absence) is already in the transcript.

Some `rpcn-test` positives echo the description's quoted phrases and some
are new phrasings, so read the results with that in mind:

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
| `trigger_bloblang_samples` | contains "check my Bloblang mapping against its samples" verbatim |
| `trigger_dry_run` | contains "dry-run my pipeline" verbatim |
| `trigger_unit_tests` | contains "write rpk connect unit tests" verbatim |
| `trigger_design_check` | contains "check my pipeline against its design note" verbatim |

## Run it

From the repo root (the plugin root), with a logged-in Claude Code >= 2.1.269:

```
claude plugin eval . --ablation none --runs 2 --tag trigger --no-publish --trust-plugin --json <out>.json
uv run tools/eval_gate.py <out>.json
```

- `--ablation none` runs only the with-plugin arm, so the `tool_used: Skill`
  graders count toward the score instead of being a with-only indicator.
- `--no-publish` keeps the HTML report local; nothing goes to claude.ai.
- `--runs 2` is the AD-13 minimum (decision 2026-11-21; it was 3).
- `claude plugin eval` also writes `evals/results/<timestamp>/`. Those
  timestamped folders are gitignored (`evals/results/*/`); the eval-record
  files `evals/results/<date>-<skills-hash>.json` (AD-14) are not, because
  they are committed with the change.

To try a single case, add `--case 'rpcn-test__trigger_lint_pipeline' --runs 1`.
The gate rejects such a file (exit 2), because it needs the full suite.

## Recording a run

Every change that affects a skill (anything under `skills/`) carries an eval
record (R12, AD-14). CI does not run evals; it only checks that a passing
record exists for the exact skill content.

```
uv run tools/run_evals.py [--test-project ../rpcn-test-skills] [--runs 2] [--with-compare]
                          [--concurrency 4] [--jobs 4]
```

It runs, in order: the `rpcn-test-skills` runner's own unit tests
(`uv run tests/test_run_scenarios.py` in the test project, free; a failure is
exit 2 before any paid step, naming the failed tests), the skills hash, the
trigger suite above, the gate (with `--cases-dir` set to this `evals/`), and
the `rpcn-test-skills` pass scenarios (`run_scenarios.py --source local:<this
repo>`). `--with-compare` adds the comparison scenarios (`[compare] enabled =
true`: `rpcn-test__compare_lint`, `rpcn-test__compare_diagnose` and
`rpcn-author__compare_write`, about +$12, so about $55 in all). Each is scored
the same way in every arm: its `score` is the known causes the reply names
(`[[compare.errors]]`) plus points on the file the arm writes
(`[[compare.files]]`: lints clean, a bounded run gives the expected outputs,
contains a string), with this repo's `rpcn_check.py` on both pinned binaries;
ties go to the blind judge's rank, then cost (the test project's README has the
details). The record's `compare` maps each comparison scenario to its winner.
A passing run writes
`evals/results/<YYYY-MM-DD>-<skills-hash12>.json`. A failing run still writes
its record, as `<YYYY-MM-DD>-<skills-hash12>.failed-<HHMMSS>.json`: the check
ignores that name, so a failed re-run never replaces a passing record. `passed`
is true only when the gate is ok, every scenario passed and `run_scenarios.py`
exited 0 with no crashed comparison arm. Exit 0 passed, 1 not passed, 2 setup
error (no record), which includes a gate exit 2 (an incomplete suite): then no
scenario runs.

A record can pass only with `--runs` 2 or more, because the gate requires 2
runs per trigger case. `--runs 1` is a smoke run that never passes.

**Run time and parallelism.** One session at a time, a full default run
took about 58 minutes (story 2.8: 954 s for the trigger gate's 90 sessions,
2,522 s for the 69 scenario runs). Two flags run sessions in parallel at the
same cost and the same 3-run bar, aiming at about 16-18 minutes:

- `--concurrency <n>` (1-8, default 4) is passed to `claude plugin eval` as
  `--concurrency`: up to n trigger sessions at once. Results keep case order.
- `--jobs <n>` (1-8, default 4) is passed to `run_scenarios.py` as `--jobs`:
  up to n scenario runs at once. `results.json` keeps scenario and run order;
  comparison scenarios still run one at a time, after the others.

The stages stay in order: the trigger gate finishes before any scenario
starts. Every session shares one Claude account rate limit, so a higher value
can hit it; `--concurrency 1 --jobs 1` is the old sequential run.

- **Commit the record** with the change. CI's step `Eval record matches the
  skills (R12)` runs `uv run tools/eval_record_check.py` and fails unless a
  record with the current skills hash and `passed: true` is committed.
- **The skills hash** is the sha256 over every git-trackable file under
  `skills/` (path, NUL, file sha256, newline, in path order; no
  `__pycache__/`, nothing gitignored). Edits to `evals/`, `tools/` or docs
  don't change it, so they need no new record. Any byte under `skills/` does.
- **Cost:** about $38 for a default run at 2 runs (trigger suite ~$5.50, the
  fifty pass scenarios x 2 ~$33; it was about $47 at 3 runs with forty: one
  pass of thirty-eight of them at `--runs 1` cost $12.39 in story 3.1, plus about
  $0.40 for the two added after it, story 3.2's five `rpcn-design__pattern_*`
  scenarios cost about $0.42 a run each, and story 3.3's five
  `rpcn-design__ask_*` scenarios about $1.90 a run together; the three-step
  `rpcn-design__chain_tracer` is the largest at about $1.25 a run). The record's `cost_usd` holds the measured total.

## The gate

`tools/eval_gate.py <aggregate-result.json> [--min-accuracy 0.9] [--min-runs 2] [--cases-dir evals]`
counts every run of every `<skill>__trigger_*` and `<skill>__miss_*` case, for
any skill (the eval output has no tags, so the name decides). A run is correct
when its trigger grader passed and its `error` does not start with `API`.

**The case list.** The trigger case names in the result must equal the
`<skill>__trigger_*` and `<skill>__miss_*` folders in `--cases-dir` (default:
this `evals/` folder). A folder with no result (a dropped case) or a result
with no folder (an unknown case) is an incomplete suite: exit 2, with each one
named in `errors` and in `error`. So the suite can't shrink unnoticed.

| Exit | Meaning |
|---|---|
| 0 | accuracy >= 0.9 and no negative run fired the skill |
| 1 | accuracy below the minimum, or any negative run fired; see `failed_runs` |
| 2 | missing or unreadable file, `schemaVersion` not the integer 1, no trigger cases, no trigger case folders in `--cases-dir`, an incomplete suite (no positive or no negative case, a case with fewer than `--min-runs` runs, a missing or extra case), or a partial run |

When the gate fails, `failed_runs` lists the phrasings to address. Fixing them
means changing the skill's description, which is a separate decision.

## Cost

About $0.07 and 7 s per run, so roughly $5.50 for the full 39 cases x 2 runs ($8.20 at 3).
These evals run locally only, never in CI (CI holds no Claude credentials).
