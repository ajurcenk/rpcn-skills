---
title: 'Tracer: rpcn-design writes a ready note that Author builds and Test checks'
type: 'feature'
ticket: '1'
created: '2026-11-21'
status: 'built'
baseline_revision: 'b78adf3c9177cae1f23faeb69778450e3e5b4397'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['_bmad-output/initiative-rpcn-skills/tickets/epic-design/epic-design.md', 'tools/shared/formats/design-format.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** there is no `rpcn-design` skill. Author (2.6) and Test (2.10) read and check a design note, but in every test so far the note was written by hand. Epic 3's tracer is the thinnest path through every layer: Design, Author reading the note, Test checking against it, and a runner that can run those as separate sessions.

**Approach:**
- **New skill `skills/rpcn-design`:**
  - It follows the shape of rpcn-author and rpcn-test: `SKILL.md`, references one level deep, the shared copies listed in `shared.txt` (`rpcn_check.py`, `design-format.md`, `handoff-header.md`), and Next lines.
  - From a plain request, it writes `<dir>/<name>.design.md` in `design@1`.
  - Every component in the note is checked with `rpcn_check list` and `fields`.
  - The note is hashed and passes `hash --check` as `ready`.
  - Patterns are minimal in this story. Error handling names the failure destination (a DLQ) and the retries. Every other pattern section is filled with what the request says, or "None." Story 2 adds the full set.
  - Headless only in this story: it never asks, and a gap is written as `[non-blocking]` with its pick. Stories 3 and 4 settle asking and draft notes.
- **Triggers:** the eval cases `rpcn-design__trigger_*` (at least three positives, such as "design a Redpanda Connect pipeline") and `rpcn-design__miss_*` near-misses ("write the pipeline YAML" belongs to rpcn-author; "lint it" to rpcn-test). A runner scenario `rpcn-design__npx_trigger` installs rpcn-design alone through `npx`. Sibling descriptions are story 7.
- **Chains in the runner:** a scenario may list steps. Each step runs its own `claude -p` session, with its own prompt and skill, in the same run folder, one after another, each starting from the files alone (R16). The checks run after the last step, and the run's wall time is the sum of its steps. Single-step scenarios work as today.
- **Tracer scenario `rpcn-design__chain_tracer`, headless, in a subfolder with a non-default name:**
  - step 1: rpcn-design from a plain request;
  - step 2: rpcn-author "build from the design note";
  - step 3: rpcn-test "test the pipeline".
  - Checks: the note is `ready` (hash and readiness), the pipeline lints clean on 4.100.0 and 4.117.0, the report is ready, and Design check reports `0 mismatch`.

## Boundaries & Constraints

**Always:**
- The `design@1` format is unchanged (epic 1).
- rpcn-design writes only its own note (AD-6).
- `SKILL.md` stays at or under 4,803 characters, and its description at or under 1,024. The validator shows no warnings for any of the three skills.
- Every RPCN fact the skill states comes from `rpcn_check` at run time, or from a SOURCES.md row proved on 4.100.0 and 4.117.0 (AD-15).
- `claude plugin eval` keeps `--no-publish`.

**Never:**
- Edit rpcn-author or rpcn-test (story 7).
- Write pipeline YAML from rpcn-design.
- Ask questions in this story.
- Add patterns beyond error handling and the DLQ (story 2).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Plain request, headless | "orders from Redpanda to an HTTP API, failures to a DLQ" | ready `<dir>/<name>.design.md`, 11 sections, components the binary reports | — |
| A component the binary doesn't list | the request names one | a close match from `fields`, or the gap as a `[blocking]` open decision | never write an unlisted component |
| An existing note | `<dir>/<name>.design.md` exists | not overwritten in this story: `blocked`, with the reason | the re-run is story 5 |
| The chain | 3 steps | the note is ready, the pipeline lints, the report is ready, 0 mismatch | a step that fails stops the chain; its checks report it |
| Trigger | "design a pipeline …" | rpcn-design fires; on a near-miss it stays silent | — |
| Single-step scenarios | every existing one | run unchanged | — |

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`; `T` = `rpcn-test-skills` (local, baseline `bf3c07e2484645dedb99542daee18899d34a23ea`; leave the untracked `orders_benthos_test.yaml` alone).

- **The `R/skills/rpcn-author/` model:**
  - `SKILL.md` steps: binary, name the files, `hash --check` on the note, pick components (`list`), check fields (`fields`), write, lint, Next, status block;
  - `references/`, with shared copies via `shared.txt`;
  - `scripts/rpcn_check.py`, a shared copy.
- **New `R/skills/rpcn-design/`:**
  - `SKILL.md`: binary; name the files; refuse an existing note (story 5 adds the re-run); pick components; check fields; write the note; hash it; check it; Next is rpcn-author; status block (AD-8).
  - `references/note-writing.md`: how to fill each section from a request, the minimal error-handling pattern, and the `[non-blocking]` rule.
  - `references/status-block.md`.
  - `shared.txt` lists `rpcn_check/rpcn_check.py`, `formats/design-format.md` and `formats/handoff-header.md`. Then run `tools/sync_shared.py`.
- **`R/tools/validate_skills.py`** already checks every `skills/<x>/`. Check that it runs on rpcn-design (clash list, `use rpcn-<x>` siblings).
- **`R/evals/`:**
  - new `rpcn-design__trigger_*` (positive, `graders/fired.md` matching `rpcn-design`) and `rpcn-design__miss_*` (`graders/not-fired.md`, `arm: both`);
  - `tools/eval_gate.py` finds the cases by folder name, so no code change is expected;
  - `evals/README.md`: counts and cost.
- **`R/tools/run_evals.py`:** check that it installs and covers a third skill without a code change; the scenario list comes from T.
- **`T/run_scenarios.py`:**
  - `Scenario`, `load_scenario` and `run_once`. Add `[[step]] {prompt, skill}` to `expect.toml`, where `prompt` is a file in the scenario folder. With steps, `install` holds every step's skill.
  - `run_once` runs each step's `claude -p` in the same `run_dir`, records each step's turns, cost and reply, and puts the sums in the run.
  - The `skill` and `status` checks apply to the last step; a per-step `[status]` is optional, the builder's choice.
  - Keep `--rejudge`, the comparisons and the current single-step path working, and add tests.
- **New `T/scenarios/`:**
  - `rpcn-design__chain_tracer`: steps; `[[design]]` or `[[report]]` with `ready = true` on the note; `[[lint]]` on the pipeline; `[[report]]` on the test report; a check that the report contains `0 mismatch`.
  - `rpcn-design__npx_trigger`: the single-step npx positive, as `rpcn-author__npx_trigger` does it.
  - `rpcn-design__npx_miss`.
- **`T/README.md`:** steps.

## Tasks & Acceptance

**Execution:**
- [x] `R/skills/rpcn-design/` (`SKILL.md`, references, `shared.txt`), then `sync_shared.py`.
- [x] `R/evals/` (trigger and miss cases, README).
- [x] `T/run_scenarios.py`: steps, plus tests (single-step regression included).
- [x] The T scenarios (`chain_tracer`, `npx_trigger`, `npx_miss`) and the README.
- [x] Smoke: the three new scenarios at `--runs 1` on both binaries, then all non-compare scenarios once (about $10). Record the results in Implementation Notes.

**Acceptance Criteria:**
- Given the repo, when the validator, `sync_shared --check`, all `tools/` suites, `rpcn_check` on both binaries and T's tests run, then all pass, and the validator shows no warnings for any of the three skills.
- Given the smoke run, when it finishes, then every scenario passes, including the chain tracer.
- Given the reviewed, committed tree, when `run_evals.py` runs, then it passes, and a `dirty: false` record is committed.

## Implementation Notes

- **rpcn-design:** `SKILL.md` 4,644 characters, description 860. Steps: binary, name the note, `hash --check` (any result but not-found means a note exists: `blocked`), `list`, `fields`, write, `hash --check`, Next, status block. References: `note-writing.md` (header, the eleven sections, the minimal error-handling pattern, the `[non-blocking]`/`[blocking]` rule), `status-block.md` (`checks` always `skipped`; a draft note with a `[blocking]` item ends `complete`), plus the shared `design-format.md`, `handoff-header.md`, `scripts/rpcn_check.py`. The skill states no RPCN behaviour fact of its own: retry fields and the DLQ wrapper come from `fields`/`list` at run time, and the wrapper shape points at `design-format.md`'s Example. No SOURCES.md row was needed.
- **Validator:** no errors or warnings for rpcn-author, rpcn-design, rpcn-test. `sync_shared --check` clean.
- **Evals:** 4 positives (`trigger_design_pipeline`, `trigger_design_note`, `trigger_failure_handling`, `trigger_plan_flow`), 2 sibling near-misses (`miss_write_yaml`, `miss_lint_pipeline`, rpcn-design silent) and 1 out-of-repo (`miss_kafka_streams`, any `rpcn-` silent). A `--runs 1` trigger pass of the whole suite (39 cases): gate ok, accuracy 1.0 (with `--min-runs 1`; not a record).
- **Runner (`T`):** `[[step]] {prompt, skill, [status]}`; `prompt.md` is a setup error beside steps; not with `silent` or `[compare]`. Each step is its own `claude -p` in the same run folder (`run-<i>.step-<k>.stream.jsonl`), with `step<k>.skill` and optional `step<k>.status` checks; a session error or a failing step check stops the chain and records `step k/n failed (…); steps … not run`. The run's turns, cost and Claude time are the step sums; `skill`, `[status]` and the reply checks read the last step; `no_cd`/`bash_lacks`/`read_lacks` cover every step; `visible` must hold in every step. Single-step runs are unchanged (regression test checks the record shape and transcript name). T tests: 356 passed, 3 skipped.
- **Smoke 1** (`--runs 1 --no-judge`, `RPCN_TEST_BINARIES` 4.100.0:4.117.0, `rpcn-design__*`, `runs/20261121-114401`): all 3 PASS. Chain tracer 74 turns, $1.30, 174 s; the note was `ready` with the eleven sections, components `redpanda`/`fallback`/`http_client`/`redpanda`, `retries: 3`, DLQ `orders.dlq`, three `[non-blocking]` picks; the pipeline linted clean on both binaries; the report was ready with `Design check: 3 ok, 0 deviation-recorded, 0 mismatch` (verdict `fail`, from other checks; the plan asks only for a ready report).
- **Smoke 2** (all 38 non-compare scenarios once, `runs/20261121-114755`, $12.39): 37 PASS; `rpcn-test__lint_broken` failed once on `read_lacks` (it read `references/unit-tests.md` after a failed lint). rpcn-test is unchanged in this story; a re-run at `--runs 2` (`runs/20261121-115714`) passed 2/2, so it is a model flake to watch.
- **Matrix-gap scenarios** (added after review): `rpcn-design__existing_note` (fixture `streams/order_sync.design.md`; `blocked`, the note `unchanged`, `exists = false` globs for any other file) and `rpcn-design__unlisted_component` (`acme_queue` input; a `draft` note with a `[blocking]` item, `[[report]] ready = false`, `acme_queue` absent from Components). Both PASS at `--runs 1` on both binaries (`runs/20261121-115955`, $0.11 and $0.28). `rpcn-design__*` is now 5 scenarios, so there are 40 pass scenarios.
- **Not done here:** review, commit and the `run_evals.py` record (AC 3).

## Plan Change Log

## Review Triage Log

Quick pass: 0 high, 3 medium, 5 low, 1 false, 0 maybe-false. Eight route to patch.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | AC 3 (the eval record) not met | false | reject | The record runs after review and commit. |
| 2 | Step 1's "exit 2 means stop" contradicts Step 6's fix-and-recheck and `status-block.md` | medium | patch | Fix: the exception covers Step 2's and Step 6's checks, matching `status-block.md`. |
| 3 | `note-writing.md` states an unsourced RPCN fact ("a message that fails processing goes to the same DLQ"); a `fallback` routes failed writes only | medium | patch | AD-15. Fix: Error handling states the request's destination for each kind of failure as intent, and names a component only for what Components lists. No mechanism claim; how to route is Author's job. |
| 4 | Step 2's naming rule doesn't cover an extensionless path (`flows/order_relay`), which every scenario uses | medium | patch | Fix: a named path without an extension gives `<dir>/` and `<name>` too. |
| 5 | The root README's skills table and install hint omit rpcn-design | low | patch | Add its row and a design example. |
| 6 | `evals/README.md` counts 38 pass scenarios; there are 40 | low | patch | Fix the count and the cost estimate. |
| 7 | Implementation Notes don't record the two gap scenarios' run | low | patch | Add `runs/20261121-115955` and the 5-scenario count. |
| 8 | `chain_tracer` can't catch rpcn-design writing YAML in step 1 (file checks run after step 3) | low | patch | Fix: step 1's status block lists only the note (`artifacts`). |
| 9 | `chain_tracer`'s note readiness is only partly checked, and the comment overclaims | low | patch | Fix: `[[report]] ready = true` on the note (`hash --check`), and a comment that says what is checked. |

## Verification

**Commands:**
- `uv run tools/validate_skills.py` — no warnings for rpcn-design, rpcn-author or rpcn-test
- `uv run tools/sync_shared.py --check` — clean
- `uv run --with pytest pytest -q tools/tests skills` — pass
- `cd T && uv run --with pytest pytest -q tests` — pass
- `cd T && RPCN_TEST_BINARIES=<abs 4.100.0>:<abs 4.117.0> uv run run_scenarios.py --runs 1 --no-judge --scenario 'rpcn-design__*'` — all PASS
