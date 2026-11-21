---
title: 'Refactor sweep'
type: 'chore'
ticket: '13'
created: '2026-11-20'
status: 'built'
baseline_revision: '4b1d508ab3cc9860c4d791833f34b90e52585889'
route: 'full'
route_source: 'auto'
risk: 'low'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** epic 2 deferred 21 items to `deferred-work.md` (the entries whose `source_plan` is in `epic-author-and-test`, numbered in file order). The sweep is cleanup only: scope pushed out of a story becomes a new story.

**Approach (decision 2026-11-20, user: cleanup only):**
- **Close without code:**
  - #17 and #18: fixed by story 2.14 (neutral redaction, and the repair after the retry);
  - #20: a watch item, confirmed by 2.18 (`dry_run_error` 26.7 against 28);
  - #3: AD-11's deprecated scan belongs to epic 4 and doesn't exist yet. Record the exemption for `evals/rpcn-author__miss_kafka_connect/prompt.md` in `epic-release-sync`'s Notes, beside the rpcn-test case.
- **Do, in rpcn-test-skills only, with no change under `rpcn-skills/skills/`** (so no eval record is needed):
  - **#8:** the 2.6 design-note scenarios check their status and reply parts:
    - the edited note in `artifacts` (deviation);
    - the not-ready line in `open_questions` and in the reply (not_ready, draft);
    - that the deviation pipeline has no `orders.dlq`.
  - **#9:** a write scenario with a mapping of 3 lines or fewer asserts that no `.blobl` was written.
  - **#11:** a new runner check validates a samples file left behind, by running `rpcn_check blobl --samples` on every binary. `rpcn-test__samples_written` uses it.
  - **#19:** every rpcn-test non-compare scenario gets `bash_lacks = ["rpcn-test/references"]`.
- **Hand to Sofia as new stories, after this build:**
  - one coverage story for the 11 missing-scenario items (#1, 2, 4, 5, 6, 7, 10, 13, 14, 15, 16);
  - #12 (rpcn-author's `.blobl` rule when one mapping needs `now()` or `uuid_v4()`, a skill change);
  - #21 (the judge leaves no note on `ours` in `compare_diagnose`).

  The plan records which item goes where.

## Boundaries & Constraints

**Always:**
- Use the runner keys already there (`[[file]] exists`, `reply_contains`, `reply_lacks`, `bash_lacks`, `status_nonempty`) before adding a new one.
- Each new key is validated and tested, as the others are.
- T's tests and R's suites pass.

**Never:**
- Change anything under `rpcn-skills/skills/`.
- Write a ticket file.
- Edit old `deferred-work.md` entries.
- Add a scenario for the 11 coverage items.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| `design_deviation` | the note edited | the note is in `artifacts`; the pipeline lacks `orders.dlq` | — |
| `design_not_ready`, `design_draft` | a note that isn't ready | the reason is in `open_questions`, and in the reply | — |
| A short mapping | a 3-line mapping request | no `.blobl` written | — |
| `samples_written` | the skill writes `<name>.samples.json` | the runner check runs `blobl --samples` on both binaries and passes | a broken samples file fails it (runner test) |
| Any rpcn-test scenario | a run that lists `references/` | it fails `bash_lacks` | — |

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`; `T` = `rpcn-test-skills` (local, baseline `fafb20bfaa3b511aa993b180af30d7f7e32dac8d`; leave the untracked `orders_benthos_test.yaml` alone).

- **`R/_bmad-output/initiative-rpcn-skills/tickets/epic-release-sync/epic-release-sync.md`:** add a Notes line for #3, beside any AD-11 note already there, and cite the deferred entry.
- **`T/scenarios/rpcn-author__design_deviation`, `__design_not_ready`, `__design_draft`, `expect.toml`:**
  - the `[status]` exact match can't check list contents, so use `reply_contains` (the status block is in the reply) and `status_nonempty`;
  - for "lacks `orders.dlq`", `[[file]]` has only `contains`. Add `lacks` to `[[file]]`, or use the bounded `[[run]]` if that fits better; the builder picks the smaller one.
- **#9:** pick an existing write scenario whose mapping is 3 lines or fewer (check `rpcn-author__npx_trigger`, `existing_file` and similar fixtures and prompts), or the 2.4 tracer scenario. Add `[[file]] exists = false` for `<dir>/<name>.*.blobl`; a glob needs a small extension, otherwise name the likely label.
- **#11, `T/run_scenarios.py`:** a new `[[samples]]` check `{file}` (the samples file). It runs `rpcn_check.py blobl <blobl> --samples <file>` for each mapping the file names, from `--source`'s checker, on every binary in `RPCN_TEST_BINARIES`. It passes only on exit 0 everywhere. Reuse the binary-and-checker plumbing that `[[run]]` and `lint_binaries` already use.
- **#19:** add `bash_lacks = ["rpcn-test/references"]` to every `T/scenarios/rpcn-test__*` except the comparisons and `npx_*`. Then smoke all of them. A scenario that fails it records a finding: the skill change that fixes it is a new story, not this sweep.
- **`T/tests/test_run_scenarios.py`:** tests for any new key, and the shipped-scenario tests updated.
- **`T/README.md`:** the new keys.

## Tasks & Acceptance

**Execution:**
- [x] `epic-release-sync.md` Notes (#3).
- [x] The T runner keys (`[[file]] lacks` if needed, `[[samples]]`, the `.blobl` absence) and their tests.
- [x] The T scenario changes for #8, #9, #11 and #19, and the README.
- [x] A smoke run of every touched scenario once on both binaries, about $8. In Implementation Notes, record the results and where each of the 21 items went (closed, done, or to Sofia).

**Acceptance Criteria:**
- Given T's tests and R's `tools/` suites, when they run, then all pass, and nothing under `rpcn-skills/skills/` changed (the 2.18 eval record still matches).
- Given the smoke run, when it finishes, then every touched scenario passes. If one fails only on `bash_lacks`, it is recorded as a finding for a new story, and the sweep is not blocked.

## Implementation Notes

**Runner (T `run_scenarios.py`), each key validated and tested in `tests/test_run_scenarios.py`, and in `README.md`:**
- `[[file]] lacks`: strings the file must not hold. Not allowed with `exists = false`. Chosen over `[[run]]` as the smaller change.
- `[[file]] exists = false` takes a glob (`*`, `?`, `[`) in `file`, only with `exists = false` and inside the run folder; it fails when anything matches.
- `[[samples]] {file}`: reads the samples file's `mappings` keys and runs `blobl <folder>/<key> --samples <file>` with the installed skill's checker (installed from `--source`), on every binary in `RPCN_TEST_BINARIES`, through `run_rpcn_check` and `lint_binaries`. It passes only on exit 0 with `ok` true everywhere. A missing file, bad JSON, no mappings, or a checker rejection fails it. A runner test with the real checker shows that a broken samples file fails with exit 2, and one with both binaries shows that the samples_pass fixture passes.

**Scenarios:**
- #8: `design_deviation` gets `status_nonempty = ["artifacts"]`, `reply_contains = ['"pipes/order_fulfilment.design.md"']` (the quoted form the status block uses) and `[[file]] lacks = ["orders.dlq"]` on the pipeline. `design_not_ready` and `design_draft` get `status_nonempty = ["open_questions"]` and `reply_contains = ["not ready", "blocking"|"draft"]`. Limit: `reply_contains` matches the whole reply, so it can't prove the line sits in `open_questions` and not only in the prose. The earlier runs show it does sit there.
  `design_deviation`'s note-in-artifacts check (`reply_contains` on the quoted path) has the same whole-reply limit: the quoted form targets the status block's JSON, but it can't prove the path is in `artifacts`.
- #9: `rpcn-author__assume_headless` (2-line mapping) gets `[[file]] file = "signups/signup_feed.*.blobl"`, `exists = false`.
- #11: `rpcn-test__samples_written` gets `[[samples]] file = "pipes/orders.samples.json"`.
- #19: `bash_lacks = ["rpcn-test/references"]` on the 15 rpcn-test scenarios that lacked it. With `lint_broken` and `dry_run_pass`, that makes 17, all except `compare_*` and `npx_*`.

**Verification:** T tests: 340 passed, 3 skipped (the real-binary tests also pass with `RPCN_TEST_BINARIES` set). In R, `eval_record_check` still matches (`evals/results/2026-11-20-83e2eea0bd76.json`) and `pytest tools/tests skills` gives 146 passed. Nothing under `skills/` changed. Smoke run `T/runs/20261120-191044` ran the 21 touched scenarios, 1 run each, on 4.100.0 and 4.115.0: 21/21 pass, about $9.74. `bash_lacks` passed in all 17 rpcn-test scenarios, so there is no finding for a new story.

**Where the 21 epic-2 deferred items went:**
- Closed without code: #3 (exemption recorded in `epic-release-sync.md` Notes, beside the rpcn-test case), #17 and #18 (fixed by 2.14), #20 (watch item confirmed by 2.18).
- Done in this sweep: #8, #9, #11, #19.
- To Sofia, one coverage story: #1, #2, #4, #5, #6, #7, #10, #13, #14, #15, #16.
- To Sofia, its own story: #12 (rpcn-author's `.blobl` rule for a mapping that needs `now()`/`uuid_v4()`, a skill change).
- To Sofia, its own story: #21 (the judge leaves no note on `ours` in `compare_diagnose`).

The old `deferred-work.md` entries are left as they were (Never rule).
- **After the review fixes (2026-11-20):** R's suites (146) and T's tests (343, both binaries set) pass. Nothing under `skills/` changed, so the 2.18 eval record still matches.

## Plan Change Log

## Review Triage Log

Quick pass: 0 high, 0 medium, 5 low, 0 false, 0 maybe-false. No acceptance criterion is unmet. Four route to patch; one is a note.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | `test_missing_unparsable_or_empty_fails_without_a_call` checks for no checker call only in its last case | low | patch | Each `check()` resets `self.calls`. Fix: assert after each case. |
| 2 | `test_broken_samples_file_fails` asserts only "exit 2", which other causes also give | low | patch | Exit 2 also covers a missing file or binary. Fix: also assert the `samples@1` message. |
| 3 | `design_deviation`'s note-in-`artifacts` check can't tell `artifacts` from prose | low | note | The same limit as the other #8 checks. Recorded in Implementation Notes; the false-pass risk is low. |
| 4 | The `assume_headless` comment cites the wrong file for the 3-line rule | low | patch | The rule is in `pipeline-files.md` (and SKILL.md). Fix the comment, and note that the scenario relies on the skill keeping its mapping short. |
| 5 | Three blank lines before `FileLacksAndGlobTests` | low | patch | PEP 8 nit; delete one line. |

## Verification

**Commands:**
- `uv run tools/eval_record_check.py` (in R) — still matches
- `uv run --with pytest pytest -q tools/tests skills` (in R) — pass
- `cd T && uv run --with pytest pytest -q tests` — pass
- `cd T && RPCN_TEST_BINARIES=<abs 4.100.0>:<abs 4.115.0> uv run run_scenarios.py --jobs 4 --runs 1 --no-judge --scenario <each touched>` — all pass, or `bash_lacks`-only failures recorded
