---
title: 'Tracer: rpcn-design describes a hand-written pipeline'
type: 'feature'
ticket: '1'
created: '2026-11-25'
status: 'built'
baseline_revision: '9bc1695f0e79282fb159a994c3fee59656c9b5b5'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['_bmad-output/initiative-rpcn-skills/tickets/epic-existing-pipelines/epic-existing-pipelines.md', '_bmad-output/initiative-rpcn-skills/change-requests-vscode-extension/describe-an-existing-pipeline.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** rpcn-design only designs from a plain request, or re-runs over an existing note. It never reads a pipeline. So a hand-written pipeline can't take part in the note-driven flow (epic 8 R1, R2; initiative R22).

**Approach:**
- **Describe mode,** in a new `skills/rpcn-design/references/describe.md`, with a short pointer from Step 2. It applies when no note exists yet, the named pipeline `<dir>/<name>.yaml` (or `.yml`) exists, and the request asks for its design: "describe my pipeline …", "write a design note for `<file>`", "document this pipeline's design".
- **Reads, Read only:** the pipeline, its resources files and its `.blobl` files. It writes nothing but the note. Every component found is checked with `list` and `fields` (Steps 3–4). A component the binary doesn't list becomes a `[blocking]` item, and the note is `draft`, as today.
- **Writes `<note>` in `design@1`:**
  - **Purpose:** names the pipeline file it describes.
  - **`inputs: []`:** the pipeline is not hashed (epic decision, staleness option a).
  - **Components:** one row per component in config order.
  - **Error handling, Delivery and ordering, Idempotency and Batching:** what the config does. A behaviour claim needs a `patterns.md` Basis, or a field value with its `fields` description (AD-15).
  - **What the config can't show:** an open decision. It is `[blocking]` only for a four-asks gap the config leaves open, such as a sink failure with no target. Otherwise it is `[non-blocking]`, with the config's behaviour as the pick.
  - **Deviations:** the empty table (header row and separator).
- **Asking:** interactive runs ask only the open asks the config doesn't answer, as `questions.md` says, through the question tool when it is offered. Headless runs never ask.
- **Unchanged:**
  - a plain request, a re-run, an existing note (Step 2 stops or asks);
  - a note only, never YAML.
- **Description:** gains one describe phrase, so the trigger gate can test it. The full sibling fit is story 8.5.

## Boundaries & Constraints

**Always:**
- Every pipeline, resources, `.blobl` and `.env.example` file is byte-identical afterwards.
- `design@1` is unchanged. `SKILL.md` stays at or under 4,803 characters, and the description at or under 1,024. The validator shows no warnings.
- Sessions run on 4.117.0, and checks run on both pins. The record runs 2 times per case.

**Never:**
- A behaviour claim the config, `fields` and `SOURCES.md` don't back.
- Hashing the pipeline in `inputs`.
- Changing rpcn-author or rpcn-test.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Hand-written pipeline, headless | a `redpanda` input, a `mapping`, a `fallback` to `http_client` and a DLQ | ready note; components in config order; at-least-once with the DLQ; ordering a `[non-blocking]` pick naming the config's setting; `inputs: []`; every file unchanged | — |
| An unlisted component | a pipeline using a name the binary doesn't list | `[blocking]` item naming it; note `draft`; files unchanged | — |
| A sink failure with no target | no `fallback` or DLQ | `[blocking]` failure target; draft | — |
| A note already exists | `<name>.design.md` present | Step 2's rule: headless `blocked`, interactive asks | — |
| No such pipeline | the named file is missing | not describe mode: today's plain design path | — |
| A plain design request | no pipeline named | unchanged | — |

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`; `T` = `rpcn-test-skills` (local, baseline `5c05827c81d25a2bab61cc43b5a5e086f1ad40ab`; leave the untracked `orders_benthos_test.yaml` alone).

- **`R/skills/rpcn-design/SKILL.md`** (4,644 characters, about 159 to spare):
  - In the Step 2 not-found branch, add a pointer: "a named existing pipeline and a request for its design: `references/describe.md`".
  - Add one describe phrase to the description.
  - Trim nearby wording if needed, keeping every rule.
- **New `R/skills/rpcn-design/references/describe.md`:** the Approach above. Reuse `note-writing.md` for the sections and header, `patterns.md` for Basis, and `questions.md` for asks and "A choice left open". Say which config fields answer which ask: a `fallback` or `switch` to an output answers the failure target, and `max_in_flight` or an input's ordering field answers ordering, read from `fields`.
- **`R/skills/rpcn-design/references/questions.md`:** a line in "The four asks" saying the config's settings also answer an ask in describe mode.
- **New `R/evals/rpcn-design__trigger_describe_pipeline/`:** a positive case ("Describe my Redpanda Connect pipeline `pipes/orders.yaml` as a design note."), copied from `rpcn-design__trigger_update_note`. Update the README counts.
- **T, new scenarios** (headless, a subfolder with a non-default name, `no_cd`, `unchanged` on every fixture file). Each fixture pipeline must lint clean on both pins; check them with `rpcn_check lint`.
  - `rpcn-design__describe_pipeline`: the first matrix row. `[[report]] ready = true`; the note contains each component's row and `[non-blocking]`, and lacks `[blocking]`. Pick the ordering setting from what `fields inputs redpanda` reports on both pins (for example `unordered_processing`, if it's listed), else use the output's `max_in_flight`.
  - `rpcn-design__describe_unlisted`: an unlisted component gets `[blocking]` and a draft note. The fixture must still be a file the skill reads, even though it won't lint.
- **`T/tests/test_run_scenarios.py`:** shipped tests for both.
- **`R/evals/README.md`:** the counts and cost.

## Tasks & Acceptance

**Execution:**
- [ ] `describe.md`, the `SKILL.md` pointer and description phrase, the `questions.md` line, and the trigger case.
- [ ] T: the two scenarios and their tests; README counts.
- [ ] Smoke: both scenarios at `--runs 2` on both pins, then every `rpcn-design__*` once. The trigger suite through the gate, at accuracy 1.0. Do not commit and do not run `run_evals.py`; review comes first.

**Acceptance Criteria:**
- Given the repo, when the validator, `sync_shared --check`, all `tools/` suites and T's tests run, then all pass.
- Given the smoke, when it finishes, then both new scenarios pass 2/2, every `rpcn-design__*` scenario passes, and the trigger gate is at 1.0.
- Given the reviewed, committed tree, when `run_evals.py` runs (2 runs), then it passes with `dirty: false`. Then ask before pushing.

## Implementation Notes

- 2026-11-25, smoke (sessions on 4.117.0, checks on 4.100.0 and 4.117.0, `--no-judge`):
  - `describe_pipeline` and `describe_unlisted`: PASS 2/2, run twice. The second pair ran on the final skill text: after the first pair, describe.md gained a line saying that with no `dedupe`, Idempotency says only that the config has none (one note had claimed that redelivery re-posts, with nothing backing it). About $0.61 and $0.43 a run.
  - Every `rpcn-design__*` once (29 scenarios): all PASS.
  - Trigger suite at `--runs 2` through `eval_gate.py`: ok, accuracy 1.0, no failed runs.
- 2026-11-25, matrix audit: added `rpcn-design__describe_no_target` (row 3), `rpcn-design__describe_existing_note` (row 4) and `rpcn-design__describe_missing` (row 5), with shipped tests (T: 423 tests OK). All three PASS 2/2: about $0.47, $0.18 and $0.37 a run.
  - **`describe_no_target`:** a draft with `[blocking] Where do failed messages go`; no `fallback` row.
  - **`describe_existing_note`:** `blocked`; the note, the pipeline and `.env.example` are unchanged, and nothing else is written.
  - **`describe_missing`:** the plain path is consistent. Both runs wrote a draft placeholder note that says `ghost/order_tap.yaml` "does not exist". It holds only `[blocking]` items for source, sink, failure target and delivery, and an empty Components table. Neither run tried to Read the missing file (it was checked with `ls`). The check is:
    - the note is not ready;
    - it contains `does not exist` and `[blocking]`;
    - it lacks "Describes `ghost/order_tap.yaml`" and any `| input |` or `| output |` row;
    - no YAML is written.

    Risk: a run that writes "doesn't exist" would fail the check.
- `evals/README.md`: 43 trigger cases (~$6.00) and 66 pass scenarios (~$64 for a default run).
- 2026-11-25, review fixes:
  - **`describe.md`:**
    - the read list and config order cover inline `*_resources`, a shared resources file a `resource:`/`cache:`/`rate_limit:` label points to, `.blobl` files imported by another `.blobl`, input and output `processors`, `broker` children, and the buffer between the input and the pipeline;
    - the request-keyed rules of `note-writing.md` and `patterns.md` read "the config" for "the request";
    - delivery is a `[non-blocking]` pick (`Picked: at-least-once — failed writes are kept in <the DLQ>.`, or at-most-once for a `drop`), never a claim, and Error handling keeps pattern 1's fact;
    - an interactive answer that differs from the config is recorded as intent beside what the config does, and adds no component;
    - Throughput stays `None.` for a `rate_limit`, since a cap goes in Components.
  - **`questions.md`:** "A choice left open" and "Headless" add "(in describe mode, or the config)". Describe mode suggests no destination.
  - **T scenarios:**
    - the pick lines are tied: `Picked: no ordering (unordered_processing` and `Picked: at-least-once — failed writes are kept in \`orders.dlq\``;
    - `[blocking] acme_queue` is one string (this wording held in all ten runs read so far);
    - `describe_missing` drops "does not exist" and adds `read_lacks = ["ghost/order_tap.yaml"]`;
    - each describe scenario with a fixture pipeline has "no other file" globs: by name (`<name>[!.]*`, `<name>.[!dy]*`, `<name>.y[!a]*`, `<name>.yaml?*`) and by other names (`[!<first>.]*`, `*.yml`, `*[!<last>].yaml`). A shipped test proves they catch `<name>.yml`, `<name>.resources.yaml`, `<name>2.yaml` and `other.yaml`;
    - `[[lint]] ok = true` is added for the three lintable fixtures.
  - **`evals/README.md`:** pass scenarios ~$57.20, default run ~$63.
- 2026-11-25, smoke after the fixes (absolute `RPCN_TEST_BINARIES`, 4.100.0 first):
  - The five `rpcn-design__describe_*` at `--runs 2`: all PASS 2/2 (`runs/20261125-171000`).
  - The other 27 `rpcn-design__*` once: all PASS (`runs/20261125-171214`). The runner still exited 1, because `compare_design`'s third-party `connect-plugin` arm timed out at 600 s. Our arm scored 5/5 and won; that arm is not under test here.
  - Validator ok with no warnings; T's tests: 423 OK.
- Not done yet: the commit and the `run_evals.py` record, which wait for review.

- **First record failed** (2026-11-25, $73.21; the failed file is in the scratchpad): 65/66 scenarios passed 2/2. `describe_missing` was 1/2, only on `read_lacks`: one Read to see whether the file exists is how Design checks it, and that check was added in review. It was dropped, and T's fix is `64ef6f4`.
- **Eval record:** `evals/results/2026-11-25-fa87b4f80a78.json` passed with `dirty: false`, at $66.82. Trigger accuracy 1.0, all 66 scenarios 2/2 on both pins.

## Plan Change Log

## Review Triage Log

Quick pass (2026-11-25): 0 high, 5 medium, 6 low, 0 false. All route to patch.

| # | Finding | Verdict | Route | Action |
|---|---|---|---|---|
| 1 | "Delivery says at-least-once" is a behaviour claim nothing in the config or `fields` backs (AD-15) | medium | patch | Keep pattern 1's backed fact (failed writes go to the DLQ). Write the delivery guarantee as a `[non-blocking]` pick ("Picked: at-least-once — failed writes are kept in `orders.dlq`"), never as a claim. |
| 2 | An interactive answer can make the note stop describing the config, or add a component the pipeline lacks | medium | patch | In describe mode, an answer that differs from the config is recorded as intent beside what the config does, and adds no component. |
| 3 | `questions.md` still says headless settles asks "from the request alone", and contradicts `describe.md`'s "no Suggested destination" | medium | patch | Say "from the request, or in describe mode the config". State the describe exception in `questions.md`. |
| 4 | `note-writing.md` ("from the request … only") and the pattern rules keyed to the request aren't overridden for describe mode | medium | patch | `describe.md` says those rules read "the config" in describe mode. |
| 5 | Coverage gaps: resources defined inside the pipeline file and in shared files, nested processors and `broker` children, `.blobl` imports, the buffer's place in config order | medium | patch | Extend `describe.md`'s read list and its order. |
| 6 | Config order and the ordering pick aren't proved by the checks | low | patch | Tighten where the runner allows it: a `contains` string tying the setting to its pick line. |
| 7 | `[blocking]` isn't tied to `acme_queue` | low | patch | A `contains` string tying the two. |
| 8 | `describe_missing` relies on the phrase "does not exist", and nothing proves the file was never read | low | patch | Use `read_lacks` on the missing path, drop the phrase, and keep the draft and component-free checks. |
| 9 | The "no YAML written" globs skip same-letter names | low | patch | Use `<name>.*` / `<name>[!.]*` globs, as `rerun_bad_header` does. |
| 10 | The fixtures' lint-clean state isn't shown | low | patch | Add a `[[lint]] ok = true` on each lintable fixture. |
| 11 | A `rate_limit` is treated as a throughput rate; the README cost totals are off | low | patch | A rate limit is a cap, written in Components or a role, not Throughput. Fix the arithmetic. |

## Verification

**Commands:**
- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`, `uv run --with pytest pytest -q tools/tests skills` -- pass
- `claude plugin eval . --ablation none --runs 2 --tag trigger --no-publish --trust-plugin --json <out>.json`, then `uv run tools/eval_gate.py <out>.json` -- accuracy 1.0
- `cd T && RPCN_TEST_BINARIES=<R>/.cache/rpcn/4.100.0/redpanda-connect:<R>/.cache/rpcn/4.117.0/redpanda-connect uv run run_scenarios.py --source local:<R> --runs 2 --no-judge --scenario 'rpcn-design__describe_*'` -- PASS 2/2 each
