---
title: 'Design asks what only the user can decide'
type: 'feature'
ticket: '3'
created: '2026-11-21'
status: 'built'
baseline_revision: '8969862377c891704820fe75afcfb8ec56269369'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['_bmad-output/initiative-rpcn-skills/tickets/epic-design/epic-design.md', 'skills/rpcn-author/references/questions.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** rpcn-design never asks (`SKILL.md` "Never ask."). Every gap gets a pick, even in an interactive run where the user is there to answer. Epic R4 asks an interactive run to ask what only the user can decide: the failure target, the delivery guarantee, ordering and the idempotency key, each with the answer Design would pick. Every other choice gets a default.

**Approach:**
- **A questions reference:** new `skills/rpcn-design/references/questions.md`, shaped like rpcn-author's `questions.md`:
  - **The four asks:** the failure target, the delivery guarantee, ordering and the idempotency key. Each is asked unless the request already answers it. Nothing else is asked; every other choice gets a default from `patterns.md` or `note-writing.md`.
  - **Rounds:** at most two short rounds. Round 1 holds every open ask, numbered, each with `My pick: <pick>`, and the reply ends there with no file written. Round 2 is only for a new question an answer raised, never a repeat.
  - **After the answers:** an answer, or "go ahead", settles a choice. A pick the user accepts is written as `[non-blocking] … Picked: …`.
  - **A choice left open:** the user skips it or says it isn't decided. It is `[blocking]` only when it changes components (the failure target, the delivery guarantee), and the note is `draft`. Ordering or the idempotency key left open is `[non-blocking]`, with the pick written in.
- **SKILL.md:** "Never ask" becomes: interactive runs ask as `questions.md` says, and headless runs never ask. Stay at or under 4,803 characters.
- **`note-writing.md` Open decisions:** add the asked-and-left-open `[blocking]` case beside the existing "no listed component fits" case.
- **Headless is unchanged** (story 4 owns it).

## Boundaries & Constraints

**Always:**
- `SKILL.md` stays at or under 4,803 characters, with no validator warnings for the three skills.
- `design@1` is unchanged.
- Every existing headless scenario keeps passing unchanged.
- Smoke-run only; the eval record is story 4's, and 3 and 4 are pushed together.

**Never:**
- Changing headless behaviour or the status block (story 4).
- Changing rpcn-author or rpcn-test.
- More than two rounds of questions.
- A question the request or the binary already answers.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Interactive, all four open | a plain "read X, write Y" request | one reply with four numbered questions, each with `My pick:`; no note written; no status block | — |
| Interactive, answers in the prompt | the request names the DLQ topic, at-least-once delivery, per-key order and the dedupe key | no question; a `ready` note whose sections carry each answer | — |
| Interactive, failure target left open | the answers to three asks; "we haven't decided where failed messages go" | no question; a `draft` note with a `[blocking]` failure-target decision | — |
| Interactive, "go ahead" | the user accepts the picks | the picks written in as `[non-blocking]`; the note `ready` | — |
| Ordering or key left open | the user skips it | `[non-blocking]` with the pick; the note stays `ready` | — |
| Headless | any request | unchanged from 3.2 | — |

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`; `T` = `rpcn-test-skills` (local, baseline `2671dbea03ec33ba79fc8f1c2d0a50864399736a`; leave the untracked `orders_benthos_test.yaml` alone).

- **New `R/skills/rpcn-design/references/questions.md`:** the rules above. Reuse the shape and wording of `R/skills/rpcn-author/references/questions.md`, sections "One round of questions" (asking in a plain reply, `My pick:`, stop with no file written) and "Headless". Leave out Author's required-field rules. Say when to ask: after Steps 1–4, before Step 5 writes. An existing note still stops at Step 2 with no question.
- **`R/skills/rpcn-design/SKILL.md`** (4,790 characters, 13 to spare): replace the "**Never ask.** …" paragraph with a shorter one that points at `references/questions.md` and keeps the headless definition. Find the room in that paragraph and in Step 5. Add `questions.md` to the read before Step 5.
- **`R/skills/rpcn-design/references/note-writing.md` "Open decisions":** "Never ask" becomes "headless never asks; interactive asks first (`questions.md`)". Add the `[blocking]` case for a failure target or delivery guarantee the user left open. Keep the status-block line for headless.
- **`R/skills/rpcn-design/references/status-block.md`:** unchanged.
- **T, the new interactive scenarios** (`install = ["rpcn-design"]`, a subfolder with a non-default name, `no_cd`, `reply_lacks = ["```json"]`), modelled on `T/scenarios/rpcn-author__ask_first` and `__ask_existing`:
  - `rpcn-design__ask_first` (`ship/parcel_events`): a plain request. `reply_contains` `?`, `pick`, and one word per ask (`fail`, `deliver`, `order`, `duplicate`); the note `exists = false`; no YAML.
  - `rpcn-design__ask_answered` (`billing/invoice_sync`): all four answered in the prompt. `[[report]] ready = true`; `[[file]] contains` the DLQ topic, `[non-blocking]` absent for those four, the dedupe key's `| dedupe |` row and `max_in_flight`; `reply_lacks` `My pick`.
  - `rpcn-design__ask_failure_open` (`audit/login_events`): three answered, failure target "not decided yet". `[[report]] ready = false`; `contains` `status: draft`, `[blocking]`; no `| fallback |` row.
- **`T/tests/test_run_scenarios.py`:** a `ShippedDesignAskScenarioTests` class beside `ShippedDesignTracerScenarioTests` (line ~5134), asserting each scenario's key checks, as `test_ask_first_is_interactive_and_writes_nothing` (line ~4581) does for Author.
- **`R/evals/README.md`:** the pass-scenario count (45 → 48) and cost at 2 runs.

## Tasks & Acceptance

**Execution:**
- [ ] `R/skills/rpcn-design/references/questions.md`, `SKILL.md`, `note-writing.md` -- the asking rules -- R4.
- [ ] T: the three scenarios and their shipped tests -- the verify line.
- [ ] `R/evals/README.md` -- counts and cost.
- [ ] Smoke: the three new scenarios at `--runs 2` on both pins, then every `rpcn-design__*` scenario once. Record the results in Implementation Notes.

**Acceptance Criteria:**
- Given the repo, when the validator, `sync_shared --check`, all `tools/` suites and T's tests run, then all pass, and `SKILL.md` is at most 4,803 characters.
- Given the smoke run, when it finishes, then the three ask scenarios and every headless `rpcn-design__*` scenario pass, and `ask_first`'s one reply holds all four questions with their picks.
- Given the reviewed tree, when it is committed, then it stays local until story 4's record.

## Implementation Notes

- R: new `skills/rpcn-design/references/questions.md` (the four asks with their picks, what counts as already answered, two rounds, after the answers, a choice left open, headless). The example round labels each ask (Failure target, Delivery, Ordering, Duplicates) so `ask_first`'s reply words hold. Rounds, answers and left-open rules are marked interactive, so headless stays as in 3.2.
- R: `SKILL.md` "Never ask" paragraph replaced by the headless definition ("never ask, and end with the status block. Else ask first (Step 5)"); Step 5 first reads `references/questions.md`. 4,762 characters.
- R: `note-writing.md` Open decisions: "Headless never asks; interactive asks first"; `[blocking]` now also covers an interactive failure target or delivery guarantee the user left open (no DLQ or `fallback` added). Error handling's default-DLQ bullet points at the interactive ask.
- R: `evals/README.md` cost line: forty-eight pass scenarios, about $36 at 2 runs.
- T: scenarios `rpcn-design__ask_first`, `__ask_answered`, `__ask_failure_open`; `ShippedDesignAskScenarioTests` in `tests/test_run_scenarios.py`.
- Checks: validator (no warnings, 3 skills), `sync_shared --check`, `tools/tests skills` (146 passed), `rpcn_check` tests on 4.100.0 and 4.117.0 (192 passed), T tests (369 passed, 3 skipped).
- Smoke (sessions on 4.117.0, `[[lint]]`-style checks on both pins via `RPCN_TEST_BINARIES`):
  - `rpcn-design__ask_*` at `--runs 2`: `ask_first` 2/2 ($0.28/run), `ask_failure_open` 2/2 ($0.37), `ask_answered` 0/2 on the first try (see change log), then 2/2 ($0.46) after the fix.
  - every `rpcn-design__*` once: 13/13 PASS (`runs/20261121-192849`).
  - `ask_first`'s reply held all four numbered questions (Failure target, Delivery, Ordering, Duplicates), each with `My pick:`, and no note.
- Matrix audit follow-up (coordinator), covering the "go ahead" and "ordering or key left open" rows with the answer in the prompt:
  - T: `rpcn-design__ask_key_open` (`clicks/ad_click_feed`: DLQ `ad_clicks.failed`, at-least-once, no order, repeats undecided → ready, `[non-blocking]`, `Picked: no dedupe`, no `dedupe` row, no `[blocking]`) and `rpcn-design__ask_go_ahead` (`geo/device_pings`: a plain request ending "Don't wait on me: go ahead with your picks for anything I haven't said." → ready, `[non-blocking]`, `the request named none`, `| fallback |`, no `[blocking]`). Both added to `ShippedDesignAskScenarioTests`. T tests: 371 passed, 3 skipped.
  - R: `questions.md` "After the answers" now says a request that already says go ahead with your picks is that answer for every open ask (ask nothing, write), and a pick is written in the file's words (`Picked: no dedupe.`; the failure target as pattern 1 writes it). `SKILL.md` unchanged (4,762). `evals/README.md`: fifty pass scenarios, about $38 at 2 runs.
  - Smoke at `--runs 2`, `RPCN_TEST_BINARIES` = absolute 4.100.0 then 4.117.0: `ask_key_open` 2/2 ($0.40/run), `ask_go_ahead` 0/2 then 2/2 ($0.38/run) (`runs/20261121-193614`). The 0/2 was the check, not the skill: it asked nothing and wrote the right ready note, but its summary said "**My picks**", which `reply_lacks = "My pick"` caught. The no-question scenarios (`ask_answered`, `ask_failure_open`, `ask_key_open`, `ask_go_ahead`) now lack `My pick:`, the question line's own form.

- **Review fixes (2026-11-21, quick pass):** `questions.md` applies the "answers an ask" inferences to answers given in a round, and its open-failure-target `[blocking]` names no destination. `patterns.md` pattern 1 qualifies the default pick (headless, or a pick the user accepted). `ask_failure_open` lacks `the request named none` and `logins.dlq`. `ShippedDesignAskScenarioTests.load` rejects "unattended", "headless" and "non-interactive". `SKILL.md`: 4,770 characters.
- **Verification after the fixes:** validator no warnings; `sync_shared --check` clean; `tools/tests skills` 146 passed; `rpcn_check` tests on 4.100.0 and 4.117.0 192 passed; T 371 passed, 3 skipped. Smoke (`T/runs/20261121-194215`, all 15 `rpcn-design__*` at `--runs 1`, sessions on 4.117.0, checks on both pins): 15/15 PASS, $6.71.
- **Not done here:** the eval record (story 4's, shared), and the push (3 and 4 together).

## Plan Change Log

- 2026-11-21: `ask_answered`'s "`[non-blocking]` absent for those four" is checked as `lacks` on the four asks' pick lines (`the request named none`, `Picked: at-least-once`, `Picked: no ordering`, `Picked: no dedupe`) instead of a blanket `[non-blocking]`. The first smoke run's notes held `[non-blocking]` picks for other defaults (the dedupe cache's TTL, the output key), which the plan lets stand ("every other choice gets a default").

## Review Triage Log

Quick pass (2026-11-21): 0 high, 2 medium, 3 low, 0 false. Four route to patch, one to defer.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | The "answers an ask" inferences cover only the request, not a round-1 reply: "at-most-once" with Q1 skipped, or a DLQ named with Q2 skipped, would come out `[blocking]` | medium | patch | `questions.md` "A choice left open" applies to any skipped ask; the inference paragraph says "The request answers an ask". Make the inferences hold for answers in a round too. |
| 2 | `patterns.md` pattern 1 **When** still says, unconditionally, that a missing destination gets the default pick and the note stays ready; Step 3 reads it first | medium | patch | Pattern 1 line 29–34 has no interactive condition; `questions.md` and `note-writing.md` say the opposite for an interactive open failure target. Qualify pattern 1: headless, or an interactive pick the user accepted. |
| 3 | `ask_failure_open` accepts any `[blocking]` item and doesn't rule out a default DLQ named without a `fallback` row | low | patch | `expect.toml` checks only `[blocking]` and no `fallback` row. Add `lacks` on `the request named none` and `logins.dlq`, and mirror it in the shipped test. |
| 4 | `ShippedDesignAskScenarioTests.load` checks only "unattended"; "headless" and "non-interactive" also switch the skill to headless | low | patch | `SKILL.md` lists all three. Assert none is in the prompt. |
| 5 | The "go ahead" and "ordering/key left open" rows are covered by answers carried in the request, not by a reply after round 1 | low | defer | `claude -p` ends at the first reply and `[[step]]` sessions share no conversation, so a real round-1 reply needs multi-turn support in the runner. The behaviour under the row (picks written as `[non-blocking]`, the note ready) is checked. |

## Design Notes

**Why the four:** each changes the pipeline and has no safe default. The failure target and the delivery guarantee change components (a DLQ output, a `fallback`; at-most-once drops failures, so no DLQ). Ordering and the key change one setting or one processor, so a pick is safe to build on.

**Example round 1:**

```
1. Where should a message go when the API rejects it? My pick: the Redpanda topic `parcels.dlq`.
2. Delivery: at-least-once (failures retried or kept) or at-most-once (failures dropped)? My pick: at-least-once.
3. Must order hold, per parcel or overall? My pick: no ordering.
4. Can events repeat, and if so which field identifies one? My pick: no dedupe.
```

## Verification

**Commands:**
- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`, `uv run --with pytest pytest -q tools/tests skills` -- pass
- `RPCN_TEST_BINARIES=<abs 4.100.0>:<abs 4.117.0> uv run --with pytest pytest -q tools/shared/rpcn_check/tests` -- pass
- `cd T && uv run --with pytest pytest -q tests` -- pass
- `cd T && RPCN_TEST_BINARIES=… uv run run_scenarios.py --runs 2 --no-judge --scenario 'rpcn-design__ask_*'` -- all PASS
