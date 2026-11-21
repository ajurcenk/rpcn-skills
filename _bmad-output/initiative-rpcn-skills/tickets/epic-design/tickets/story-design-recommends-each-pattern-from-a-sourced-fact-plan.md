---
title: 'Design recommends each pattern from a sourced fact'
type: 'feature'
ticket: '2'
created: '2026-11-21'
status: 'built'
baseline_revision: '6f9c948ee2ba51f9038af4509c0b84d94465a177'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 1
context: ['_bmad-output/initiative-rpcn-skills/tickets/epic-design/epic-design.md', 'skills/rpcn-design/references/note-writing.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** story 3.1's rpcn-design knows only one pattern, a DLQ for failed writes. Epic R1 asks the note to name every pattern relevant to the request: error handling and DLQ, retries, batching, idempotency and ordering. R3 asks that each recommendation names the behaviour fact it rests on, proved on both binaries (AD-15). The binary can't report a best practice, only the behaviour under it.

**Approach:**
- **A patterns reference:** `skills/rpcn-design/references/patterns.md`, with one entry per pattern. Each entry has:
  - when it applies (what in the request calls for it);
  - what the note says in its section;
  - the components that carry it out, as the Components rows Design lists;
  - the behaviour fact it rests on, cited by its SOURCES.md row.
- **Pattern families and the facts to prove,** each with a real-binary test on 4.100.0 and 4.117.0, run through stdin and stdout so no broker is needed:
  - **DLQ for failed writes:** a `fallback` output sends a message to its next output when an earlier one fails, and sets the `fallback_error` metadata.
  - **DLQ for processing errors:** a `switch` output whose case `check` is `errored()` routes a message a processor failed on.
  - **Retries:** a `retry` output tries again up to `max_retries`, then fails, so a surrounding `fallback` takes the message.
  - **Batching:** an output's `batching.count` delivers messages in groups of that size.
  - **Idempotency:** a `dedupe` processor with a local cache drops a message whose key it has already seen.
  - **Ordering:** `max_in_flight` is read from `rpcn_check fields` at run time, which needs no row (AD-15: what the binary reports comes from the binary). The recommendation to set it to 1 for per-key order names that field's reported description as its basis.
- **Sources:** patterns adapted from `redpanda-data/skills` (`skills/connect/references/patterns.md`, at commit `a4562333`, Apache-2.0) get a SOURCES.md row naming source, commit and licence. A claim in the reference that no test proves, such as `auto_replay_nacks`, is left out.
- **Design uses it:** `note-writing.md` and `SKILL.md` point at `patterns.md` from the step that writes the note. Design names each pattern the request calls for, and only those, and lists its components.

**Decision (2026-11-21, user, review loop 1):** when the request names no failure destination, Design keeps 3.1's default DLQ (`<input topic>.dlq`, or `<name>.dlq.jsonl`), written as an explicit `[non-blocking]` pick in Open decisions ("Picked: … — the request named none"). The note stays ready. Every other pattern (retries, processing-error routing, batching, idempotency, ordering) is named only when the request calls for it; otherwise its section says `None.`.

## Boundaries & Constraints

**Always:**
- Every pattern in `patterns.md` cites either a SOURCES.md row proved on 4.100.0 and 4.117.0, or a value `rpcn_check list` or `fields` reports at run time.
- `SKILL.md` stays at or under 4,803 characters. The validator gives no warnings for any of the three skills.
- The `design@1` format is unchanged.
- Eval records run 2 times per case (decision 2026-11-21).

**Never:**
- Asking questions (stories 3 and 4).
- Changing rpcn-author or rpcn-test.
- A pattern without a sourced fact.
- Copying text from the reference set without a SOURCES row.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| A request with failures to a DLQ and retries | "post to the API, retry 3 times, then to `orders.dlq`" | Error handling names the retries and the DLQ; Components lists the `retry`/`fallback` chain | — |
| A request with processing failures | "orders that fail processing go to the DLQ" | Error handling names the DLQ for processing errors; Components lists the `switch` | — |
| A request with batching | "write to S3 in batches of 100" | Batching names the count; the output's batching is in Components or its role | — |
| A request with duplicates | "events may repeat; drop duplicates by `event_id`" | Idempotency names `event_id`; Components lists `dedupe` and its cache | — |
| A request with per-key order | "keep each customer's orders in order" | Delivery and ordering names `max_in_flight: 1` on that path | — |
| A request that needs none of these | a plain copy | the default DLQ as a `[non-blocking]` pick; retries, batching, idempotency and ordering say `None.` | — |
| A fact that changes on a binary | a proof fails on 4.117.0 | the pattern is reported and not shipped | — |

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`; `T` = `rpcn-test-skills` (local, baseline `9be79edc624608126da229786b59c9f688bcba7f`; leave the untracked `orders_benthos_test.yaml` alone).

- **New `R/skills/rpcn-design/references/patterns.md`:** the pattern entries. Write it in our own words; where text is adapted from `/home/aleksejjurcenko/projects/skills/skills/connect/references/patterns.md` (patterns 4, 5, 6, 9 and 2), record that.
- **`R/skills/rpcn-design/references/note-writing.md`:** replaces 3.1's minimal error-handling pattern with "use `patterns.md`". Keep its intent wording for destinations (3.1 review fix): state where each failure goes as the request's intent.
- **`R/skills/rpcn-design/SKILL.md`** (4,698 characters): the write step names `references/patterns.md`.
- **`R/tools/shared/rpcn_check/tests/test_rpcn_check.py`, `RealBinaryCommandsTest`:** one test per fact (fallback, switch on `errored()`, retry then fallback, batching count, dedupe). Run the binary on a temporary config with a `stdin` input and a `stdout` output, as the existing real-binary tests do. The `reject` output gives a failing output. Use small backoffs.
- **`R/SOURCES.md`:** one row per proved fact (connect `v4.100.0` with benthos `v4.76.0`, and `v4.117.0` with benthos `v4.84.0`), plus one row for `patterns.md`'s adapted text (source, commit `a4562333`, Apache-2.0).
- **`T/scenarios/`:** one single-step headless rpcn-design scenario per family:
  - `rpcn-design__pattern_dlq_retry`;
  - `rpcn-design__pattern_batching`;
  - `rpcn-design__pattern_idempotency`;
  - `rpcn-design__pattern_ordering`.

  Each has a subfolder and a non-default name, `[[report]] ready = true` on the note, and `[[file]] contains` on the note for the pattern's words and components. Add a `lacks` on a family the request didn't ask for (for example, no `dedupe` in the batching note). Add shipped-scenario tests.
- **`R/evals/README.md`:** the scenario count and cost (at 2 runs).

- **Review loop 1 (2026-11-21).** The first build was reverted. Its diffs are kept as `/tmp/claude-1000/-home-aleksejjurcenko-projects-clients-personal-rpcn-skills/e8f28587-8692-460b-9a36-56b1bb18132f/scratchpad/3.2-try1-R.patch` and `/tmp/claude-1000/-home-aleksejjurcenko-projects-clients-personal-rpcn-skills/e8f28587-8692-460b-9a36-56b1bb18132f/scratchpad/3.2-try1-T.patch`, for reference only; re-derive from this plan.
  - **Keep from the first build:**
    - the five real-binary tests and how they're built (stdin/stdout, `logger.level: none`, batching through `broker`, `pipeline.threads: 1` for dedupe, and `fallback_error` after `retry` asserted only as set);
    - the SOURCES rows and the adapted-text row;
    - `patterns.md`'s entry shape (When, Note, Components, Basis, an attribution line);
    - the four scenarios;
    - the user-requested runner change (sessions on the newest pin: `session_env` and `SessionBinaryTests`, with the README note).
  - **Fix these** (review findings):
    1. **Default DLQ:** per the decision above, a `[non-blocking]` pick. Patterns 3 (retries) and 2 (processing errors) apply only when the request asks for them. Add a plain-copy scenario: the default-DLQ pick present, and no `| retry |`, `| switch |` or `| dedupe |` rows.
    2. **Batching:** the entry mentions joining a batch into one payload with a batch processor (such as `archive`), when `fields` lists `batching.processors` for that output. The SOURCES batching row claims only what its test proves (`broker`'s batching block). That the same block exists on another output is read from `fields` at run time.
    3. **Step order:** `SKILL.md` reads `patterns.md` before Steps 3–4 (picking components and checking fields), so each pattern's Components rows are picked and checked there.
    4. **`note-writing.md` intro:** a behaviour may also come from a `patterns.md` entry's Basis (its SOURCES row).
    5. **Field names:** each pattern names a field (`max_retries`, `batching.count`, `max_in_flight`) only when `fields` lists it for that component, else it states the value as intent. Make pattern 4's Note and Components agree.
    6. **Ordering:** the entry records the ordering requirement as intent, and names `max_in_flight` as the field that limits parallel batches (its `fields` description). It doesn't claim the field guarantees order.
    7. **Scenario checks:** `contains` checks Components-row strings (`| retry |`, `| fallback |`, `| switch |`, `| dedupe |`, a `| cache |` row), not bare words. Batching, idempotency and ordering get `lacks` on `| retry |` and `| switch |` when their request didn't ask for them.
    8. **Runner shims:** resolve the session binary to an absolute path (`shutil.which` for a bare name). For an `rpk` binary, `redpanda-connect` runs `<rpk> connect …`, and the `rpk` shim passes through. Write the shims per run (`<transcript stem>.shims/`), or atomically (a temp file, then rename), so parallel runs never see an empty script. Add tests for both.
    9. **Pin order:** the README and the `session_binary` docstring say the last `RPCN_TEST_BINARIES` entry is the session's binary, so list the floor first (`run_evals.py` does).

## Tasks & Acceptance

**Execution:**
- [x] The five real-binary fact tests and their SOURCES.md rows, proved on 4.100.0 and 4.117.0.
- [x] `patterns.md`, `note-writing.md` and the `SKILL.md` pointer, plus the SOURCES row for the adapted text.
- [x] The four T scenarios, their shipped tests, and the README counts.
- [x] Smoke: the four new scenarios and `rpcn-design__chain_tracer` at `--runs 1` on both binaries, then every non-compare scenario once. Record the results in Implementation Notes.

**Acceptance Criteria:**
- Given the repo, when the validator, `sync_shared --check`, all `tools/` suites, `rpcn_check` on both binaries and T's tests run, then all pass, and every pattern in `patterns.md` cites a proved row or a `fields` value.
- Given the smoke run, when it finishes, then every scenario passes, and each family's note names its pattern and lacks the ones it wasn't asked for.
- Given the reviewed, committed tree, when `run_evals.py` runs (2 runs, about $33), then it passes, and a `dirty: false` record is committed.

## Implementation Notes

- **First build (reverted 2026-11-21 at review loop 1); its notes follow, for history only.**

- **Facts (`RealBinaryCommandsTest`):** `test_pattern_fallback_sends_a_failed_write_on`, `test_pattern_switch_on_errored_routes_processing_failures`, `test_pattern_retry_then_fallback`, `test_pattern_batching_count`, `test_pattern_dedupe_drops_a_seen_key`, through a shared `_run_pattern` helper (stdin in, stdout out, `rpcn_check run`, no broker). Findings while proving them: a wrapper output (`fallback`, `switch`, `broker`) around `stdout` sends the logs to stdout too, so the configs set `logger.level: none`, and the retry test logs to a file to count attempts (`max_retries: 2` gives 3 `Failed to send message` lines); `stdout` has no `batching`, so batching is proved on `broker`'s batching policy with an `archive` batch processor; `dedupe` needs `pipeline.threads: 1` for "the first is kept" to be deterministic. After a `retry`, `fallback_error` is the retry's own error, not the inner one, so the test asserts only that it is set. Full suite on 4.100.0 and 4.117.0: 192 passed.
- **SOURCES.md:** five behaviour rows (one per fact, both pins) and one row for the text adapted from `redpanda-data/skills` patterns 6, 2, 4, 5, 9 at `a4562333`, Apache-2.0. Left out as unproved: `auto_replay_nacks`, `batching.period`, `drop_on_err`, a `redis` cache TTL. Ordering has no row: it cites the `max_in_flight` description from `fields`.
- **rpcn-design:** new `references/patterns.md` (six entries: When, Note, Components, Basis; closing attribution line; "state no behaviour beyond an entry's Basis"). `note-writing.md` points sections 5 to 8 at it and replaces 3.1's minimal pattern, keeping the intent wording for destinations. `SKILL.md` Step 5 names `references/patterns.md`: 4,769 characters. Validator: no warnings for the three skills; `sync_shared --check` clean; `tools/tests skills` 146 passed.
- **T:** `rpcn-design__pattern_dlq_retry` (`relay/order_post`, both DLQ paths and retries), `__pattern_batching` (`archive/click_archive`), `__pattern_idempotency` (`dedup/event_clean`), `__pattern_ordering` (`ordered/customer_orders`), each with `[[report]] ready = true`, `[[file]] contains`/`lacks` and no YAML. `ShippedDesignTracerScenarioTests.test_pattern_scenarios` added. T tests: 359 passed, 3 skipped.
- **Smoke 1** (`runs/20261121-125225`, the four plus `chain_tracer`): chain tracer, idempotency and ordering PASS; batching and dlq_retry FAIL on `lacks "dedupe"` only: the notes said "no `dedupe` is added" and "readers of the archive dedupe if needed". Plan change: `lacks` checks for a `dedupe` Components row (`| dedupe |`, `` | `dedupe` | ``), not the word. The dlq_retry note also claimed how `http_client`'s own `retries` add up with `retry`, which no row proves, so `patterns.md` now says to state no behaviour beyond the Basis.
- **Smoke 2** (`runs/20261121-125915`, all 9 `rpcn-design__*`): 9/9 PASS. Notes checked by hand: each names its pattern and its components; families not asked for are `None.`. Every note still adds a DLQ with `retry`/`fallback` (3.1's Error handling rule picks one when the request names none).
- **Smoke 3** (`runs/20261121-130234`, all 44 non-compare scenarios once, $14.71): 44/44 PASS.
- **evals/README.md:** 44 pass scenarios, about $34 at 2 runs.
- **Not done here:** review, commit, and the `run_evals.py` record (AC 3).
- **User request during the build (2026-11-21), outside the Code Map:** skill sessions now run on the newest pin. In T's `run_scenarios.py`, `session_env` sets `RPCN_BINARY` to the last `RPCN_TEST_BINARIES` entry, and a PATH shim makes `rpk connect` and `redpanda-connect` run it, for arm-neutral comparisons. It has tests (`SessionBinaryTests`) and a README note. Smoke on that change: all 9 `rpcn-design__*` scenarios passed on both binaries (`T/runs/20261121-131202`). The notes Design wrote now record `rpcn_version: 4.117.0` instead of PATH's 4.112.0.

- **Rebuild (review loop 1, 2026-11-21).** Started from the kept parts of the first build (the patches), then fixes 1–9:
  1. `patterns.md` pattern 1 always applies unless the request drops or only logs failures; with no destination named, the default DLQ is written as `[non-blocking] Where do failed messages go? Picked: <DLQ> — the request named none.`, and the note stays ready. Patterns 2 and 3 apply only when the request asks (`note-writing.md` Error handling and Patterns say the same). New T scenario `rpcn-design__pattern_default_dlq` (`copy/payment_mirror`, a plain copy): contains `payments.dlq`, `[non-blocking]`, `| fallback |`; lacks `| retry |`, `| switch |`, `| dedupe |`, `batching.count`, `max_in_flight: 1`.
  2. Batching entry: an `archive` batch processor (with its own row) joins a batch into one payload when `fields` lists `batching.processors`. SOURCES batching row now claims only `broker`'s block (`batching.count` and an `archive` in `batching.processors`); other outputs are read from `fields`.
  3. `SKILL.md` Step 3 starts "First read `references/patterns.md`"; Step 5's mention removed. 4,790 characters.
  4. `note-writing.md` intro: a behaviour may also come from a `patterns.md` entry's Basis (its SOURCES row).
  5. `patterns.md` has one rule for field names (only when `fields` lists them, else intent), and patterns 3, 4 and 6 follow it; pattern 4's Note and Components agree.
  6. Ordering: the order is written as intent; `max_in_flight: 1` is recommended with its `fields` description as the reason, with no claim that it guarantees order. The example description is `http_client`'s, as 4.112.0 to 4.117.0 print it.
  7. Scenario `contains` check Components rows (`| retry |`, `| fallback |`, `| switch |`, `| dedupe |`, `| cache |`, `| http_client |`, `| aws_s3 |`); batching, idempotency and ordering lack `| retry |` and `| switch |`. `ShippedDesignTracerScenarioTests.PATTERNS` covers all five.
  8. `run_scenarios.py`: `session_binary` resolves to an absolute path (`shutil.which` on the env's PATH for a bare name, None when not found). `write_binary_shims` writes per run (`<transcript stem>.shims/`) and atomically (`mkstemp`, then `os.replace`), quotes the binary with `shlex.quote`, and for an `rpk` pin makes `redpanda-connect` run `<rpk> connect …` with `rpk` passing through. A non-rpk pin's `rpk` falls through to the real rpk, which it resolves when it writes the shim, not with `sed` on PATH. Tests: `SessionBinaryTests` (7, including bare-name resolution, rpk pin, fall-through, per-run and rewritten shims).
  9. T README and the `session_binary` docstring: the **last** `RPCN_TEST_BINARIES` entry is the session's binary, so list the floor first, as `tools/run_evals.py` does.
- **Checks:** `rpcn_check` tests on 4.100.0 and 4.117.0: 192 passed (the five pattern facts included). Validator: no warnings for the three skills. `sync_shared --check` clean. `tools/tests skills`: 146 passed. T tests: 366 passed, 3 skipped. `rpcn_check binary` OK on both pins.
- **Smoke A** (`T/runs/20261121-133343`, five `rpcn-design__pattern_*` plus `chain_tracer`, `--runs 1`, both pins): 6/6 PASS. Notes checked by hand: the plain copy has `fallback` to `payments.dlq` as a `[non-blocking]` pick, no retry/switch, and `None.` in the other sections; ordering states the order as intent and gives `max_in_flight: 1` with its description; batching gives `batching.count: 100` and an `archive` row.
- **Smoke B** (`T/runs/20261121-133718`, all 45 non-compare scenarios once, both pins): 45/45 PASS, about $14.54.
- **evals/README.md:** 45 pass scenarios, about $34 at 2 runs.
- **Not done here:** review, commit, and the `run_evals.py` record (AC 3).
- **Second-pass fixes (2026-11-21):** all nine are in.
  - Pattern 1 says the kept error behind a `retry` is the retry's own error. This was proved on both pins: `fallback_error` is "message failed to reach a target destination", not the inner error.
  - `archive` with `format: lines` is proved beside `json_array`, and the batching row names only those two.
  - Pattern 5 proves only `memory`; another cache goes in as intent.
  - Pattern 6 quotes no description text.
  - A period-only batching request is written as intent.
  - The scenarios lack the backticked `retry` and `switch` rows, and `default_dlq` checks the pick line.
  - The runner writes shims for a preset `RPCN_BINARY`, and `_write_script` is tested for atomicity.
  - Smoke: all 10 `rpcn-design__*` scenarios passed on both pins (`T/runs/20261121-134827`).
  - Checks: the validator and `sync_shared` are clean, and R (146), `rpcn_check` on both pins (192) and T (369) pass.
- **First record run failed (2026-11-21, $37.72, 2 runs):** trigger accuracy was 1.0 and 43 of 45 scenarios passed 2/2. `rpcn-test__lint_broken` and `rpcn-test__samples_bug` were 1/2: rpcn-test ran `ls` on named reference files before reading them, which `bash_lacks` (story 2.13) flags. That is the habit deferred in 2.16, not this story. The failed record is kept at `/tmp/claude-1000/-home-aleksejjurcenko-projects-clients-personal-rpcn-skills/e8f28587-8692-460b-9a36-56b1bb18132f/scratchpad/2026-11-21-4eff486e7703.failed-141456.json`.
- **Fix (user, 2026-11-21: fix the skill, keep the check):** rpcn-test's `SKILL.md` References rule says to read each reference with Read, never `ls` or test for one (4,761 characters). Smoke: both scenarios passed 6 of 6 runs on both pins.

## Plan Change Log

- 2026-11-21: scenario `lacks` for a family the request didn't ask for check its Components row (`| dedupe |`), not the bare word, since a note may say a pattern is not used (smoke 1).

## Review Triage Log

Quick pass (first build): 0 high, 6 medium, 6 low, 1 false. One intent_gap (the default DLQ against "only the patterns the request calls for"), answered by the user and routed to a loop-back. The rest are folded into the rebuild as "Fix these" 2–9 in the Code Map. The false one is AC 3, the record, which comes after the commit.

**Review loop 1, second pass (2026-11-21):** 0 high, 4 medium, 5 low, 0 false. All nine route to patch. The rebuild fixed every first-pass item.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | Pattern 1 promises the sink's error in `fallback_error`, but behind a `retry` it holds the retry's error | medium | patch | The retry test only asserts it is set. Pattern 1 says the kept error is the retry's error when a `retry` is in the chain. |
| 2 | The batching row and pattern 4 claim `archive` joins a batch in general; only `format: json_array` is proved | medium | patch | Prove `format: lines` too on both pins, or narrow the claim to what is proved. |
| 3 | Pattern 5 allows a `redis` cache for `dedupe`; only `memory` is proved | medium | patch | Keep `memory` as the proved cache; another cache the request names goes in as intent, with no behaviour claim. |
| 4 | Pattern 6 quotes `max_in_flight`'s description as 4.112.0–4.117.0 print it | low | patch | Use the description Step 4 printed; no quoted text in the reference. |
| 5 | The `lacks` checks miss the backticked forms `` | `retry` | `` and `` | `switch` | `` | medium | patch | Add both forms, and assert them in `PATTERNS`. |
| 6 | `default_dlq` doesn't tie the pick to the DLQ | low | patch | Check the pick line, `Picked:` plus `payments.dlq`. |
| 7 | With `RPCN_BINARY` preset, the shims are skipped, so arms can run another version | low | patch | Write the shims for the preset binary too, and say so in the README. |
| 8 | The atomic-write test greps the source and never checks atomicity | low | patch | Test `_write_script` directly: no temp file is left behind, and the result is complete and executable. |
| 9 | A batching request with only a time window falls between the rules | low | patch | Section 8 and pattern 4 write a period-only request as intent, with no field. |

## Verification

**Commands:**
- `RPCN_TEST_BINARIES=<abs 4.100.0>:<abs 4.117.0> uv run --with pytest pytest -q tools/shared/rpcn_check/tests` — pass, including the five new tests
- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`, `uv run --with pytest pytest -q tools/tests skills` — pass
- `cd T && uv run --with pytest pytest -q tests` — pass
- `cd T && RPCN_TEST_BINARIES=… uv run run_scenarios.py --runs 1 --no-judge --scenario 'rpcn-design__*'` — all PASS
