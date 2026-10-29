---
title: 'Trigger evals and the accuracy gate for rpcn-test'
type: 'feature'
ticket: '7'
created: '2026-10-29'
status: 'built'
baseline_revision: '6290d06b5848aa2b847ad5fe5c34f0724220750d'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Every check so far assumed Claude picks `rpcn-test` from a prompt like "lint …". No measure exists of how often it triggers on the ways developers actually phrase requests, or of whether it stays quiet on requests that sound similar but belong elsewhere. R12 sets that bar at 90%.

**Approach:** Add native `claude plugin eval` trigger cases to `rpcn-skills/evals/`:
- **positives:** realistic phrasings that must invoke `rpcn-test`
- **near-miss negatives:** requests that sound related and must not invoke it

Add `tools/eval_gate.py`, which reads `aggregate-result.json`, computes suite trigger accuracy over every run, and fails when accuracy is below 90% or any negative run triggered the skill.

## Boundaries & Constraints

**Always:**
- **Case layout (AD-13):** cases live in `evals/rpcn-test__<case>/` with `prompt.md` and `graders/`. Positive cases are named `rpcn-test__trigger_<slug>`, negative cases `rpcn-test__miss_<slug>`. `eval_gate.py` tells them apart by that prefix, because the eval output doesn't carry tags. Each case's frontmatter also sets `tags: [trigger, positive]` or `tags: [trigger, negative]` for `--tag` filtering.
- **Case limits:** `max_turns: 2` and `allowed_tools: [Skill]`. The grader only needs to see whether the skill fired, so the cases stay cheap (a probe run cost $0.066 and took 7 s). A run that hits the turn limit still counts, because the Skill call is already in the transcript.
- **Graders:**
  - A positive case has one grader, `graders/fired.md`: `type: tool_used`, `tool: Skill`, `input_match: '"skill"\s*:\s*"(?:[\w-]+:)?rpcn-test"'`. This was verified on Claude Code 2.1.312.
  - A negative case has `graders/not-fired.md` with the same `tool` and `input_match`, plus `min: 0`, `max: 0` and `arm: both`.
- **The cases:** 8 positives and 6 negatives, written as a developer would phrase them.
  - **Positives** cover: lint a pipeline; "is this config valid"; "why does `rpk connect lint` fail on …"; "test my pipeline"; "check this Redpanda Connect YAML for errors"; "which rpk connect version do I have"; "is Redpanda Connect installed"; and a request that pastes a short broken config inline.
  - **Negatives** cover:
    - writing a new pipeline from scratch (that's Author's job)
    - explaining what Bloblang is
    - deploying a pipeline to Kubernetes
    - checking a Redpanda *broker* cluster's health
    - linting a Python file
    - writing a Kafka Connect connector config
- **The eval command:**
  ```
  claude plugin eval . --ablation none --runs 3 --tag trigger --no-publish --trust-plugin --json <out>
  ```
  - `--ablation none` makes the Skill graders count toward the score.
  - `--no-publish` keeps the report local, so nothing goes to claude.ai.
  - The command is documented in `evals/README.md`.
- **`tools/eval_gate.py`:** a PEP 723 script, standard library only, run with `uv run` (AD-3).
  - **Input:** `eval_gate.py <aggregate-result.json> [--min-accuracy 0.9]`.
  - **What it counts:** every `rpcn-test__trigger_*` and `rpcn-test__miss_*` run in `cases[].arms.with[]`. A run is correct when its trigger grader `passed` and `error` doesn't start with `API`.
  - **Output:** one JSON object, `{"ok", "accuracy", "runs_total", "runs_correct", "positives": {"runs", "correct"}, "negatives": {"runs", "correct"}, "failed_runs": [{"case", "run", "explanation"}], "partial": bool}`.
  - **Exit codes:**
    - 0 when accuracy is at least the minimum and every negative run is correct
    - 1 when not
    - 2 for a missing or unreadable file, an unknown `schemaVersion`, no trigger cases, or `partial: true`
- **Unit tests:** `tools/tests/test_eval_gate.py` (unittest, PEP 723) uses small synthetic `aggregate-result.json` files shaped like the real one. It covers:
  - all pass
  - below 90%
  - one negative firing while overall accuracy is still at least 90% (must fail)
  - a partial run
  - an API-error run counted as incorrect
  - no trigger cases
  - a bad file
- **CI:** add `tools/tests/test_eval_gate.py` to the existing workflow. The evals themselves stay local (decision 2026-10-23).
- **Results:** `evals/results/` is gitignored, since `claude plugin eval` writes there.

**Never:**
- running evals in CI, or publishing reports to claude.ai
- grading anything except Skill invocation in these cases
- changing `rpcn-test`'s description in this story. If accuracy is below 90%, the description fix is a follow-up the user decides on.
- copying eval files from other repos

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| All correct | 14 cases × 3 runs, every grader passed | `accuracy: 1.0`, exit 0 | — |
| Below 90% | 5 of 42 runs wrong | `accuracy: 0.881`, `ok: false`, exit 1, `failed_runs` listed | — |
| A negative fires | one miss run fails, accuracy still at least 90% | exit 1, because negatives must never fire | — |
| Partial suite | `partial: true` | exit 2 with `partialReason` | — |
| API error run | `error: "API …"`, graders not run | counted as incorrect | — |
| No trigger cases | no case name with either prefix | exit 2 | — |
| Bad file | missing, not JSON, or `schemaVersion` isn't 1 | exit 2 | — |
| Max-turns error | `error: "exit 1: Reached maximum number of turns (2)"` and the grader passed | counted as correct | — |

</frozen-after-approval>

## Code Map

- **Plugin root:** `rpcn-skills/` with `.claude-plugin/plugin.json` (`rpcn-skills` 0.1.0). Skills are in `skills/`. Running `claude plugin eval .` from the root finds `evals/` automatically.
- **The current description** is the trigger text under test, in `skills/rpcn-test/SKILL.md`. Its phrases: "lint my pipeline", "check this Redpanda Connect config", "why does my pipeline fail lint", "test my pipeline", "check my Redpanda Connect binary", "which rpk connect version do I have", "is Redpanda Connect installed", "rpcn-test", and "Not for writing, designing or deploying pipelines". The positive cases must use phrasings beyond these, so the eval measures how well the description generalises rather than echoing it.
- **The output schema,** verified with a 1-run probe on 2026-10-29:
  - **Top level:** `schemaVersion: 1`, `partial`, `aggregates{casesTotal, casesPassed, overallScore, overallPassRate}` and `costUsd`.
  - **Per case:** `cases[]{name, aggregates{score, passRate}, arms{with[]}}`.
  - **Per run** (`with[]`): `{score, passed, error, costUsd, turns, graders[{name, passed, explanation, scored, withOnly}]}`. `tags` isn't in the output.
- **Existing tool scripts:** `tools/sync_shared.py` and `tools/fetch_rpcn.py` show the style (PEP 723, docstring, JSON output). Their tests live in `tools/tests/` (`test_sync_shared.py`).
- **CI:** `.github/workflows/ci.yml` runs the steps in this order: drift check, cache, fetch, `rpcn_check` tests, `sync_shared` tests. Add an `eval_gate tests` step.
- **`.gitignore`:** add `evals/results/`.

## Tasks & Acceptance

**Execution:**
- [x] `evals/rpcn-test__trigger_*/` (8) and `evals/rpcn-test__miss_*/` (6) -- `prompt.md` plus one grader each -- the trigger suite
- [x] `evals/README.md` -- what the suite measures, the exact command, how to gate, cost (about $0.07 per run, so about $3 for 14 × 3) -- usage
- [x] `tools/eval_gate.py` -- the gate per the Boundaries -- R12
- [x] `tools/tests/test_eval_gate.py` -- every matrix row -- gate correctness
- [x] `.github/workflows/ci.yml` -- an `eval_gate tests` step -- tests in CI
- [x] `.gitignore` -- `evals/results/` -- no eval output committed

**Acceptance Criteria:**
- Given the suite run with the command in Boundaries (3 runs), when `uv run tools/eval_gate.py <out>.json` runs, then it reports `accuracy >= 0.9` and every negative run correct, with exit 0. If not, the failing phrasings are listed for a description fix.
- Given `uv run tools/tests/test_eval_gate.py`, then every test passes.

## Implementation Notes

- The plugin root is the repo root, so the paths are `evals/`, `tools/` and `.github/` at the top level. The Code Map's `rpcn-skills/` prefix means that root.
- Cases are frontmatter-only (`prompt.md` plus `graders/`), with no `case.yaml`, the same as the 2026-10-29 probe.
- Runs in `arms.with[]` have no index field, so `failed_runs[].run` is the run's 1-based position.
- The gate looks for the grader by name: `fired` for `trigger_` cases and `not-fired` for `miss_` cases. If that grader is missing, for example because graders didn't run, the run counts as incorrect.
- When the input is partial, the gate copies its `partialReason` into the output and exits 2.
- `--case` does not support brace globs. The 1-run probe used `--case 'rpcn-test__*_lint_p*'`, which matched `trigger_lint_pipeline` and `miss_lint_python`. Both passed, and the gate exited 0 with accuracy 1.0. Cost was $0.12 for 2 runs, and each run ended with the expected max-turns error.
- In `trigger_rpk_version`, the prompt says "redpanda input and output" rather than naming `redpanda_migrator`, so a future deprecated-name scan (AD-11) can't trip on it.
- **Full suite (orchestrator, 2026-10-29),** 14 cases × 3 runs on Claude Code 2.1.312. It cost $3.44 and took 532 s. `claude plugin eval` exits 1 because its per-case threshold defaults to 1.0; `eval_gate.py` is the gate.
  - **Gate:** `accuracy: 0.929` (39 of 42), `ok: true`, exit 0.
  - **Negatives:** 18 of 18 correct.
  - **Positives:** 21 of 24 correct. `rpcn-test__trigger_inline_broken` failed in all 3 runs: Claude answered the config pasted into the prompt directly, without invoking the skill.
  - **Follow-up for the user:** the description may need to cover a config pasted into the prompt, or the skill's file-based design makes a direct answer acceptable there.
- **After the review fixes:** 20 gate tests pass. Re-running the stricter gate on the saved full-suite output (`/tmp/claude-1000/trigger.json`) still gives `ok: true`, `accuracy: 0.929`, negatives 18 of 18, exit 0. The earlier 1-run probe now exits 2 as an incomplete suite, which is intended.

## Plan Change Log

## Review Triage Log

**Pass 1 (quick):** 6 → patch, 1 deferred, 1 rejected.

| # | Finding | Verdict | Route | Evidence |
|---|---|---|---|---|
| 1 | `partial` and `partialReason` are lost on the exit-2 paths raised after they're copied | low | patch | `main()` prints a fresh `empty_result()` and drops the reason. |
| 2 | The gate passes incomplete suites (no negatives, or fewer than 3 runs) | medium | patch | `negatives_clean` is true when there are 0 negative runs, and runs per case aren't checked. AD-13 needs at least 3 runs and negatives that stay silent. |
| 3 | `schemaVersion` set to `true` or `1.0` is accepted | low | patch | `!=` treats them as equal to 1. A direct type check fixes it. |
| 4 | The README says no positive echoes the description, but `trigger_test_pipeline` does | low | patch | Doc correction. Accuracy is partly measured on echoed phrases, and the README will say so. |
| 5 | The `miss_kafka_connect` prompt may trip AD-11's future scan of deprecated names | low | defer | The scan doesn't exist yet (epic 4). It must tolerate "Kafka Connect" as plain text. Recorded in `deferred-work.md`. |
| 6 | `.gitignore` `evals/results/` conflicts with AD-14's committed eval-record file | medium | patch | It would hide `evals/results/<date>-<hash>.json`. The fix narrows it to the timestamped folders. |
| 7 | The task checkboxes weren't ticked | low | patch | Ticked by the orchestrator. |
| 8 | Acceptance criterion 1 is met only by recorded output | low | reject (false) | The orchestrator ran the suite and recorded accuracy 0.929 and exit 0. |

## Verification

**Who runs what:** the implementer writes the cases, the gate and its tests, and runs only the unit tests, plus at most a `--runs 1` run of one positive and one negative case. The orchestrator runs the full 3-run suite, with progress shown to the user.

**Commands** (from `rpcn-skills`):
- `uv run tools/tests/test_eval_gate.py` -- expected: all pass
- `claude plugin eval . --ablation none --runs 3 --tag trigger --no-publish --trust-plugin --json /tmp/claude-1000/trigger.json`, then `uv run tools/eval_gate.py /tmp/claude-1000/trigger.json` -- expected: `accuracy >= 0.9`, exit 0
