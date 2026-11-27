---
title: 'Author proposes a change as a change@1 file when headless'
type: 'feature'
ticket: '2'
created: '2026-11-25'
status: 'done'
baseline_revision: '64f13c59866d9dd494d4dd1f065b8d6cc91785c7'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['_bmad-output/initiative-rpcn-skills/tickets/epic-existing-pipelines/epic-existing-pipelines.md', '_bmad-output/initiative-rpcn-skills/change-requests-vscode-extension/change-an-existing-pipeline.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** rpcn-author never changes an existing pipeline on request. Step 2 blocks, or asks for another name, and only Step 7 edits a pipeline, from a test report. Epic 8 R3 (initiative R21) asks for a headless, reviewable change: a proposal file with verified diffs, which Author's apply step then applies.

**Approach:**
- **A new hand-off format, `change@1`:** `tools/shared/formats/change-format.md`, synced into rpcn-author.
  - **The shared hand-off header:** `artifact: change`, `format: change@1`, `pipeline`, `status` (`ready` or `draft`), `produced_by: rpcn-author@…`, `rpcn_version`, `updated`, and `inputs` hashing every file a diff applies to.
  - **The body:** `## Request`, the change asked for, in the user's words; `## Proposed changes`, in the same item shape as the test report (a title, a `Cause:` line naming the request, and a fenced unified diff per file, relative to the proposal's folder); and `## Open decisions`.
  - **Readiness:** `status: ready` with fresh `inputs`.
- **`rpcn_check`:** `KNOWN_FORMATS` gains `change: (1,)`, so `hash --check` reads a proposal and reports it stale when a target file has changed. Tests cover ready, stale and bad-header proposals on both pins.
- **Change mode** (new `skills/rpcn-author/references/change.md`, with a pointer from Step 2):
  - **When it applies:** an explicit request to change a named existing pipeline ("change `<file>` to …", "update `<file>` so …").
  - **Reads:** the pipeline, its resources, `.blobl` files and `.env.example`, and its design note if there is one.
  - **Checks:** each new component and field with `list` and `fields` (Steps 3 and 4).
  - **Diffs:** only what the request needs. Labels, comments, order and unrelated parts stay as they are. An inline mapping isn't moved into a `.blobl` unless asked, and `.env.example` only gains names.
  - **Verifying:** every diff is checked on a copy in the system temp folder, as rpcn-test's `fix-check.md` does. It is linted, with at most 2 revisions, and a diff that still fails is marked `(unverified)`.
  - **Writes:** `<dir>/<name>.change.md` and nothing else. The pipeline and its files stay byte-identical.
- **In this story, interactive runs write the same proposal.** Story 3 switches interactive runs to Edits.
- **Applying:**
  - Step 7 and `apply-report.md` also apply a ready `<name>.change.md` ("apply `<file>.change.md`"), the same way they apply a test report.
  - Its readiness comes from `change-format.md`.
  - The proposal itself is never edited.
- **Description:** gains one change phrase, so the scenarios trigger rpcn-author. The full sibling fit is story 5.

## Boundaries & Constraints

**Always:**
- A plain "write a pipeline …" over an existing file keeps today's rule: blocked headless, asking interactively.
- Applying a test report works as today.
- `${ENV}` for secrets and addresses, and only components and fields the binary reports.
- `design@1` and `test-report@2` are unchanged. The new format goes through `tools/shared/formats` and `sync_shared`.
- `SKILL.md` stays at or under 4,803 characters, and the description at or under 1,024. The validator shows no warnings.

**Never:**
- Editing the pipeline, or any of its files, in change mode. Only Step 7's apply does that.
- Writing a verify copy beside the pipeline.
- The design note's Deviations: a departure from a ready note is story 4. This story writes no Deviations row, and names a departure in the proposal's Open decisions.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Headless change | "change `<file>` to drop test orders before posting", unattended | a ready `<name>.change.md` with a verified diff, the pipeline unchanged, status `complete` with the proposal in `artifacts` | — |
| Apply a ready proposal | "apply `<name>.change.md`" | the pipeline carries the diff and lints clean; the proposal unchanged | — |
| Stale proposal | the pipeline changed after the proposal | `hash --check` reports `changed`; apply stops (`blocked` headless) | as for a stale report |
| A plain write over an existing file | "write a pipeline in `<file>` …" | today's rule (blocked or ask) | — |
| A change needing an unlisted component | — | no such diff; an Open decision names it; the proposal is `draft` | — |

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`; `T` = `rpcn-test-skills` (local, baseline `64ef6f4601562eeb0168e4ef111ef7dd8602f80a`; leave the untracked `orders_benthos_test.yaml` alone).

- **New `R/tools/shared/formats/change-format.md`:** modelled on `test-report-format.md` (Header, Status, Sections, Readiness list, an Example). Proposed-changes items follow `test-report-format.md` §7's item shape: title, `Cause:`, `diff` block. If the rpcn_check tests pin the example's sha256, as `test-report-format.md`'s comment says they do for the design example, add the same for this example.
- **`R/tools/shared/rpcn_check/rpcn_check.py`, `KNOWN_FORMATS` (line ~375):** add `"change": (1,)`. No verdict logic: `report_verdict` is test-report only.
- **`R/tools/shared/rpcn_check/tests/test_rpcn_check.py`:** tests for `hash --check` on a change file: ready, stale input, unknown major, missing header field. Use the existing hand-off tests as the pattern.
- **`R/skills/rpcn-author/shared.txt`:** add `formats/change-format.md references/change-format.md`, then `uv run tools/sync_shared.py`.
- **New `R/skills/rpcn-author/references/change.md`:** the Approach's change mode. It reuses `rpcn-test`'s `fix-check.md` method for the temp-folder copy, its own `pipeline-files.md` rules, and Steps 3–6.
- **`R/skills/rpcn-author/SKILL.md`** (4,615 characters, about 188 to spare):
  - Step 2: before "If `<dir>/<pipeline>` exists, never write over it", add a pointer: "a request to change it: `references/change.md`".
  - The start of Step 2 sends a named `<name>.change.md` to Step 7.
  - Step 7's title and lead-in cover a change proposal.
  - One description phrase, for example "change my pipeline to …".
- **`R/skills/rpcn-author/references/apply-report.md`:** §1–§3 also take a `change@1` proposal: its readiness from `change-format.md`, `<pipeline>` its `inputs[0]`, and the same target rules. The rest is unchanged.
- **`R/skills/rpcn-author/references/status-block.md`:** a proposal goes in `artifacts`.
- **T, new scenarios** (headless, a subfolder with a non-default name, `no_cd`):
  - `rpcn-author__change_propose`: the fixture is a pipeline that lints clean on both pins (plus `.env.example`). Expect:
    - `[[report]]` on `<name>.change.md` with `ready = true`;
    - `contains` `artifact: change`, `## Proposed changes`, ` ```diff`, `Cause:`;
    - the pipeline and `.env.example` unchanged;
    - status `complete` with the proposal in `artifacts`;
    - no stray file.
  - `rpcn-author__change_apply`: the fixture is the pipeline plus a ready `<name>.change.md`, whose `inputs` hashes match the fixture (compute them with `rpcn_check hash`). Expect:
    - the pipeline carries the diff's new line(s) and lints clean on both pins (`[[lint]]`);
    - the proposal unchanged;
    - status `complete`.
- **`T/tests/test_run_scenarios.py`:** shipped tests for both.
- **`R/evals/README.md`:** the counts and cost.

## Tasks & Acceptance

**Execution:**
- [x] The `change@1` format, the `rpcn_check` entry and its tests on both pins, and `sync_shared`.
- [x] `change.md`, the `SKILL.md` pointers and phrase, `apply-report.md` and `status-block.md`.
- [x] T: the two scenarios and their tests; README counts.
- [x] Smoke on both pins:
  - both scenarios at `--runs 2`;
  - every `rpcn-author__*` scenario once, including `existing_file` (the plain write still blocks) and the apply-report ones;
  - the trigger suite through the gate, at accuracy 1.0.

  Do not commit, and do not run `run_evals.py`. The record is shared with 8.3.

**Acceptance Criteria:**
- Given the repo, when the validator, `sync_shared --check`, all `tools/` suites (`rpcn_check` on both pins) and T's tests run, then all pass.
- Given the smoke, when it finishes, then both new scenarios pass 2/2, every `rpcn-author__*` passes, and the gate is at 1.0.
- Given the reviewed tree, when it is committed, then it stays local until 8.3's shared record.

## Implementation Notes

- `handoff-header.md` also names `change` in its `artifact` row and `change-format.md` among the format docs (synced into rpcn-design and rpcn-test).
- `hash --check` applies no first-input rule to `change@1` (rule 4 stays test-report only); the pipeline-first rule is in `change-format.md`'s Readiness list.
- A diff may create a file (`--- /dev/null`): not an input; apply Writes it only when it doesn't exist.
- A `[blocking]` item writes a `draft` proposal and ends `blocked` (consistent with the unlisted-component rule in `status-block.md`).
- SKILL.md is 4,800 characters (limit 4,803): Step 7 names both format docs, which the validator's file-refs rule requires; no room was left for a Next line.
- Matrix audit (coordinator): rows 3 and 5 gained headless T scenarios in `market/`, with shipped tests. `rpcn-author__change_stale` uses change_apply's proposal byte for byte, with one extra comment line in the pipeline: it ends `blocked` with every file unchanged. `rpcn-author__change_unlisted` asks for an `acme_queue` output: it writes a `draft` proposal (Proposed changes `None.`, one `[blocking]` item naming `acme_queue`) and ends `blocked`.
- Smoke results (session on 4.117.0, lint on 4.100.0 and 4.117.0):
  - `change_propose` and `change_apply` passed 2/2, at about $0.24 and $0.17 a run;
  - `change_stale` and `change_unlisted` passed 2/2, at about $0.13 and $0.20 a run;
  - all 19 earlier `rpcn-author__*` scenarios passed 1/1, including the four `change_*` ones;
  - the trigger gate was at 1.0 (86/86 runs).
- Review fixes (coordinator):
  - `change@1` `inputs`: the pipeline, then every resources and `.blobl` file read, plus `.env.example` when a diff changes it. On apply, every resources input is a `--resources` for lint.
  - `status-block.md`: in change mode an `(unverified)` diff ends `complete`, with `checks.lint: fail`.
  - `apply-report.md`: a `/dev/null` diff is Written only when the file is absent; otherwise the item is skipped and reported.
  - A request the pipeline already meets writes no proposal and ends `complete` with `artifacts: []`.
  - `change.md`: the no-op diff rule; the temp-dir and session-ID rule; the Read wording; the not-ready note line.
  - SKILL.md Next: "Report or proposal not ready: re-run its writer." and "Proposal written: review, then apply it.". To stay at 4,802 characters, I cut informational text only.
  - T: `(unverified)` added to change_propose's `lacks`; change_apply's `checks.lint` is checked; change_stale has `reply_contains` `changed`; all four change scenarios have stray globs at the project root and in the subfolder, built as a prefix chain so only the kept names pass. A shared test checks each glob against strays and kept files.
- Re-verification:
  - validator, `sync_shared --check`, `tools/tests` + `skills` (146) and `rpcn_check` on both pins (203): pass;
  - T tests: OK;
  - the four `change_*` scenarios at `--runs 2`: PASS 2/2 each;
  - the other 17 `rpcn-author__*` scenarios once: all PASS.
- The architecture's AD-6 writer table and `artifact:` list do not yet name `change` (not in this plan's Code Map).

- **Eval record (shared by 8.2 and 8.3):** `evals/results/2026-11-27-1978440ab31a.json` passed with `dirty: false`, at $76.70. Trigger accuracy 1.0; all 71 scenarios 2/2 on both pins. The first attempt ($75.87, 2026-11-26) failed only on `rpcn-test__dry_run_error`: rpcn-test's `SKILL.md` read `design-check.md` with no note. Fixed in `15aebfb`.

- **Pushed:** `64f13c5..491e126`, 8.2 and 8.3 together. CI run 46060786787 was green. T commits stay local.

## Plan Change Log

## Review Triage Log

Quick pass (2026-11-25): 0 high, 3 medium, 10 low, 0 false. All route to patch.

| # | Finding | Verdict | Action |
|---|---|---|---|
| 1 | A proposal hashes only the files its diffs change. An unchanged resources or `.blobl` file is then left out of the apply lint and of the stale check, against `handoff-header.md` ("every file the work read") | medium | `inputs` = the pipeline first, then every file read (resources, `.blobl`). The apply lint passes `--resources` for each resources input. |
| 2 | The `(unverified)` outcome (`complete`, lint fail) conflicts with `status-block.md`'s "lint still failing → blocked" | medium | A carve-out in `status-block.md` for change mode's copy lint. |
| 3 | A `--- /dev/null` (new file) diff has no apply procedure or result category | medium | `apply-report.md` §4: Write such a file only when it is absent, else skip it and say so; §5 reports it. |
| 4 | Nothing to change has no defined outcome | low | Write no proposal; the reply says the pipeline already does this; `complete`, `artifacts: []`. |
| 5 | Next sends a stale or draft proposal to rpcn-test, and has no "proposal written" line | low | Reword it to cover both (re-run the skill that wrote the file; a written proposal: review, then apply), trimming elsewhere to fit within 4,803. |
| 6 | `change.md` §1 says "Read only" but runs `hash --check` | low | Reword. |
| 7 | The not-ready note case doesn't match `status-block.md`'s `open_questions` line | low | Align. |
| 8 | Two of `fix-check.md`'s rules are missing: never look up the session ID, and the no-op diff rule | low | Add both. |
| 9 | `change_propose` doesn't prove the diff was verified | low | `lacks` `(unverified)`. |
| 10 | The stray globs only cover the subfolder, and `.ch*` names slip through | low | Add project-root globs and tighten the name globs. |
| 11 | `change_apply` has no stray globs and doesn't check its lint status | low | Add both. |
| 12 | `change_stale` doesn't check that the reason names the stale input | low | `reply_contains` the stale wording (`changed` or `stale`). |

## Verification

**Commands:**
- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`, `uv run --with pytest pytest -q tools/tests skills` -- pass
- `RPCN_TEST_BINARIES=<R>/.cache/rpcn/4.100.0/redpanda-connect:<R>/.cache/rpcn/4.117.0/redpanda-connect uv run --with pytest pytest -q tools/shared/rpcn_check/tests` -- pass
- `cd T && RPCN_TEST_BINARIES=… uv run run_scenarios.py --source local:<R> --runs 2 --no-judge --scenario 'rpcn-author__change_*'` -- PASS 2/2 each
