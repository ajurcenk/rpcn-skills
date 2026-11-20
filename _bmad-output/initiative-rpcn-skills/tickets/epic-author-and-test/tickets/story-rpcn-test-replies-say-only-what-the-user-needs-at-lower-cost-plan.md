---
title: 'rpcn-test replies say only what the user needs, at lower cost'
type: 'feature'
ticket: '16'
created: '2026-11-20'
status: 'built'
baseline_revision: 'eb2f84c909d8347a9809962c8da2479e9ec133d5'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 1
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** in the 2.12 benchmark, rpcn-test's replies padded with notes about checks that did not run. It spent 22–28 turns, where the other arms spent 6–10.
- **Where the turns go:** the 2.12 transcripts (`T/runs/20261118-105216`) show about 9 of every 21–25 tool calls are reference Reads, each in its own turn.
- **Reads that aren't needed:** some are for checks that never run: `dry-run.md` and `unit-tests.md` after lint failed, and `design-check.md` with no note. One `ls` of the references folder happens on every run.
- **A useless fix:** in one 2.12 run, a proposed diff had the same removed and added lines.

**Approach:**
- **Shorter reply:** the verdict, each failure's cause and diff, and the report path. `Not run` lines stay in the report only.
- **Fewer turns:**
  - the references a step needs are read together, in one turn;
  - a reference for a check that won't run is not read, because `SKILL.md` gives that section's one-line `Not run` text;
  - no listing of the references folder.
- **No-op diffs:** a diff whose removed and added lines are the same is never a fix. `fix-check.md` rejects it, so the item is revised or marked `(unverified)`.
- **What stays the same:** every check still runs, and the report and status block are unchanged.

**Decision (2026-11-20, user):** rpcn-test keeps today's rule for samples and unit cases whose intent is unclear. It leaves that case out, finishes the run, and asks in the reply (headless: `open_questions`). It never asks before running. This settles the open question in 2.17's Notes for rpcn-test.

**Decision (2026-11-20, user, review loop 1):** turns are compared like for like: against the 2.12 runs of the same scenario that did the same checks (for `dry_run_error`, the run that wrote and ran unit tests, 28 turns). `num_turns` counts tool calls, so fewer calls is what lowers it.

## Boundaries & Constraints

**Always:**
- The report's content and format (`test-report@2`), and the status block (AD-8), are unchanged.
- Every check that runs today still runs.
- `SKILL.md` stays at or under 4,803 characters, and its description at or under 1,024. The validator gives no warnings for either skill.
- Shared files change only in `tools/shared/`, then `sync_shared.py` runs.
- Story 16 is not pushed alone: 18's eval run is its record (decision 2026-11-18). This story only smoke-runs.

**Never:**
- Skip a check to save turns.
- Drop a reference a running check needs.
- Change rpcn-author.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Lint fails | `lint_broken` | `dry-run.md` and `unit-tests.md` are not read; their sections read `Not run: lint failed.`; the reply has no `Not run` line | — |
| No design note | any scenario without one | `design-check.md` is not read; section `Not run: no design note.` | a note that exists is always read through `design-check.md` |
| Everything runs | `unit_bug`, `dry_run_error` | the same checks and report as before, with fewer mean turns than the 2.12 runs that did the same checks | — |
| A no-op diff | removed and added lines equal | rejected by the fix check, then revised or marked `(unverified)` | — |
| Headless | any | the status block is unchanged | — |

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`; `T` = `rpcn-test-skills` (local, baseline `4172e7660d6e0320691f0bb67a8fb5641e36990a`; leave the untracked `orders_benthos_test.yaml` alone).

- **`R/skills/rpcn-test/SKILL.md`** (4,790 characters):
  - Step 3 names `references/samples.md`, `dry-run.md`, `unit-tests.md` and `design-check.md` in turn. Add one compact rule:
    - read a step's references together, in one turn, several Reads at once;
    - skip one when its section can't run: lint failed means `Not run: lint failed.` for Dry run and Unit tests; no design note means `Not run: no design note.`;
    - never list the references folder.
  - The "Reply with …" line (Step 5) says what the reply holds. Make it exclude `Not run` lines and checks that did not run.
  - To stay within the limit, move wording out to a reference such as `report-writing.md` rather than cutting a rule.
- **`R/skills/rpcn-test/references/`:**
  - `dry-run.md` §1, `unit-tests.md` §1 and `design-check.md` §1 hold the full `Not run` rules. Keep them, so every `Not run` variant SKILL.md doesn't name still loads the reference.
  - `fix-check.md` gets the no-op diff rule.
  - `report-writing.md` says what the reply holds.
- **`R/tools/shared/`:** no change expected.
- **`T/scenarios/`:**
  - `rpcn-test__lint_broken` and `rpcn-test__unit_bug` get `reply_lacks = ["Not run"]`.
  - `lint_broken` also gets a check that `dry-run.md` and `unit-tests.md` were not read. If the runner can't check a Read today, add a small `read_lacks` key (the read-path counterpart of `reply_lacks`) and test it.
- **`T/tests/test_run_scenarios.py`:** tests for any new key, and for the shipped scenarios' new checks.
- **Turn baseline:** the 2.12 run's mean turns per scenario, from `T/runs/20261118-105216/results.json`, for `lint_broken`, `dry_run_error` and `unit_bug`.

- **Review loop 1 (2026-11-20).** The first build was reverted. Its diff is kept as `/tmp/claude-1000/-home-aleksejjurcenko-projects-clients-personal-rpcn-skills/e8f28587-8692-460b-9a36-56b1bb18132f/scratchpad/2.16-try1-R.patch` and `/tmp/claude-1000/-home-aleksejjurcenko-projects-clients-personal-rpcn-skills/e8f28587-8692-460b-9a36-56b1bb18132f/scratchpad/2.16-try1-T.patch`, for reference only; re-derive from this plan. Keep what worked and fix the review's findings:
  - **Keep:**
    - the SKILL.md References rule (read together; skip `dry-run.md` and `unit-tests.md` after a lint failure; skip `design-check.md` with no note; never list `references/`);
    - moving Step 4's per-error wording into `lint-errors.md` and the ready check into `report-writing.md`;
    - `report-writing.md`'s "The reply" section, with diffs copied exactly from the report;
    - the no-op diff rule;
    - the temp-dir rule (`/tmp`, on Windows `%TEMP%`; never run a command to learn the temp dir or the session ID);
    - the `read_lacks` runner key and its tests.
  - **The reply also holds the questions and reasons the references send to it.** That covers the unit-tests question when intent is unclear, and `design-check.md` §1's reason for a note that isn't ready. SKILL.md Step 5 says so in a few words; it must not contradict `report-writing.md`.
  - `lint_broken`'s `read_lacks` also lists `references/design-check.md` (the scenario has no note).
  - `reply_lacks` uses `Not run:` (with the colon), not `Not run`.
  - `fix-check.md` step 1 wraps at the file's width and names the temp dir and the session ID plainly.
  - **Turn baseline:** read the 2.12 per-run turns from `T/runs/20261118-105216` and match each run by unit tests written or `Not run`. Record both baselines in Implementation Notes.

## Tasks & Acceptance

**Execution:**
- [x] `R/skills/rpcn-test/SKILL.md` and its references, within both size limits.
- [x] `T/run_scenarios.py` (`read_lacks`, if needed) and its tests; the scenario changes.
- [x] A smoke run: every rpcn-test non-compare scenario once (about $9), plus `lint_broken`, `dry_run_error` and `unit_bug` at `--runs 3` for the turn means (about $4.50). Record the turns against the 2.12 baseline in Implementation Notes.

**Acceptance Criteria:**
- Given the repo, when the validator, `sync_shared --check`, all `tools/` suites, `rpcn_check` on both binaries and T's tests run, then all pass, and the validator shows no warnings for either skill.
- Given the smoke run, when it finishes, then every rpcn-test scenario passes, and `lint_broken`, `dry_run_error` and `unit_bug` each have a lower mean turn count than the 2.12 runs of that scenario that did the same checks (by unit tests written or `Not run`).

## Implementation Notes

- **First build (reverted 2026-11-20 at review loop 1); its notes follow, for history only.**

- **SKILL.md** (4,791 characters, 4,797 bytes; was 4,784 / 4,790): a **References** rule under the opening lines (read what a step needs in one turn, never list `references/`, skip `dry-run.md` and `unit-tests.md` on a lint failure and `design-check.md` with no note, each with its `Not run` line), and Step 5 now says the reply holds the verdict, each failure's cause and diff and the report path, with nothing on skipped checks. To make room, the per-error wording of Step 4 moved to `lint-errors.md`, the report's `hash --check` to `report-writing.md`, and two Next lines merged.
- **References:** `report-writing.md` gains **Check it** and **The reply** (what the reply holds; diffs copied exactly from the report; no `Not run` line or note on a skipped check). `fix-check.md` rejects a diff whose `-` and `+` lines are the same. `dry-run.md` and `fix-check.md` say `<system temp dir>` is `/tmp` (Windows `%TEMP%`) and never to run a command to learn it or the session ID (see "Implementer, outside the Code Map" below).
- **T:** a new `read_lacks` key (Read calls that ran, denied ones left out, matched on the path or its `/<path>` tail), with `read_paths` in each run's results. `lint_broken` gets `reply_lacks = ["Not run"]` and `read_lacks` for `references/dry-run.md` and `references/unit-tests.md`; `unit_bug` gets `reply_lacks = ["Not run"]`. There are tests for the key and the scenarios (300 pass). `JobsTests::test_ctrl_c_cancels_queue_kills_sessions_saves_and_exits_130` is flaky: it also fails on the baseline, about 2 runs in 3.
- **What `num_turns` counts:** it is about the number of tool calls plus 2, not API round trips. Reads in one response still count one each, so the parallel-Read rule makes runs faster and cheaper, but it does not lower turns. Turns go down only when there are fewer calls: no `references/` listing, no dry-run and unit-test references after a lint failure, no design-check reference with no note, and no temp-dir probing.
- **Smoke run** (runs `20261120-151022`, the three scenarios at `--runs 3`, and `20261120-151313`, the other 16 non-compare scenarios once, all on the final skill; both binaries): every scenario passes. The three turn scenarios were run 3 times instead of also once, which saved about $4.50.

  | scenario | 2.12 mean turns (runs) | now (runs) | 2.12 cost | now cost |
  |---|---|---|---|---|
  | lint_broken | 23.7 (25, 22, 24) | **19.0** (18, 21, 18) | $0.49 | $0.39 |
  | dry_run_error | 25.7 (23, 26, 28) | **26.3** (26, 27, 26) | $0.53 | $0.51 |
  | unit_bug | 26.7 (27, 27, 26) | **25.7** (26, 26, 25) | $0.50 | $0.48 |

  Two earlier runs, with the skill as it was before the last edits, gave dry_run_error 26.3 and then 25.0. **dry_run_error misses the turn criterion.** In 2.12, 2 of its 3 runs wrote no unit tests (`Not run: intent unclear.`), which is about 4 fewer calls each. Now all 3 runs write and run them. The one 2.12 run that did the same work took 28 turns, against 26 to 27 now. Every remaining call is one a running check needs, except one `ls` of the pipeline's folder per run (it finds `<res>`, `<tests>` and `<samples>`), which this story does not forbid.
- No reply in the final runs has a `Not run` line or a note on a skipped check. One run before the reply rule was tightened copied a no-op diff into the reply while the report had the right one. The reply rule now says to copy each diff exactly from the report.
- **Implementer, outside the Code Map:** 2026-11-20: Added the temp-dir rule to `dry-run.md` and `fix-check.md` (never probe for `<system temp dir>` or the session ID). The first smoke run spent 1 or 2 Bash calls per run on `echo`/`printenv` probes. This is within "Fewer turns" and runs no fewer checks.

- **Second build (review loop 1, 2026-11-20).** It re-applies the first build's diff and fixes the review's findings:
  - **SKILL.md** (4,802 characters): Step 5's reply now also holds "the references' questions and reasons", and says "no skipped checks". To make room, Step 4 reads "Lint errors: explain each as …" and "Check every fix as …" (same rules, fewer words).
  - **`report-writing.md` "The reply":** it holds each question or reason the references send to the reply, such as the unclear-intent question on a sample or unit case, or why a design note is not ready (`design-check.md` §1). Headless puts these in `open_questions`. The rest of the checks that did not run stay out of the reply (no `Not run:` line). This now matches SKILL.md, `unit-tests.md` §1 and `design-check.md` §1.
  - **`fix-check.md` step 1** is wrapped. `<system temp dir>` is `/tmp` (on Windows, `%TEMP%`). It says never to run a command to learn the temp dir or the session ID.
  - **T:** `reply_lacks = ["Not run:"]` on `lint_broken` and `unit_bug`. `lint_broken`'s `read_lacks` also lists `references/design-check.md`. The README and tests are updated to match (300 pass).
- **Turn baseline (2.12, `T/runs/20261118-105216`), matched per run by the report's Unit tests section:**
  - lint_broken: 25, 22, 24 (all `Not run: lint failed.`), mean **23.7**.
  - dry_run_error: unit tests written in 1 run (**28**); `Not run: intent unclear.` in 2 runs (23, 26; mean **24.5**).
  - unit_bug: 27, 27, 26 (all written), mean **26.7**.
- **Smoke run** (both binaries, final skill): `20261120-152656` has the three turn scenarios at `--runs 3`. `20261120-152940` has the other 16 non-compare scenarios once. All pass, including every `read_lacks` and `reply_lacks` check.

  | scenario | like-for-like 2.12 | now (runs) | 2.12 cost | now cost |
  |---|---|---|---|---|
  | lint_broken | 23.7 | **18.0** (18, 18, 18) | $0.49 | $0.37 |
  | dry_run_error, tests written | 28 | **26.5** (27, 26) | $0.55 | $0.49 |
  | dry_run_error, `Not run: intent unclear.` | 24.5 | **22** (22) | $0.51 | $0.46 |
  | unit_bug | 26.7 | **25.0** (25, 25, 25) | $0.50 | $0.48 |

  Every scenario's mean is lower than the 2.12 runs that did the same checks.
- **Review fixes (2026-11-20, after the second build):**
  - **SKILL.md** (4,735 characters): the References rule says Step 3's check references are read together, after lint. Step 5 points to `report-writing.md` for the reply and no longer has its own list.
  - **`fix-check.md` step 2:** a diff is a no-op when, in each hunk, the `-` lines equal its `+` lines in the same order, or when the patched file equals the original. A diff that only moves lines is not a no-op.
  - **`report-writing.md`:** the reply copies the report's diff exactly. A no-op diff in the report goes back to `fix-check.md` (revise it or mark it `(unverified)`).
  - **T:** a new `bash_lacks` key (strings no Bash call that ran may hold, case-sensitive; denied calls left out), with README and tests (305 pass). `lint_broken` and `dry_run_pass` set `bash_lacks = ["rpcn-test/references"]`. That string matches `ls …/rpcn-test/references` with or without a trailing `/`, but not a script call. `unit_bug` and `dry_run_error` set `read_lacks = ["references/design-check.md"]` (they have no note), and the test comment is corrected.
- **Smoke run after the review fixes** (both binaries): `20261120-153819` has the three turn scenarios at `--runs 3`. `20261120-154109` has the other 16 non-compare scenarios once. All pass.

  | scenario | like-for-like 2.12 | now (runs) | 2.12 cost | now cost |
  |---|---|---|---|---|
  | lint_broken | 23.7 | **18.0** (18, 18, 18) | $0.49 | $0.37 |
  | dry_run_error, tests written | 28 | **27.5** (28, 27) | $0.55 | $0.53 |
  | dry_run_error, `Not run: intent unclear.` | 24.5 | **22** (22) | $0.51 | $0.44 |
  | unit_bug | 26.7 | **25.7** (26, 25, 26) | $0.50 | $0.49 |

  Every mean is lower than its like-for-like baseline, but the dry_run_error margin with tests written is only 0.5, and one of its runs equals the baseline's 28. `samples_bug` (which has no `bash_lacks`) still ran one `ls …/rpcn-test/references/` in this run.
- **After the second-pass fixes (2026-11-20):** the validator, `sync_shared --check`, R's suites (146), `rpcn_check` on 4.100.0 and 4.115.0 (187) and T's tests (305) pass, and `SKILL.md` is 4,735 characters. Not pushed: under the 2026-11-18 decision, 18's eval run is the record for 16 and 17. Left open: `samples_bug` still listed `references/` once in the smoke run (it has no `bash_lacks`); see `deferred-work.md`.
- **Decision (2026-11-20, user):** in 2.18's eval record (16's record), `unit_bug` is 26.7 turns against 26.7 in 2.12, so it is not lower. The user accepted it as unchanged (its cost fell, $0.50 to $0.40); `lint_broken` (18.7 against 23.7) and `dry_run_error` (26.7 against 28) are lower.

## Plan Change Log

## Review Triage Log

Quick pass: 0 high, 2 medium, 4 low, 0 false, 0 maybe-false. One intent_gap, four patches and one fix to these notes.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | `dry_run_error` mean turns are 26.3, against 25.7 in 2.12, so the frozen matrix row and the AC are unmet | medium | intent_gap | The baseline isn't like-for-like: 2 of the 3 2.12 runs skipped the unit tests. `num_turns` also counts tool calls, not round trips, so the plan's "read together" rule can't lower it. Asked the user. |
| 2 | The "No design note" matrix row has no scenario check | low | patch | `lint_broken` has no note, but its `read_lacks` lacks `references/design-check.md`. Fix: add it. |
| 3 | SKILL.md Step 5 and report-writing's "The reply" forbid the reason `design-check.md` §1 sends to the reply for a note that isn't ready, and the summary leaves out the questions the references send | medium | patch | The rules contradict each other, so the not-ready-note reason or the unclear-intent question may be dropped. Fix: the reply also holds the questions and reasons the references send there. |
| 4 | `reply_lacks = ["Not run"]` matches ordinary wording such as "do not run it" | low | patch | Case-insensitive substring match. Fix: use `Not run:`. |
| 5 | The Implementation Notes point to an empty Plan Change Log | low | fixed | My move of the note; the pointer now names "Implementer, outside the Code Map". |
| 6 | `fix-check.md` step 1 has an overlong line, and an unclear "learn either" | low | patch | Fix: wrap it, and name the temp dir and the session ID, as `dry-run.md` does. |

**Review loop 1, second pass (2026-11-20):** 0 high, 2 medium, 5 low, 0 false, 0 maybe-false. Every first-pass patch row (2–4, 6) is confirmed fixed in the rebuild. Of the new findings, six route to patch and one is rejected.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 7 | `dry_run_pass` listed `references/` in the smoke run, and no check catches it | medium | patch | Seen in `bash_commands` in `T/runs/20261120-152940`. `read_lacks` sees only Read calls. Fix: a `bash_lacks` key (the counterpart of `reply_lacks` and `read_lacks`), set on `lint_broken` and `dry_run_pass`. |
| 8 | The no-op diff rule would reject a fix that only moves lines (reordering processors) | medium | patch | "removed and added lines are the same" also matches a move. Fix: no-op means each hunk's `-` lines equal its `+` lines in the same order, or the patched file equals the original. |
| 9 | "The reply" says to copy a no-op diff again from the report, which can't work when the report's own item is the no-op | low | patch | Fix: the reply copies the report's diff exactly; a no-op in the report goes back to `fix-check.md` (revise it or mark it `(unverified)`). |
| 10 | "Read a step's references together" comes before Step 3 knows the lint result | low | patch | Fix: read Step 3's check references together after lint. |
| 11 | SKILL.md Step 5 lists the reply's contents differently from `report-writing.md` | low | patch | Fix: Step 5 points to `report-writing.md` without its own list, which also frees characters. |
| 12 | `unit_bug`'s test comment says every check runs, but it has no design note and no `.blobl` | low | patch | Fix: `read_lacks` for `references/design-check.md` on `unit_bug` and `dry_run_error`, and correct the comment. |
| 13 | `read_lacks` sees only the Read tool | low | reject | SKILL.md forbids `cat`, and the README says this accurately. |

## Verification

**Commands:**
- `uv run tools/validate_skills.py` — no warnings
- `uv run tools/sync_shared.py --check` — clean
- `uv run --with pytest pytest -q tools/tests skills` — pass
- `cd T && uv run --with pytest pytest -q tests` — pass
- `cd T && RPCN_TEST_BINARIES=<abs 4.100.0>:<abs 4.115.0> uv run run_scenarios.py --jobs 4 --runs 1 --no-judge --scenario 'rpcn-test__*'` (all but compare), then `--runs 3` on the three turn scenarios
