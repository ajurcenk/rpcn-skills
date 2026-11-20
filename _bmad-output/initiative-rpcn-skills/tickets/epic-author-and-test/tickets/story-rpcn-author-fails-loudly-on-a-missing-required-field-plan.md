---
title: 'rpcn-author fails loudly on a missing required field'
type: 'feature'
ticket: '17'
created: '2026-11-20'
status: 'done'
baseline_revision: 'b196eae0cd2f7f5fc76421a7f1ddfc5ed74e7413'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['_bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-rpcn-author-fails-loudly-on-a-missing-required-field.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** the story file (in `context:`) holds the approved criteria 1–6, and this plan builds them. In 2.12, rpcn-author wrote `.string()` on an `email` the request only implied was required, so a message without one passed as `"null"`. It also never asks about behaviour gaps before writing.

**Approach:**
- **Required fields:** a field the processing needs is required. A message missing it fails, or comes out with the field absent, and never passes with a made-up value. This rests on the 2.15 SOURCES.md row.
- **One round of questions (interactive):** one message, before any file is written, holding:
  - behaviour gaps the request leaves open: a field the pipeline reads but doesn't need, or where failures go;
  - the two asks the skill already has (an existing file, an unclear component).

  Each question comes with the answer the skill would pick.
- **Headless:** never ask. Use the picks and list them in `open_questions`. The run ends `complete`, except for the existing overwrite rule, which stays `blocked`.
- **Proof:**
  - a new headless scenario where the requirement is only implied, checked by a new bounded-run check;
  - an interactive ambiguous-request scenario that writes no file and ends with one question;
  - a headless ambiguous-request scenario that ends `complete`, with its picks in `open_questions`.

## Boundaries & Constraints

**Always:**
- The story's Boundaries apply: R1, the overwrite rule, R2 and R3 don't change; `SKILL.md` stays at or under 4,803 characters and its description at or under 1,024; headless never asks; at most one round.
- `SKILL.md` makes room by moving wording into a reference.
- Every new scenario follows the epic's 2026-11-05 decision: a pipeline outside the project root and a non-default name.
- Story 17 only smoke-runs. 18's eval run is its record.

**Never:**
- Change rpcn-test.
- Weaken the overwrite rule.
- Ask what the binary, a ready design note or the request already answers.
- Add a new binary fact without a SOURCES.md row.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Implied required field, headless | "lowercase each event's email; failures go to a DLQ" | a bounded-run event without `email` fails, or `email` is absent; never `"null"` | a `.string()` pipeline fails the check (runner test) |
| Ambiguous request, interactive | a pass-through field with no rule; failure target not named | one question message, each with its pick; no pipeline file written | — |
| The same, headless | the same request, "unattended" | `status: complete`; each pick in `open_questions` | not `blocked` |
| An existing pipeline file, interactive | the file is there | the overwrite question goes in the same single message | headless: `blocked`, as today |
| A request that answers everything | stated fields and failure path | no question; writes as today | — |
| `compare_write` | the 2.15 prompt | still meets `missing_email` | regression |

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`; `T` = `rpcn-test-skills` (local, baseline `24fb1031029cd5a9e91a3713d0776e4e0a128b68`; leave the untracked `orders_benthos_test.yaml` alone).

- **`R/skills/rpcn-author/SKILL.md`** (4,792 characters):
  - Step 2 holds the overwrite ask (line 41). Step 4 holds the close-match ask (line 76). The headless rule is at lines 16–17.
  - Add, before Step 5 writes: the one-round rule, pointing at a reference.
  - Make room by moving existing wording into a reference, as 2.16 did.
- **`R/skills/rpcn-author/references/`:**
  - `blobl-files.md` is a shared copy (`shared.txt`: `formats/blobl-files.md`), so never edit it here. Put the required-field guidance in a local reference, either `pipeline-files.md` or a new `questions.md`. The guidance: no `.string()` or `.or()` default on a needed field; a string method errors on null; route failures as the request says. It cites the SOURCES.md row.
  - The one round and the assumption rule go in that new or existing local reference.
  - `status-block.md`: picks go in `open_questions` with status `complete`.
- **`R/SOURCES.md`:** the 2.15 Bloblang row's notes column names the rpcn-author reference that uses it.
- **`T/run_scenarios.py`:**
  - **New pass check `[[run]]`** `{file, input, expect?, errors?, absent?}`. It reuses 2.15's `judge_run` (bounded run on every binary in `RPCN_TEST_BINARIES`, with `run.errors` and `run.absent` meaning the same as in `[[compare.files]]`).
  - **`[[file]]` gains `exists = false`,** which fails if the file was written.
  - **New `reply_contains`** (the counterpart of `reply_lacks`), so the interactive scenario can require a question mark and its picks.
  - Validate each like the existing keys, and add tests for each matrix row, including a `.string()` pipeline that fails `[[run]]`.
- **`T/scenarios/`** (all with `install = ["rpcn-author"]`, `no_cd`, and a pipeline in a subfolder with a non-default name):
  - `rpcn-author__implied_required` (headless): `[[run]]` with an event missing `email`, `errors = [i]` and `absent = ["email"]`; `[[lint]] ok`.
  - `rpcn-author__ask_first` (interactive, no "unattended"): `[[file]] exists = false` for the pipeline; `reply_contains` for `?`.
  - `rpcn-author__assume_headless`: `[status]` `complete`; `open_questions` non-empty, checked by a status key if one exists, else a small extension.
- **`T/README.md`:** the new keys.

## Tasks & Acceptance

**Execution:**
- [x] `R/skills/rpcn-author/` (`SKILL.md` and references) and the SOURCES.md notes column.
- [x] `T/run_scenarios.py`: `[[run]]`, `[[file]] exists`, `reply_contains`, plus tests.
- [x] The three new T scenarios and the README.
- [x] A smoke run: every rpcn-author non-compare scenario once (about $4), plus `rpcn-author__compare_write` once in all four arms (about $1.50). Record the results in Implementation Notes.

**Acceptance Criteria:**
- Given the repo, when the validator, `sync_shared --check`, all `tools/` suites, `rpcn_check` on both binaries and T's tests run, then all pass, and the validator shows no warnings for either skill.
- Given the smoke run, when it finishes, then every rpcn-author scenario passes, including the three new ones, and `ours` meets `missing_email` on `compare_write`.

## Implementation Notes

**R (rpcn-skills):**
- `SKILL.md` (4,802 characters, description unchanged): Step 5 is now "Ask, then write" and opens by pointing at `references/questions.md`. Step 2's overwrite ask and Step 4's close-match ask say they go in Step 5's round. Room came from moving the status block's JSON template out of `SKILL.md` into `references/status-block.md`; no rule was cut.
- New local reference `references/questions.md` (`blobl-files.md` stays an untouched shared copy). It holds the required-field guidance (call the method on the field; never `.string()`, `.or()` or a filling `catch` first; a default only on request; route failures as the request says), the one round of questions (behaviour gaps plus the existing-file and close-match asks, each with a `My pick:` line, then stop and write nothing), and the headless rule (picks go in `open_questions` as `Assumed: …`, run ends `complete`, an existing file still `blocked`). It cites the 2.15 row (`test_run_deleted_root_and_missing_field`) and the processor-error row (`errored()`).
- `references/status-block.md`: now holds the template; picks never block and go in `open_questions`.
- `SOURCES.md`: the Notes column of the 2.15 Bloblang row and the processor-error-handling row both name `skills/rpcn-author/references/questions.md`. No new binary fact.

**T (rpcn-test-skills):**
- `[[run]]` `{file, skill?, input, expect?, errors?, absent?}`: it validates through a new `validate_run_table`, which `[[compare.files]].run` now shares, so compare's error messages are unchanged. `check_run` runs `judge_run` on every binary through `_check_with_env`. `expect` may be left out only with `errors`, and then means no other output.
- `[[file]] exists = false` (only `false`; not with `contains`) fails if anything is at the path.
- `reply_contains`: the counterpart of `reply_lacks`, case-insensitive.
- `status_nonempty = ["open_questions"]` (or `artifacts`): no status key could check "non-empty", so this is the small extension the Code Map allowed.
- How "one question message" is judged: `claude -p` ends the session at the skill's first final reply, so that reply is the only message. `ask_first` requires `?` and `pick` in it (the `My pick:` line), plus no pipeline file.
- Tests: validation and behaviour for each new key, a fake `.string()` run that fails `[[run]]`, and `RunCheckRealBinaryTests`. The real-binary test is skipped unless `RPCN_TEST_BINARIES` is set; with both binaries set it passed, with `.lowercase()` passing and `.string().lowercase()` failing on `email="null"`. There are shipped-scenario tests for the three new scenarios.
- Scenarios: `rpcn-author__implied_required` (`streams/customer_events.yaml`), `rpcn-author__ask_first` and `rpcn-author__assume_headless` (`signups/signup_feed.yaml`, the same request, with only the headless one unattended). All use `no_cd` and an empty subfolder fixture.

**Verification (2026-11-20):** `validate_skills` ok with no warnings for either skill. `sync_shared --check` clean. R `tools/tests skills` 146 passed. `tools/shared` with both binaries 187 passed. T `tests` 324 passed with 2 skipped (both pass with binaries set).

**Smoke run** (`RPCN_TEST_BINARIES` = 4.100.0 and 4.115.0, `--runs 1 --no-judge`):
- All 15 rpcn-author non-compare scenarios PASS 1/1, about $4.17 (`runs/20261120-164416`).
  - `implied_required`: `run` passed with input 1 failing as expected on both binaries.
  - `ask_first`: 2 questions, each with `My pick:`, and no file written.
  - `assume_headless`: `complete` with 3 `open_questions`.
- `compare_write` with all four arms, about $1.20 (`runs/20261120-164723`): ours 4/4 (meets `missing_email`), connect-plugin 4/4, skills-repo 4/4, bare 3/4.

**Review fixes (review loop 1, 2026-11-20):**
- The T test file's 2.17 classes moved above the `__main__` guard, so `uv run tests/test_run_scenarios.py` runs them (327 tests, 2 skipped).
- `questions.md`:
  - **Headless:** with nothing written, an existing pipeline (Step 2 stops there), an existing resources or `.blobl` file, and no fitting listed component all stay `blocked`. Never write a component that doesn't fit.
  - **One round:** the existing resources and `.blobl` file asks are now part of the single round, and every file name is decided before it. With an existing pipeline, an interactive run writes nothing until the answer.
  - **`errored()`:** the bullet now says only what the row proves (an unhandled error is still `errored()` in the output's processors).
  - **Headless examples:** there is now one bracketed-question example for each gap.
- `pipeline-files.md` points its two existing-file asks at the round.
- `status-block.md`: an existing pipeline stops at Step 2 with nothing written, and a missing fitting component blocks.
- `SKILL.md` Step 2 says "headless: stop, `blocked`". Step 5's pointer is shorter: the full rule is in `questions.md`. It is now 4,797 characters.
- Scenarios:
  - `ask_first` gained `reply_lacks = ["```json"]` and `exists = false` for `signups/.env.example` and `signups/signup_feed.resources.yaml`.
  - `assume_headless` gained `reply_contains = ["referrer required", "failure path"]`.
  - New `rpcn-author__ask_existing` covers the "existing pipeline, interactive" row. It has `billing/invoice_feed.yaml` as a fixture, with `unchanged` on it. It requires `?`, `pick`, `exist`, `invoice_feed.yaml` and `po_number` in the reply and no ```` ```json ```` fence. It also checks that `exists = false` holds for `.env.example` and the resources file. A `.blobl` under a label the skill picks, or a pipeline under a new name, can't be listed. It has its own shipped-scenario test.
- Second smoke run, with absolute `RPCN_TEST_BINARIES` for 4.100.0 and 4.115.0:
  - All 16 rpcn-author non-compare scenarios PASS 1/1 (`runs/20261120-165600`): apply_report, ask_existing, ask_first, assume_headless, design_deviation, design_draft, design_note, design_not_ready, draft_report, existing_file, implied_required, npx_miss, npx_trigger, stale_report, write_blobl and write_resources_yml.
  - `compare_write` PASS (`runs/20261120-165914`): every arm scored 4/4 (ours, connect-plugin, skills-repo, bare), so ours still meets `missing_email`.

**Seen, not fixed (for 18's eval run):**
- In this one run, the interactive pick for the failure path was a DLQ `signups.dlq`, while the headless pick was to log and drop.
- The headless `open_questions` also listed "email is required", which the guidance answers and so is not a real question.
- **After the review fixes (2026-11-20):** the validator, `sync_shared --check`, R's suites (146), `rpcn_check` on 4.100.0 and 4.115.0 (187) and T's tests (327, both binaries set) pass. `SKILL.md` is 4,797 characters. Not pushed: 18's eval run is the record for 16 and 17.
- **Pushed:** `dd33885..046fe05`, with stories 16–18 together. CI run 44834989733 was green. The eval record is `evals/results/2026-11-20-83e2eea0bd76.json`.

## Plan Change Log

## Review Triage Log

Quick pass: 0 high, 4 medium, 4 low, 0 false, 0 maybe-false. All eight route to patch.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | The new test classes sit after `if __name__ == "__main__"`, so a direct run of the file skips them | medium | patch | `run_evals` runs `uv run tests/test_run_scenarios.py` directly, so the record would skip them. Fix: move the block above the guard. |
| 2 | `questions.md` Headless says only an existing file blocks, while `status-block.md` blocks when no component fits | medium | patch | The two rules contradict, and the skill could write a component that doesn't fit (R1). Fix: with no fitting component, headless stays `blocked` as before, and `questions.md` says so. |
| 3 | The resources and `.blobl` existing-file asks in `pipeline-files.md` run after the round, so a second round is possible | medium | patch | `pipeline-files.md` lines 25–26 and 57–58. Fix: those asks join the same round (`questions.md` lists them), so it stays one round. |
| 4 | A headless existing pipeline doesn't say whether side files still get written before `blocked` | medium | patch | The old Step 2 stopped at once. Fix: an existing pipeline stops at Step 2 as before (headless: `blocked`, nothing written); interactively it asks in the round and writes nothing until answered. |
| 5 | `ask_first`'s checks are weak | low | patch | `?` and `pick` match anything. Fix: add `reply_lacks` for a status-block fence, and `[[file]] exists = false` for the `.env.example` and resources file it could write. |
| 6 | `assume_headless` can pass on one irrelevant assumption | low | patch | `status_nonempty` takes any entry. Fix: `reply_contains` names both open choices (the pass-through field and the failure target). |
| 7 | The matrix row "An existing pipeline file, interactive" has no scenario | low | patch | `existing_file` is headless only. Fix: a new interactive scenario with an existing pipeline and an ambiguous request: one message holding both the overwrite question and the gap questions; the pipeline unchanged. |
| 8 | "the output can route on it" goes beyond the `errored()` row | low | patch | The row proves `errored()` in the output's processors only. Fix: keep the wording to that. |

## Verification

**Commands:**
- `uv run tools/validate_skills.py` — no warnings
- `uv run tools/sync_shared.py --check` — clean
- `uv run --with pytest pytest -q tools/tests skills` — pass
- `cd T && uv run --with pytest pytest -q tests` — pass
- `cd T && RPCN_TEST_BINARIES=<abs 4.100.0>:<abs 4.115.0> uv run run_scenarios.py --jobs 4 --runs 1 --no-judge --scenario 'rpcn-author__*'` (non-compare), then `--scenario rpcn-author__compare_write --runs 1`
