---
title: 'Headless Design writes a draft note with its open decisions'
type: 'feature'
ticket: '4'
created: '2026-11-21'
status: 'built'
baseline_revision: 'ab87f48a426017fbdc00b0b55fd685d1250819a9'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['_bmad-output/initiative-rpcn-skills/tickets/epic-design/epic-design.md', '_bmad-output/initiative-rpcn-skills/tickets/epic-design/tickets/story-design-asks-what-only-the-user-can-decide-plan.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** headless rpcn-design never asks, but it also never stops at what only the user can decide. With no failure target named, it writes a `ready` note with the default DLQ as a `[non-blocking]` pick (story 3.2). Epic R5 asks a headless run to write a `draft` note listing its open decisions and to end with the status block. R4's rule decides what blocks: an unanswered choice is `[blocking]` only when it changes components (the failure target, the delivery guarantee).

**Decision (2026-11-21, user):** draft, per R4/R5. This replaces 3.2's decision for headless runs.
- **The failure target or delivery guarantee:** when nothing in the request settles it (by 3.3's inferences in `questions.md`: a named DLQ, retries or "drop"), it is a `[blocking]` open decision. Its question may name the default DLQ as a suggestion. The note is `draft`, with no DLQ output and no `fallback` row for it.
- **Ordering and the idempotency key:** these stay `[non-blocking]` picks. So do all other defaults.
- Interactive behaviour (3.3) is unchanged.

**Decision (2026-11-21, user, review):** a request that asks for a DLQ without naming it ("failed messages go to a dead-letter topic") settles the failure target in both modes. The default DLQ is written as a `[non-blocking]` pick, and the note stays ready. In this one case, interactive no longer asks the failure-target question.

**Approach:**
- `questions.md` "Headless" applies the same "settled or left open" rule as interactive, without asking.
- `patterns.md` pattern 1 and `note-writing.md` (Error handling, Open decisions) drop the headless default-DLQ pick: with nothing to settle the failure target, it is `[blocking]` in both modes. The one exception is an interactive pick the user accepted.
- The run still ends `complete`. `open_questions` lists each `[blocking]` question and each `Assumed:` pick (`status-block.md`, unchanged unless its wording needs it).
- **T:**
  - A chain scenario: headless Design on an ambiguous request writes a draft. Then headless rpcn-author builds from the request alone and says the note is not ready.
  - The headless scenarios that named no failure target are updated to the new rule.

## Boundaries & Constraints

**Always:**
- `SKILL.md` stays at or under 4,803 characters, with no validator warnings for the three skills.
- `design@1` and rpcn-author are unchanged.
- This story's eval record covers 3.3 and 3.4 (2 runs, `dirty: false`); then both are pushed together, after asking.

**Never:**
- Asking in a headless run.
- Blocking on ordering, the idempotency key or any other default.
- A `blocked` status for a draft note.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Headless, no failure target | a plain copy, "unattended" | a `draft` note; a `[blocking]` failure-target item; no `fallback` row; status `complete` with it in `open_questions` | — |
| Headless, DLQ named | "failures go to `x.dlq`", unattended | the delivery guarantee is settled; a `ready` note, as today | — |
| Headless, ordering/key unstated | a DLQ named, nothing on order or repeats | `None.` or a `[non-blocking]` pick; the note `ready` | — |
| Headless, "drop failures" | unattended | at-most-once; no DLQ; the note `ready` | — |
| Chain | headless Design (draft), then headless Author | Author builds from the request, says the note is not ready, ends `complete` | — |
| Interactive | any | unchanged from 3.3 | — |

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`; `T` = `rpcn-test-skills` (local, baseline `e89369347c9f6c1bb1d1a492891b579e1fc4e71b`; leave the untracked `orders_benthos_test.yaml` alone).

- **`R/skills/rpcn-design/references/questions.md`:**
  - "Headless": never ask. Settle each of the four asks from the request with the inferences in "The four asks", then apply "A choice left open" as written: failure target or delivery → `[blocking]`; ordering or key → `[non-blocking]` pick.
  - "A choice left open": make it apply in both modes; it is headed "(interactive)" today.
- **`R/skills/rpcn-design/references/patterns.md` pattern 1 When** (lines ~28–36): with no destination named, write `[blocking] Where do failed messages go? (Suggested: <the default DLQ>.)`. Add no `fallback` or DLQ row, and the note is `draft`. An interactive pick the user accepted keeps the 3.3 `[non-blocking] … Picked: … — the request named none.` line.
- **`R/skills/rpcn-design/references/note-writing.md`:**
  - Error handling, the DLQ destination bullet: the same change as pattern 1.
  - Open decisions: the `[blocking]` list item "interactive only: a failure target or delivery guarantee the user left open" becomes both modes ("one nothing settles").
- **`R/skills/rpcn-design/references/status-block.md`:** already says a draft with a `[blocking]` item ends `complete` with it in `open_questions`. Touch it only if a wording conflict shows.
- **`R/skills/rpcn-design/SKILL.md`** (4,770 characters): it likely needs no change. If one is needed, stay at or under 4,803.
- **`T/scenarios/rpcn-design__pattern_default_dlq`:** the prompt is unchanged (a plain copy, unattended). The expectation becomes:
  - `[[report]] ready = false`, and the note `contains` `status: draft` and `[blocking]`;
  - the note `lacks` `| fallback |`, `` | `fallback` | ``, `the request named none`, `[blocking] Where do failed messages go? Picked`, and the other families (as today);
  - `[status] status = "complete"`, with `status_nonempty = ["open_questions"]` and `reply_contains = ["Where do failed messages go"]` (the reply includes the status block).

  Update its header comment, which now covers the 3.4 row "Headless, no failure target".
- **`T/scenarios/rpcn-design__pattern_batching`, `__pattern_idempotency`, `__pattern_ordering`:** add a named DLQ topic to each prompt (for example, "Failed writes go to the Redpanda topic `<input>.dlq`."), so they stay `ready` and keep their checks. Don't add a `| fallback |` `lacks`.
- **New `T/scenarios/rpcn-design__chain_headless_draft`** (a subfolder with a non-default name, for example `intake/meter_reads`), modelled on `rpcn-design__chain_tracer`'s `[[step]]` layout:
  - **Step 1:** headless Design on a request naming no failure target. `[step.status]` is `complete`, `skill = "rpcn-design"`, `artifacts = ["<note path>"]`.
  - **Step 2:** headless rpcn-author, "Write the Redpanda Connect pipeline `<path>.yaml` …" with the same request. It ends `complete` (top-level `[status]`), with `status_nonempty = ["open_questions"]`, `reply_contains = ["not ready", "draft"]`, and `unchanged` on the note.
  - The note's `[[report]] ready = false` and `[[file]] contains` `[blocking]`; the pipeline's `[[lint]] ok = true`.
- **`T/tests/test_run_scenarios.py`:**
  - Update the `ShippedDesignTracerScenarioTests.PATTERNS` entries that read `default_dlq`'s checks.
  - Add a test for the chain's key checks.
- **`R/evals/README.md`:** the count (51 pass scenarios) and cost.
- **`R/_bmad-output/initiative-rpcn-skills/tickets/epic-design/tickets/story-design-recommends-each-pattern-from-a-sourced-fact-plan.md`:** don't edit it. 3.2's decision is superseded here, in this plan.

## Tasks & Acceptance

**Execution:**
- [ ] `questions.md`, `patterns.md`, `note-writing.md` (and `status-block.md` only if needed) -- the headless rule -- R4/R5.
- [ ] T: `pattern_default_dlq` re-expected, the three pattern prompts given a DLQ, the new chain, their shipped tests, and the README count.
- [ ] Smoke: every `rpcn-design__*` scenario once on both pins (sessions on 4.117.0), plus the new chain at `--runs 2`. Record the results in Implementation Notes.

**Acceptance Criteria:**
- Given the repo, when the validator, `sync_shared --check`, all `tools/` suites (`rpcn_check` on both pins) and T's tests run, then all pass.
- Given the smoke run, when it finishes, then every `rpcn-design__*` scenario passes.
- Given the reviewed, committed tree, when `run_evals.py` runs (2 runs, about $40), then it passes with `dirty: false`, and the record is committed for 3.3 and 3.4.

## Implementation Notes

- R: `questions.md`: "A choice left open" now applies in both modes (headless: nothing in the request settles the ask); headless may suggest the pattern 1 default in the `[blocking]` question. "Headless" settles the four asks from the request by "The four asks" inferences, then applies "A choice left open" (failure target or delivery `[blocking]`, note `draft`; ordering or key a `[non-blocking]` pick), and a draft still ends `complete`. The inferences now say a DLQ asked for without a name ("a dead-letter topic") settles the failure target, its name the pattern 1 default as a `[non-blocking]` pick.
- R: `patterns.md` pattern 1 When: no failure target settled → `[blocking] Where do failed messages go? (Suggested: <the default DLQ>.)` (interactive, no suggestion), no `fallback` or DLQ row, `draft`. The default DLQ `[non-blocking] … — the request named none.` pick stays for an unnamed DLQ the request asks for and for an interactive pick the user accepted.
- R: `note-writing.md` Error handling (DLQ bullet) and Open decisions (`[blocking]` for a failure target or delivery guarantee nothing settles, either mode). `status-block.md` and `SKILL.md` unchanged (4,770 characters).
- R: `evals/README.md`: fifty-one pass scenarios, about $40 at 2 runs.
- T: `pattern_default_dlq` re-expected (draft, `[blocking]`, no `fallback`, `status_nonempty`/`reply_contains` as top-level keys, as the runner reads them); `pattern_batching`/`idempotency`/`ordering` prompts name `clicks.dlq`/`events.dlq`/`orders.dlq`; new `rpcn-design__chain_headless_draft` (`intake/meter_reads`, two steps); `ShippedDesignTracerScenarioTests`: `default_dlq` moved out of `PATTERNS` into `test_default_dlq_is_blocking_headless`, a `DLQS` prompt check, and `test_chain_headless_draft`.
- Checks: validator no warnings (3 skills); `sync_shared --check` clean; `tools/tests skills` 146 passed; `rpcn_check` tests on 4.100.0 and 4.117.0 192 passed; T 373 passed, 3 skipped.
- Smoke (sessions on 4.117.0, checks on both pins): every `rpcn-design__*` at `--runs 1`: 16/16 PASS (`T/runs/20261121-203419`). `chain_headless_draft` at `--runs 2`: 2/2 ($0.70/run, `T/runs/20261121-203818`). The `default_dlq` and chain notes held `[blocking] Where do failed messages go? (Suggested: …)` and a `[blocking]` delivery question, with ordering and key as `[non-blocking]` picks.
- Matrix audit follow-up (coordinator), the row "Headless, 'drop failures'":
  - T: `rpcn-design__headless_drop` (`metrics/gauge_relay`: a headless plain copy, a failed write "logged and dropped" → complete, ready, `status: ready`, `## Error handling`; lacks `[blocking]`, `| fallback |`, `` | `fallback` | ``, `.dlq`, `the request named none`; no YAML), plus `test_headless_drop` in `ShippedDesignTracerScenarioTests`. T tests: 374 passed, 3 skipped.
  - Smoke at `--runs 2` (`RPCN_TEST_BINARIES` = absolute 4.100.0 then 4.117.0): 1/2 at first (`T/runs/20261121-204049`). Run 1 wrapped the sink in `drop_on`; run 2 built a `fallback` to a `log` processor then a `drop` output (no DLQ, but a `| fallback |` row).
  - R fix: `note-writing.md` (log and drop: pattern 1 doesn't apply, no `fallback`, not even to a `drop` or `log`; a component only when `fields` shows one that drops on a failed write) and `patterns.md` pattern 1 When (the same, briefly). After it: 2/2 ($0.41/run, `T/runs/20261121-204204`). Validator no warnings, `sync_shared --check` clean, `tools/tests skills` 146 passed. The other `rpcn-design__*` scenarios were not re-run after this fix (it touches only drop requests).
  - R: `evals/README.md`: fifty-two pass scenarios, about $41 at 2 runs.
- **Not done here:** the review, the commits, the eval record (2 runs, about $40, `dirty: false`, covering 3.3 and 3.4) and the push (after asking).

- **Final verification (2026-11-21, after the review patches):** validator no warnings; `sync_shared --check` clean; `tools/tests skills` 146 passed; `rpcn_check` tests on both pins 192 passed; T 374 passed, 3 skipped; `SKILL.md` 4,770 characters. Smoke (`T/runs/20261121-205428`, all 17 `rpcn-design__*` scenarios once): 16/17 PASS. `chain_tracer` failed in step 3: Design said the DLQ copy carries `fallback_error`, Author didn't write that metadata, and Test reported a mismatch. This dates from story 3.2 and is deferred. A re-run passed 2/2 (`T/runs/20261121-210958`).
- **Not done here:** the shared 3.3 + 3.4 eval record, and the push.

## Plan Change Log

- 2026-11-21: the chain checks the note with `[[file]]` (still `status: draft`, `[blocking]`, the Deviations header, `lacks` `| fallback |` and `| 20` for a dated Deviations row) instead of `unchanged`: the runner's `unchanged` compares against `fixtures/`, and the chain's note is written by step 1.
- 2026-11-21: `questions.md` and pattern 1 say an unnamed DLQ the request asks for ("a dead-letter topic") settles the failure target, keeping the default-DLQ `[non-blocking]` pick, so `chain_tracer`, `npx_trigger` and `unlisted_component` (which ask for a DLQ without a name) keep their behaviour.

## Review Triage Log

Quick pass (2026-11-21): 0 high, 2 medium, 3 low, 0 false. One intent_gap, resolved by the user in favour of the build, so the code is unchanged. Three route to patch and one is rejected.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | The unnamed-DLQ inference changes interactive behaviour; the intent listed only a named DLQ, retries or "drop" | medium | intent_gap | The user chose "yes, both modes". It is recorded in the Intent as a decision. The built code already does this, so nothing is reverted. |
| 2 | The full smoke ran before the last `skills/` edit (the drop fix in pattern 1's When, read on every run) | medium | patch | Re-run every `rpcn-design__*` scenario on the final tree. |
| 3 | The chain's note check is weaker than "Author leaves the note untouched" | low | reject | That Author leaves a not-ready note byte-identical is already checked with `unchanged` by `rpcn-author__design_draft`. Proving it here needs a cross-step compare in the runner (new surface). |
| 4 | The `DLQS` comment says each entry gained a DLQ, but `pattern_dlq_retry` already named one | low | patch | Fix the comment. |
| 5 | `test_chain_headless_draft` pins only `\| fallback \|` of the note's `lacks` | low | patch | Pin the full `lacks` list, as the other two tests do. |

## Verification

**Commands:**
- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`, `uv run --with pytest pytest -q tools/tests skills` -- pass
- `RPCN_TEST_BINARIES=<abs .cache/rpcn/4.100.0/redpanda-connect>:<abs .cache/rpcn/4.117.0/redpanda-connect> uv run --with pytest pytest -q tools/shared/rpcn_check/tests` -- pass
- `cd T && uv run --with pytest pytest -q tests` -- pass
- `cd T && RPCN_TEST_BINARIES=… uv run run_scenarios.py --source local:<R> --runs 1 --no-judge --scenario 'rpcn-design__*'` -- all PASS
