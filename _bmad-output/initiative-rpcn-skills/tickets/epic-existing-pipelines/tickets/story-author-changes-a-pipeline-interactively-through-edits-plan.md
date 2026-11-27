---
title: 'Author changes a pipeline interactively through Edits'
type: 'feature'
ticket: '3'
created: '2026-11-25'
status: 'done'
baseline_revision: '3e007ffa6ca3c0cc1b91b7bf92063ac864a791c9'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['_bmad-output/initiative-rpcn-skills/tickets/epic-existing-pipelines/epic-existing-pipelines.md', '_bmad-output/initiative-rpcn-skills/change-requests-vscode-extension/change-an-existing-pipeline.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** after 8.2, an interactive change request writes a `change@1` proposal just as a headless one does. Epic 8 R4 (initiative R21) wants interactive changes made with Edit on the existing files, one Edit per change and never a whole-file Write, so the host can show each one as a diff to approve or refuse.

**Approach:**
- **Interactive change mode** (`skills/rpcn-author/references/change.md`):
  - It builds and verifies each diff exactly as headless does (8.2), then applies it with `apply-report.md` §4's Edit procedure: Read first, one hunk per Edit, matched on content.
  - It never Writes an existing file. A new file (a `--- /dev/null` diff) is Written only when it is absent, as §4 says.
  - It writes no `.change.md` and no status block.
- **A refused Edit:** the file stays as it was. Author doesn't try that change another way, such as a Write or a different Edit. It lints what landed, with up to 3 revisions done as Edits, and the reply names each change left out.
- **Questions:** only what the change leaves open, in one round, through the question tool when it is offered (as today).
- **Headless is unchanged:** it writes the proposal (8.2).
- **A departure from a ready note:** named in the reply. Deviations rows are story 4.
- **Runner:** a new `expect.toml` key, `write_lacks`, a list of paths no Write tool call may target (shaped like `read_lacks`), with tests.
- **`SKILL.md`** (4,802 characters): move informational text into references, keeping every rule, so it stays at or under 4,803 after any change.

## Boundaries & Constraints

**Always:**
- Unrelated lines stay byte-identical, and so do labels, comments and order.
- A plain "write a pipeline" over an existing file keeps today's rule.
- Applying a test report or a proposal works as in 8.2.
- The validator shows no warnings. The description is unchanged unless a trigger needs it.

**Never:**
- A whole-file Write of an existing pipeline, resources, `.blobl` or `.env.example` file in change mode.
- Retrying a refused Edit another way.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Interactive change | "change `<file>` to retry the API 3 times with backoff; go ahead" | the pipeline changes through Edit only (no Write of it); unrelated lines unchanged; lint clean; no `.change.md`; no status block | — |
| Headless change | as 8.2 | a proposal, the pipeline unchanged | — |
| A refused Edit | the host refuses one Edit | that file unchanged; no retry another way; the reply names what was left out; lint run on what landed | checked in the extension only (`claude -p` approves allowed tools) |
| A plain write over an existing file | — | today's rule | — |

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`; `T` = `rpcn-test-skills` (local, baseline `8e7fbfb242bb3ce4b9a09a3cd07d5608c2182586`; leave the untracked `orders_benthos_test.yaml` alone).

- **`R/skills/rpcn-author/references/change.md`:** replace "Interactive runs write the same proposal as headless ones." (line ~20) with the interactive path above. Point at `apply-report.md` §4 for the Edit procedure, and keep the verify-on-copy step (§4 of `change.md`) for both modes.
- **`R/skills/rpcn-author/references/apply-report.md` §4:** it already applies hunks with Edit. Add only what interactive change mode needs: the refused-Edit rule (no retry another way; report the change as not applied; lint what landed).
- **`R/skills/rpcn-author/SKILL.md`:** make room (for example, move informational sentences in Step 6 or Step 7 into `pipeline-files.md` or `apply-report.md`) without changing a rule. It must stay at or under 4,803 characters.
- **`T/run_scenarios.py`:**
  - Add `write_lacks` to the `top` key set and validate it like `read_lacks` (line ~218).
  - Default it to `[]`.
  - Add a check that fails when any Write tool call's `file_path` (relative to the run folder) is in the list, next to the `read_lacks` check.
  - Tests in `T/tests/test_run_scenarios.py`: validation, pass, fail, a relative-path match, and a path outside the run folder.
- **New `T/scenarios/rpcn-author__change_edit`** (interactive, the 8.2 `change_propose` fixture in a new subfolder with a non-default name, `no_cd`):
  - **Prompt:** complete enough that no question is needed ("change `<file>` to retry the fulfilment API 3 times with backoff before giving up; go ahead with your picks").
  - **Checks:**
    - `write_lacks` on the pipeline (and on `.env.example`, unless the change needs a new name);
    - the pipeline `contains` the new retry text and distinctive unchanged lines from the fixture (the header comment and the existing processor's text);
    - `[[lint]] ok = true` on both pins;
    - `<name>.change.md` `exists = false`;
    - `reply_lacks` ` ```json `;
    - stray globs as in 8.2.
- **`T/tests/test_run_scenarios.py`:** a shipped test for the scenario.
- **`R/evals/README.md`:** the counts and cost.

## Tasks & Acceptance

**Execution:**
- [ ] `change.md`, `apply-report.md` §4 and the `SKILL.md` room.
- [ ] T: the `write_lacks` key and its tests, the scenario and its shipped test; README counts.
- [ ] Smoke on both pins:
  - `rpcn-author__change_edit` at `--runs 2`;
  - every `rpcn-author__*` scenario once, the four `change_*` included;
  - the trigger gate, if the description changed.

  Do not commit, and do not run `run_evals.py`.

**Acceptance Criteria:**
- Given the repo, when the validator, `sync_shared --check`, all `tools/` suites and T's tests run, then all pass.
- Given the smoke, when it finishes, then `change_edit` passes 2/2 with no Write of the pipeline, and every `rpcn-author__*` passes.
- Given the reviewed, committed tree, when `run_evals.py` runs (2 runs, the record shared with 8.2), then it passes with `dirty: false`. Then ask before pushing 8.2 and 8.3 together.

## Implementation Notes

- `change.md`: the intro splits the modes after §1-§4 (shared make and verify). §5 is now headless only; a new §6 applies the verified diffs with Edit (Read first, one hunk per Edit, never a Write of an existing file nor a whole-file Edit; a `/dev/null` diff Written only when absent, per `apply-report.md` §4); the reply is §7, with an interactive paragraph. Departures from a ready note and an unlisted component are named in the reply when interactive.
- `apply-report.md` §4 gains the refused-Edit rule (file stays as it was, no retry another way, item not applied, lint what landed); §5 lists a refused Edit as "not applied".
- `SKILL.md` is unchanged (4,802 characters): the mode split lives entirely in `change.md`, so no room was needed. A tried pointer in Step 2 needed room taken from Step 5's `blobl-files.md` mention, which the validator's file-refs rule forbids (every reference must be named in `SKILL.md`), so it was dropped. Description unchanged, so no trigger gate.
- T: `write_lacks` resolves each Write `file_path` against the run folder (absolute inside it, or relative); a path outside it never matches, so the `/tmp` verify copies don't count. Exact path from the run folder, not a tail match (unlike `read_lacks`).
- Scenario prompt deviates from the Code Map's example: http_client's `retries` already defaults to 3 with backoff, so "retry 3 times with backoff" could be judged already done (no diff). The prompt adds "backoff starting at 2s and capped at 30s" so a change is always needed; the checks look for `2s`, `30s` and `retries: 3`.
- Smoke (2026-11-26, sessions on 4.117.0 via `RPCN_BINARY`, checks on both pins): `rpcn-author__change_edit` PASS 2/2 (about $0.30 a run; the agent Wrote the verify copy to `/tmp/rpcn-author-*/` and changed the pipeline with one Edit adding `retries: 3`, `retry_period: 2s`, `max_retry_backoff: 30s`, `backoff_on`); every `rpcn-author__*` scenario (22, the four `change_*` included) PASS 1/1. Trigger gate not run: description unchanged. Not committed; `run_evals.py` not run.
- Review fixes (2026-11-26):
  - `change.md` §6/§7 and `apply-report.md` §4/§5: a hunk refused mid-item leaves the earlier hunks applied (never undone), and the item is reported as partly applied, naming what landed; a lint revision never redoes a refused item, whole or part; `(unverified)` items are applied (lint decides) and named as unverified in the interactive reply; what §4 puts in `open_questions` goes in the reply when interactive.
  - T runner: Edit calls are recorded (`file_path`, `old_string`); `write_lacks` also fails on an Edit of a listed path whose `old_string` holds every non-blank line of the fixture file (a whole-file Edit); `results.json` keeps `write_paths` and `edit_paths`. README: "a Write call that wasn't denied (an errored one still counts)". Tests for whole-file Edit, Edit recording, and the fixture original in `run_checks`.
  - `change_edit`: `contains` checks each untouched block exactly as in the fixture (header plus input with the flow-style `seed_brokers`, the processors block, the output's `url`/`verb`), and the new values tied to their fields (`retry_period: 2s`, `max_retry_backoff: 30s`, `retries: 3`); the shipped test derives the blocks from the fixture.
  - Deviation: `bash_lacks` on the pipeline's file name would always fail, because every run lints `depot/order_relay.yaml` by name. It is `[">", "uv run python", "uv run --with", "uv run sh", "uv run bash"]` instead: shell-write shapes no legitimate `rpcn_check.py` call holds.
  - Smoke after the fixes (sessions on 4.117.0, `RPCN_TEST_BINARIES` absolute, 4.100.0 first): `change_edit` PASS 2/2 ($0.31 a run; 1 Write to `/tmp`, 1 Edit of the pipeline); the other 21 `rpcn-author__*` PASS 1/1. Validator clean; T's tests 433 passed, 4 skipped.

- **Eval record (shared by 8.2 and 8.3):** `evals/results/2026-11-27-1978440ab31a.json` passed with `dirty: false`, at $76.70. Trigger accuracy 1.0; all 71 scenarios 2/2 on both pins. The first attempt ($75.87, 2026-11-26) failed only on `rpcn-test__dry_run_error`: rpcn-test's `SKILL.md` read `design-check.md` with no note. Fixed in `15aebfb`.

- **Pushed:** `64f13c5..491e126`, 8.2 and 8.3 together. CI run 46060786787 was green. T commits stay local.

## Plan Change Log

## Review Triage Log

Quick pass (2026-11-26): 0 high, 4 medium, 7 low, 0 false. Ten patched, one rejected.
- medium, patch: `change_edit` doesn't prove that unrelated lines are byte-identical; it checks only three fragments. Check each untouched block as one multi-line `contains` string.
- medium, patch: a whole-file Edit isn't caught, because only Write calls are recorded. Record Edit calls, and fail `write_lacks` when an Edit on a listed path has an `old_string` holding (nearly) the whole original file.
- medium, patch: a refused hunk in the middle of an item, or a refused file in a multi-file item, leaves the earlier hunks applied, but the text says "stays as it was / not applied". The reply should say the item is partly applied and name what landed.
- medium, patch: the lint revision loop could redo a refused change. Lint revisions must never redo a refused item, in whole or in part.
- low, patch: `2s` and `30s` are loose substrings. Tie them to their field names.
- low, patch: a write through `Bash(uv run *)` isn't caught. Add a `bash_lacks` on the pipeline's name.
- low, patch: how an `(unverified)` item is handled in interactive mode is unclear. It is applied and named as unverified in the reply.
- low, patch: `open_questions` isn't mapped for interactive mode. Say it goes in the reply.
- low, patch: `write_paths` isn't saved in `results.json`. Save it, as `read_paths` is.
- low, patch: the README says "a Write that ran", but an errored Write also counts. Reword.
- low, reject: the symlink and case gaps in `_run_relative`. The runner's base is already resolved, so the case is rare, and fixing it adds path handling.

## Verification

**Commands:**
- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`, `uv run --with pytest pytest -q tools/tests skills` -- pass
- `cd T && uv run --with pytest pytest -q tests` -- pass
- `cd T && RPCN_TEST_BINARIES=<R>/.cache/rpcn/4.100.0/redpanda-connect:<R>/.cache/rpcn/4.117.0/redpanda-connect uv run run_scenarios.py --source local:<R> --runs 2 --no-judge --scenario rpcn-author__change_edit` -- PASS 2/2
