---
title: 'Test diagnoses failures with a fix that passes'
type: 'feature'
ticket: '11'
created: '2026-11-13'
status: 'built'
baseline_revision: 'bf7877b0a0553db1839dbc64f2b7e1d024bdf868'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** rpcn-test already proposes a diff for each failed check, but nothing proves the diff passes: the scenarios only look for a `+++ b/<file>` line. A Design check fix is checked by lint alone, a dry-run failure with an unclear cause gets no item, and a fault in Test's own files (`<name>.samples.json`, `<name>_benthos_test.yaml`) is never fixed (R8, AD-6).

**Approach:**
- Every failed check (lint, samples, dry run, unit tests, Design check) gets one Proposed changes item per cause: a stated cause, a diff, and a check of that diff against the check that failed. A diff that still fails after two revisions, or can't be checked, ends its title with `(unverified)`.
- Fixes to Test's own files are applied by rpcn-test, re-run, and listed. Fixes to Author's files stay proposed diffs, and Next names rpcn-author.
- The runner proves it: a new `[[fix]]` check applies each verified diff from the report to a copy of the project and re-runs the failed check on both binaries.

**Decisions (2026-11-13, user):**
- **Test's own files:** rpcn-test edits its existing `<name>.samples.json` or `<name>_benthos_test.yaml` only for a fault in the file itself. That covers a shape error, and a missing or stale mock (a label or path the pipeline no longer has, or an unmocked outside call). It also covers an expected value that the request or a ready note states differently; the item then quotes that sentence. It never changes a value to match the pipeline's output. This narrows 2.7's "never change an expected value" and 2.9's "run an existing file as is" to these faults.
- **Design fix check:** lint the fixed copy, then re-read it against the section as `design-check.md` §2–3 does. It is verified only when the row would be `ok`; otherwise it is `(unverified)`.

## Boundaries & Constraints

**Always:** AD-6 (one writer per file); expected values come from intent, never from what the pipeline printed; the report keeps its seven sections (`test-report@2`); both `SKILL.md` limits (4,803 characters, description 1,024); validator warning-free for both skills; AD-15 rows for any new binary fact.

**Never:** edit the pipeline, a `.blobl`, `<res>` or the note; change an expected value to match the pipeline's output; run anything against an outside service.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Lint error | `lint_broken` | Item per error; the patched copy lints clean | Still failing after 2 revisions: `(unverified)` |
| Sample fail | `samples_bug` | `.blobl` diff; patched `blobl` run passes the same samples | Same |
| Dry-run error | `dry_run_error` | Pipeline diff; patched `run` on the report's input messages exits 0 | Unclear cause: best diff, `(unverified)`, a question |
| Unit fail | `unit_bug` | Pipeline diff; patched `test` passes every case | Same |
| Design mismatch | `design_mismatch` | Pipeline diff; it lints, and the section now reads `ok` | Can't confirm: `(unverified)` |
| Test-owned fault | existing `<tests>` with a stale mock label | rpcn-test edits its file, re-runs, and the item says it was applied | Still failing: the section reports it |
| Only Test-owned fixes | — | Next: re-run rpcn-test, not rpcn-author | — |

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`, `T` = `rpcn-test-skills` (local, baseline `b250c315c40eaf33858a3d65e9153edefcefab87`; leave the untracked `T/orders_benthos_test.yaml` alone).

- `R/skills/rpcn-test/references/`, the fix rules per check:
  - `fix-check.md` (lint);
  - `samples.md` §2 (exit-2 shape fix) and §4;
  - `dry-run.md` §5 (today: "propose a fix only when the cause is clear");
  - `unit-tests.md` §2 ("never edit" an existing file) and §6;
  - `design-check.md` §4 (lint only).
  Make one rule hold in all five: a cause line, a diff, a check against the failed check, `(unverified)` otherwise. Put the shared rule in `fix-check.md` and point to it; don't repeat it.
- `report-writing.md` (Proposed changes, Test-applied items), `status-block.md` (`artifacts` lists a Test-owned file it edited).
- `R/skills/rpcn-test/SKILL.md` (4,799 bytes): Next gains "only rpcn-test's own files fixed: re-run rpcn-test". Keep any edit tiny.
- `R/tools/shared/formats/test-report-format.md` §7: the cause line, `(unverified)`, and the Test-applied item (title ends `(applied by rpcn-test)`, with the diff shown). Then run `tools/sync_shared.py`, and keep the example's sha256 values valid.
- `R/skills/rpcn-author/references/apply-report.md` §3 already skips Test-owned targets. Check that it skips `(applied by rpcn-test)` items too, and say so if needed.
- `T/run_scenarios.py`, a new `[[fix]]` check `{report, checks = [lint|samples|dry_run|unit|design], contains?, all_verified?}`:
  - copy the run's workdir, and apply each item's diff not titled `(unverified)` or `(applied …)`. Match hunks on content, not line numbers, as `apply-report.md` §4 does, using a small pure-Python applier. A hunk that doesn't apply fails the check.
  - Re-run each named check on the copy on every binary, using the scenario's `[[lint]]` and `[[unit]]` parameters. `samples` runs `blobl` per `.blobl` with the samples file. `dry_run` runs `run --bounded` with the report's **Input messages** block. `design` checks `contains` on the patched file.
  - Each item needs a non-empty line before its diff (the cause). `all_verified = true` fails on any `(unverified)` item.
  - Add tests in `T/tests/test_run_scenarios.py`.
- `T/scenarios/`: add `[[fix]]` to `lint_broken`, `samples_bug`, `dry_run_error`, `unit_bug` and `design_mismatch` (with `contains = ["orders.dlq"]`). Add one Test-owned scenario: `rpcn-test__fix_own_tests`, an existing `<tests>` whose mock key is a stale label, so the target calls `http`. Its `[[unit]] ok = true` runs after the run.
- `R/evals/README.md`: the scenario count and cost.

## Tasks & Acceptance

**Execution:**
- [x] `R/tools/shared/formats/test-report-format.md` §7, then `sync_shared.py`.
- [x] `R/skills/rpcn-test/` references and `SKILL.md` Next. Check `apply-report.md`.
- [x] `T/run_scenarios.py` `[[fix]]`, plus tests.
- [x] `T/scenarios/`: the five `[[fix]]` additions and the Test-owned scenario. `R/evals/README.md`.

**Acceptance Criteria:**
- Given the repo, when the validator, `sync_shared --check`, all `tools/` suites, the `rpcn_check` tests on both binaries and T's tests run, then all pass, and the validator shows no warning for either skill.
- Given both binaries, when every non-compare scenario runs (`--jobs 4 --runs 1 --no-judge`), then all pass, and each `[[fix]]` applies and re-runs its checks.
- Given the reviewed, committed tree, when `run_evals.py` runs (about $43), then it passes and a `dirty: false` record is committed.

## Implementation Notes

- Format §7: each item is a title line, a `Cause:` line and a `diff`; `(unverified)` and `(applied by rpcn-test)` title endings. §5 notes an existing `<tests>` is edited only for a fault in the file. `samples-format.md` now allows changing a sample only when the request or a ready note states it differently (quoted in the item).
- The shared rule lives in `fix-check.md`; `samples.md`, `dry-run.md`, `unit-tests.md`, `design-check.md` point to it. SKILL.md Step 4 now says "Check each fix, of any check, as fix-check.md says" (the temp path moved into `fix-check.md`), which freed room for the new Next line (4,784 characters).
- New binary fact (AD-15): a mock keyed by a label the target no longer has stops the target from starting with `mock for label '<label>' could not be applied as the label was not found`. Proven by `test_test_stale_mock_label` on 4.100.0 and 4.115.0; the unit-tests row in `SOURCES.md` is extended.
- `apply-report.md` §3 now skips `(applied by rpcn-test)` items explicitly.
- `[[fix]]` in T: content-matched pure-Python applier (`parse_diff`, `apply_hunks`), the copy excludes `.git` and `.claude`; `dry_run` fills unset variables with `<VAR>=dry-run` as `dry-run.md` does. All five failing scenarios use `all_verified = true`.
- **Matrix audit (2026-11-13):** the row "Only Test-owned fixes → Next: re-run rpcn-test" had no check. T gained `reply_lacks`, and `fix_own_tests` sets it.
- **After the review fixes:** the validator shows no warnings (`rpcn-test` 4,784 characters). `sync_shared --check`, the `tools/` and skill suites (146), `rpcn_check` on both binaries (186) and T's tests (245) pass. Smoke run with `--jobs 4 --runs 1 --no-judge`, 31 non-compare scenarios: 31/31 on both binaries, and all five `[[fix]]` checks passed (`T/runs/20261113-102111`).
- **Eval record:** `evals/results/2026-11-13-6db288bec933.json` passed with `dirty: false`, at $44.83, on the first full run. Trigger accuracy was 1.0, and all 31 scenarios passed 3/3, linted on 4.100.0 and 4.115.0. Wall time was about 26 minutes; the trigger gate took 328 s.

## Plan Change Log

## Review Triage Log

Quick pass: 0 high, 2 medium, 9 low, 0 false, 0 maybe-false. All 11 route to patch; for finding 11 that is a README note only.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | `parse_fix_items` sets `has_cause` on a wrapped title line, so `[[fix]]` passes an item that has no `Cause:` line | medium | patch | `run_scenarios.py:946-951` sets `has_cause = True` in both branches. Fix: set it only on a line that starts with `Cause:`, and add a wrapped-title test. |
| 2 | `dry-run.md` §5 restates `fix-check.md` step 3, and `unit-tests.md` §6 and `design-check.md` keep "Revise at most twice …", which the plan said not to repeat | low | patch | The diff adds a near-copy of step 3 to `dry-run.md`; two sources of the rule will drift. Fix: point to `fix-check.md` instead of restating it. |
| 3 | A case in an existing `<tests>` that disagrees with intent gets a question but no item, which breaks "every failed check gets an item" | low | patch | `unit-tests.md` §6's last paragraph. Fix: propose the pipeline fix the case implies, as `(unverified)`, plus the question (`fix-check.md` step 3). |
| 4 | `unit-tests.md` §2 says "Never extend" but allows adding a missing mock | medium | patch | The two sentences contradict each other, and the model may refuse the fix the user's decision allows. Fix: "Never add or remove cases, or rewrite it". |
| 5 | The format example's item has a goal as its cause, and names a section rather than the check | low | patch | `test-report-format.md` example. Fix: name the Design check and state why (the DLQ output has no key), then sync. |
| 6 | `apply-report.md` §3 says every item has a `Cause:` line, but older `test-report@2` reports have one why line instead | low | patch | The T fixtures `apply_report`, `stale_report` and `draft_report` use the old shape. Fix: say an older item has one line on why and is applied the same way. |
| 7 | `reply_lacks = ["rpcn-author"]` fails a correct reply such as "nothing for rpcn-author to apply" | low | patch | Substring check, ignoring case. Fix: match the instructions instead: `["with rpcn-author", "use rpcn-author"]`. |
| 8 | `fix_own_tests` doesn't check that the edited test file is in `artifacts` | low | patch | `[status]` checks only `status` and `checks`. Fix: add `artifacts` (report, then the tests file, as `status-block.md` orders them). |
| 9 | The `[[fix]]` samples re-run drops `--env-file` | low | patch | `run_scenarios.py:1157`; the dry_run branch passes it. Fix: pass the `[[lint]]` `env_file` the same way. |
| 10 | `report_input_messages` strips whitespace and drops blank lines, so text input doesn't reach the re-run verbatim | low | patch | `run_scenarios.py:1106`. Fix: keep the lines as they are, adding only the final newline. |
| 11 | Leaving out an `(unverified)` item can make a later verified hunk fail to match | low | patch (README note) | Only reachable without `all_verified`, and every shipped `[[fix]]` sets it. A code fix would add complexity, so the README notes the limit instead. |

## Verification

**Commands:**
- `uv run tools/validate_skills.py` — no warnings
- `uv run tools/sync_shared.py --check` — clean
- `uv run --with pytest pytest -q tools/tests skills` — pass
- `cd T && uv run --with pytest pytest -q tests` — pass
- `T/run_scenarios.py --jobs 4 --runs 1 --no-judge` (non-compare) — all PASS
