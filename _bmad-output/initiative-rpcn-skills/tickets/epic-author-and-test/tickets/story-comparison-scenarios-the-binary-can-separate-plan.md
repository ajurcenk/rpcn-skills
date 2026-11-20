---
title: 'Comparison scenarios the binary can separate'
type: 'feature'
ticket: '15'
created: '2026-11-18'
status: 'built'
baseline_revision: '6689c278bf1b6e9b3eb3f22a9e58424a2401992f'
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

**Problem:** in 2.12, and again in 2.14's rejudge, every arm got full marks on all three comparisons. So the judge's style picked every winner, and the score measured nothing. The scenarios only check what any arm gets right just by running `rpk connect lint` once.

**Approach:**
- Add arm-neutral scoring points that need the pipeline to be run, or its behaviour reasoned about, not just linted. They go on the existing comparisons, so there are no new arms or judges.
- **Missing required field (`compare_write`):** a message without `email` must fail processing, so it would go to the DLQ the request names. It must not pass through with a made-up value. This is the point story 17 makes `ours` meet.
- Every new point is proved on 4.100.0 and 4.115.0, and has a runner test.

**Decisions (2026-11-18, user):**
- **Point kinds:** behavioural only.
  - the missing-field point on `compare_write`;
  - one runtime-only cause added to `compare_diagnose`: a bug that shows only when the pipeline runs, such as a message the mapping deletes by mistake.

  No version point and no hidden unit cases.
- **Missing-email point (2026-11-20, review loop 1):** the event without `email` scores when it fails at runtime, or when it comes out with no made-up email (no `"null"`, no default value). A pipeline that catches the error itself and routes the event to the DLQ meets the request, so it must also score.
- **No separation:** if the smoke run shows no score difference, revise the scenarios at most twice (about $4 per smoke run), then record the result as it is.

## Boundaries & Constraints

**Always:**
- The same prompt, fixtures and `allowed_tools` for every arm.
- Scoring stays arm-neutral, run by the runner on both binaries.
- A request states everything a point checks, so no point tests a requirement the prompt never gave.
- Old `results.json` files stay readable.
- `claude plugin eval` keeps `--no-publish`.

**Never:**
- Change our skills in this story.
- Tune a point to what `ours` does.
- Change `pick_winner`'s order (score, then judge rank, then cost).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Written pipeline errors on a message missing `email` | bounded run, one message without `email` | missing-field point scored | — |
| Written pipeline catches that error itself and routes the event | output for that event has no `email`, or keeps it absent | missing-field point scored | — |
| Written pipeline passes that message through with a made-up email | `email` coerced (e.g. `.string()` gives `"null"`, or a default) | no point | — |
| Pipeline fails on every message | — | no point for valid outputs; the missing-field point is not scored either | a pipeline that errors on everything can't earn the error point |
| An old `results.json` without the new points | `--rejudge` | reads as before | — |
| 1-run smoke | the three comparisons | scores differ between at least two arms on at least one comparison | if none differ, recorded as a finding, not forced |

</frozen-after-approval>

## Code Map

`T` = `/home/aleksejjurcenko/projects/clients/personal/rpcn-test-skills` (local, baseline `3629a2ca84d714cb62c19ea793cf47ac5aeabb67`; leave the untracked `orders_benthos_test.yaml` alone).

- **`T/run_scenarios.py` `[[compare.files]]` `run`** (added in 2.12: `validate_compare`, the scoring in `compare_scores`, and the bounded-run helper used by the file points):
  - Today `run = {input = [...], expect = [...]}` matches outputs as a JSON subset, order-independent, with an exact count.
  - Add an `errors` key: input indexes that must give a runtime error (`rpcn_check run` `data.runtime_errors[].input`). The `expect` count excludes those messages.
  - A run whose every message errors scores neither point.
- **`T/scenarios/rpcn-author__compare_write/`:** the prompt already says "a message that fails processing goes to the dead-letter topic orders.dlq". Make it state that `email` is required. Add the missing-email message, with `errors = [<i>]`, as its own `[[compare.files]]` entry, so the point counts on its own.
- **`T/scenarios/rpcn-test__compare_diagnose/`** : add the runtime-only bug to the fixture `pipes/orders.yaml`, keeping it lint-clean on both binaries. Add one `[[compare.errors]]` entry with specific matchers only (2.12's review: no loose substrings). Update the shipped-scenario test that checks the fixture and prompt don't match.
- **`R/tools/shared/rpcn_check/`:** `run --bounded` already reports runtime errors with the failing `input` (SOURCES.md row, `test_run_bounded`). No new binary fact is expected. If the build relies on one (for example how `.string()` treats null), add a SOURCES.md row and a real-binary test on both binaries (AD-15).
- **`T/tests/test_run_scenarios.py`:** a test per matrix row.
- **`T/README.md`:** the new `run.errors` key.

- **Review loop 1 (2026-11-20).** The first build was reverted; its diff is kept as `/tmp/claude-1000/-home-aleksejjurcenko-projects-clients-personal-rpcn-skills/e8f28587-8692-460b-9a36-56b1bb18132f/scratchpad/2.15-try1-T.patch` and `/tmp/claude-1000/-home-aleksejjurcenko-projects-clients-personal-rpcn-skills/e8f28587-8692-460b-9a36-56b1bb18132f/scratchpad/2.15-try1-R.patch` (reference only; re-derive from this plan). It found the following, which this build must keep or fix:
  - **The point rule:** `run.errors` fails a message only when it passes through with a made-up value. For each listed input, the point scores when that input gives a runtime error, or when its output has the field absent (no `email` key, or `null`). The key shape is the builder's choice; document it in the README.
  - **`missing_email`'s `expect`:** checks only the good message's `id` and `email`, so a cents bug does not cost this point too.
  - **`compare_diagnose`'s new cause:** the first build's final fixture (`if this.test == true { root = deleted() }` followed by `root.total_cents = …`, so the test order goes on unchanged) and its prompt line (test orders carry `"test": true` and must be dropped) are fine. Its matchers must name the test order. Drop "not actually dropped", "not actually deleted", "never actually deleted" and "after deleted()", and add a negative test so a reply about the `total_string` bug does not match.
  - **`lint_binaries`:** strip each `RPCN_TEST_BINARIES` entry, and make it absolute only when it contains a path separator, so a bare name on PATH still works. The first smoke scored nothing with relative paths. Fix the README line that says relative paths resolve from each run folder.
  - **Error text:** an unexpected runtime error quotes the error matched to that input, not the first one.
  - **SOURCES.md row:** the two Bloblang facts, proved by `RealBinaryCommandsTest.test_run_deleted_root_and_missing_field` on both binaries. The File column names only R files; the T scenarios go in its notes column.
  - **Smoke results** (scores tied in every comparison after two revisions; every arm runs the pipeline and quotes the binary's errors): run a single fresh smoke on the final scenarios and record it. The two allowed revisions are already used.

## Tasks & Acceptance

**Execution:**
- [x] `T/run_scenarios.py`: `run.errors`, plus tests.
- [x] `compare_write` (the missing-field entry) and `compare_diagnose` (the runtime-only cause).
- [x] The README.
- [x] A comparison smoke run (`--scenario '*compare*' --runs 1`, about $4), with per-arm scores recorded in Implementation Notes, revising at most twice when no scores differ.

**Acceptance Criteria:**
- Given T's tests and R's `tools/` suites, when they run, then all pass.
- Given the smoke run, when it finishes, then the per-arm scores are recorded, and at least one comparison's scores differ between arms, or, after at most two revisions, the lack of a difference is recorded.

## Implementation Notes

- **Second build (2026-11-20, after review loop 1).** It starts from the first build's diff and applies every fix the Code Map lists.
  - **Point rule.** `run.errors = [i, ...]` stays, and `run.absent = ["field", ...]` is new (optional, needs `errors`). A listed input scores when it gives a runtime error, or when its output has every `absent` field missing or `null`. Its output is the one that holds the input as a JSON subset. That output is taken out before the rest are matched against `expect`. Without `absent`, only a runtime error counts. A listed input fails the point when its output holds a value for the field (`"null"`, a default, `""`), when it gives no output at all (dropped silently), or when every input errors.
  - `attribute_errors` returns `{index: error}`, so an unexpected error quotes the error matched to that input.
  - `missing_email` uses `expect = [{id = "o1", email = "ann@example.com"}]` and `absent = ["email"]`.
  - The `test_order_kept` matchers all name the test order. "non-object type", "unable to set target path", every "after … deleted()" variant and the three "actually" phrases are gone, and some generic phrasings were added ("test orders pass through", "are kept", "are never dropped"). A negative test checks that a reply about `total_string` that uses the dropped phrases matches only `total_string`. Checked offline against rev 2's saved replies (`runs/20261118-214141`): all four arms still match, with real wording such as "Test orders aren't dropped".
  - `lint_binaries` strips each entry and makes it absolute only when it contains `/`, so a bare name stays a name for PATH. The README line is fixed.
  - The SOURCES.md row's File column is now the R test, and the T scenarios moved to its notes column.
  - **Real-binary check** of `missing_email` with `score_file_entry` on 4.100.0 and 4.115.0:

    | Pipeline | Score |
    |---|---|
    | strict `.lowercase()` | 1 |
    | `catch` that keeps the event (email absent) | 1 |
    | cents bug | 1 |
    | `.string()` (`email="null"`) | 0 |
    | `.or("none@x")` default | 0 |
    | fails every message | 0 |

    The diagnose fixture lints clean on both binaries.
- **Smoke run (second build, the single fresh run; `runs/20261120-142547`, `--runs 1`, both binaries, one path relative to check the `lint_binaries` fix):**

  | Scenario | ours | connect-plugin | skills-repo | bare | Judge winner |
  |---|---|---|---|---|---|
  | compare_write | 4/4 | 4/4 | 4/4 | 3/4 | skills-repo |
  | compare_diagnose | 3/3 | 3/3 | 3/3 | 3/3 | connect-plugin |
  | compare_lint | 4/4 | 4/4 | 4/4 | 4/4 | skills-repo |

  Scores differ on compare_write, but not because of a new point. `bare` lost the existing `orders.lint` point, because it used `kafka_franz`, which is deprecated and fails lint on both binaries. Every arm scored `missing_email` through a runtime error, and every arm named `test_order_kept`. The finding from the first build still holds: the new behavioural points don't separate arms that all run the binary. `ours` was last in the judge's rank on all three comparisons. The arms cost about $3.40, not counting the judge.

- **First build (reverted 2026-11-20 at review loop 1); its notes follow, for history only.**

**`run.errors`** (`T/run_scenarios.py`): `validate_compare` accepts `run.errors`, a non-empty list of distinct in-range indexes into `run.input` that may not list every message. `judge_run` scores one binary: with no `errors`, the same as before. With `errors`, the run may fail only with runtime errors (`exit 1`, `data.exit` 0, every envelope error a runtime error). `attribute_errors` matches each `runtime_errors[].input` to an input message, exact JSON first, then a JSON subset (an earlier processor may have added keys). The indexes must equal `errors`, no error may be left unmatched, the run may not fail on every message, and the remaining outputs must match `expect`.

**Scenarios:**
- `compare_write`: the prompt now says "Every event must have an email: an event without one fails processing." A new `[[compare.files]]` entry `missing_email` (`run` only, 1 point) has input `[o1 valid, o4 no email]`, `expect = [o1]`, `errors = [1]`. Checked on 4.100.0 and 4.115.0: `this.email.lowercase()` scores, `this.email.string().lowercase()` (gives `"null"`) does not, and a mapping that fails every message does not.
- `compare_diagnose`, final (revision 2): the `enrich` mapping has `if this.test == true { root = deleted() }` before `root.total_cents = ...`. The later assignment fails (`non-object type`), so the test order goes on unchanged. The cause is `test_order_kept`. The prompt states that test orders carry `"test": true` and must be dropped, and that real orders have no test field. The fixture lints clean on both binaries.

**Smoke runs** (`--runs 1`, both binaries):

| Run | Scenario | ours | connect-plugin | skills-repo | bare | Judge winner |
|---|---|---|---|---|---|---|
| 1 (`runs/20261118-212257`, all `*compare*`) | compare_write | 4/4* | 4/4* | 4/4* | 4/4* | skills-repo |
| 1 | compare_diagnose (`this.test != false` deletes every real order) | 3/3 | 3/3 | 3/3 | 3/3 | skills-repo |
| 1 | compare_lint | 4/4 | 4/4 | 4/4 | 4/4 | connect-plugin |
| rev 1 (`runs/20261118-213525`) | compare_diagnose (+ `.floor()`: 19.99 gives 1998, 0.29 gives 28) | 4/4 | 4/4 | 4/4 | 4/4 | bare |
| rev 2 (`runs/20261118-214141`) | compare_diagnose (final: `deleted()` overwritten) | 3/3 | 3/3 | 3/3 | 3/3 | bare |

\* Run 1 printed 1/4 for every compare_write arm. `RPCN_TEST_BINARIES` held relative paths, and the checker runs inside each run folder, so lint and run never found the binary. Rescored offline from the saved `pipes/orders.yaml` with absolute paths: every arm got 4/4, `missing_email` included. `lint_binaries` now makes relative paths absolute. Revisions 1 and 2 changed only compare_diagnose, so only it was re-run (about $1.3 and $1.4).

**Finding: no separation after two revisions.** Every arm, `bare` included, runs the pipeline on sample messages with the binary and names every runtime-only cause, quoting the binary's own error text. Each matched cause was checked by hand against the reply, and none was a loose or accidental match. Behavioural points that a run exposes don't separate arms that all run the binary. Separation probably needs points that a single sample run doesn't show, or a weaker model behind the arms. That is for the next story to decide.

**Binary facts** (AD-15): a new SOURCES.md row and `RealBinaryCommandsTest.test_run_deleted_root_and_missing_field` (R). An assignment after `root = deleted()` fails and the message goes on unchanged. `.lowercase()` on a missing field is a runtime error, while `.string()` gives `"null"`. Both hold on 4.100.0 and 4.115.0.

**Known gap:** a pipeline that `catch`es the missing-email error inside `pipeline.processors` and routes it to the DLQ with metadata is a valid design. Its bounded run shows no runtime error, so it scores no `missing_email` point. In the smoke, every arm routed errors in the output, so none was affected.
- **Implementer (2026-11-18):** compare_diagnose's runtime-only cause revised twice (allowed by the no-separation decision): `this.test != false` became `.floor()` (rev 1), which became `root = deleted()` overwritten by a later assignment (rev 2, final). Only one runtime-only cause stays in the fixture.
- **Implementer (2026-11-18):** `lint_binaries` resolves relative `RPCN_TEST_BINARIES` paths (found in smoke run 1). This is outside the Code Map, and it is a one-line fix.
- **Implementer (2026-11-18):** a SOURCES.md row and a real-binary test were added, because the final scenarios rely on two Bloblang facts (the Code Map's "if the build relies on one").
- **After the review fixes (2026-11-20):** T's tests (293; one run hit the known `test_ctrl_c_…` timing flake, and two re-runs passed), R's suites (146), `rpcn_check` on 4.100.0 and 4.115.0 (187) and the validator pass. Nothing under `skills/` changed, so the 2.11 eval record still covers the skills. Separation finding: `bare` lost the lint point in `compare_write` for a deprecated `kafka_franz` (`lint --deprecated`, AD-4); the new points tie for every arm.

## Plan Change Log

## Review Triage Log

Quick pass: 0 high, 3 medium, 5 low, 1 false, 0 maybe-false. One intent_gap, six patches and two rejects.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | `missing_email` scores 0 for a valid design that `catch`es the error in `pipeline.processors` and routes it to the DLQ | medium | intent_gap | The prompt says only that such an event "fails processing" and goes to `orders.dlq`, and a caught error leaves no runtime error in the bounded run. The frozen matrix defines the point as "errors on a message missing email", which conflicts with the Always rules (arm-neutral; no requirement the prompt never gave). Asked the user. |
| 2 | `missing_email` also requires o1's `total_cents`, so a cents bug costs two points | medium | patch | Its `expect` for o1 includes `total_cents` and `total`. Fix: check only o1's id and email. |
| 3 | `test_order_kept` matchers such as "not actually dropped" also match a reply about the `total_string` bug | medium | patch | Case-insensitive substring match. Fix: keep only matchers that name the test order, plus a negative test for the cross-match. |
| 4 | `lint_binaries` turns a bare binary name on PATH into `<cwd>/name`, and calls `abspath` on the unstripped string | low | patch | `rpcn_check.find_binary` uses `shutil.which`. Fix: strip, then make the path absolute only when it contains a path separator. |
| 5 | The README line still says relative paths resolve from each run folder | low | patch | Now they resolve from the runner's folder. Fix the line. |
| 6 | The "extra" branch of `judge_run` quotes the first runtime error, not the unexpected one | low | patch | `next(... for e in runtime)`. Fix: use the error attributed to that index. |
| 7 | The SOURCES.md row's File column names `rpcn-test-skills` scenarios | low | patch | The table's rule is files in this repo. Fix: File is the R test; the scenarios go in its notes column. |
| 8 | Greedy subset matching in `attribute_errors` can reject a valid assignment | low | reject | Unlikely with these scenarios (one missing-field message each), and a fix needs a full matching algorithm. |
| 9 | The diff carries the 2.17 and epic-3 commits | false | reject | Those are separate commits after the baseline (`7bbf116`, `3d430c3`), not 2.15's work. |

**Review loop 1, second pass (2026-11-20):** 0 high, 0 medium, 4 low, 0 false, 0 maybe-false. Every first-pass patch row (2–7) is confirmed fixed in the rebuild. Of the four new findings, three route to patch and one is rejected.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 10 | The README's `missing_email` example breaks an inline TOML table across lines, so it is not valid TOML | low | patch | TOML 1.0 forbids a newline inside `{}` outside an array; `tomllib` rejects it. Fix: one line, or a `[compare.files.run]` table. |
| 11 | `absent` also scores a pipeline that drops `email` and sends the event on to `orders.clean` | low | patch (doc) | The bounded run can't see which output an event took. The user's decision (2026-11-20) scores "comes out with no made-up email", so this is in scope. Fix: state the limit in the README and the `expect.toml` comment. |
| 12 | A caught event that is reshaped (wrapped, or `total` replaced) scores 0 | low | reject (documented) | The held lookup needs the whole input as a JSON subset. No arm reshaped in the smoke run, and a fix needs an identity-key option. It goes in the same README limit note as row 11. |
| 13 | `score_file_entry`'s docstring still says a `run` point needs exit 0 | low | patch | It contradicts `judge_run`. Fix: point the docstring at `judge_run`'s rule. |

## Verification

**Commands:**
- `cd T && uv run --with pytest pytest -q tests` — pass
- `uv run --with pytest pytest -q tools/tests skills` (in R) — pass
- `cd T && RPCN_TEST_BINARIES=… uv run run_scenarios.py --scenario '*compare*' --runs 1` — exit 0; per-arm scores in the table
