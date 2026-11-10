---
title: 'Bloblang mappings come with samples, and Test runs them'
type: 'feature'
ticket: '7'
created: '2026-11-10'
status: 'built'
baseline_revision: 'c886d57ccf6573cc7fedbaf9edabd12a0d546ce3'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** a test report's `pass` today means only that the pipeline lints clean. A Bloblang mapping that parses but computes the wrong value passes. The report's Bloblang samples section always says `Not run`.

**Approach:**
- **`rpcn-author`:** writes each non-trivial mapping as `<name>.<label>.blobl` beside the pipeline. The pipeline loads it with `from`.
- **New format:** `tools/shared/formats/samples-format.md` defines `<name>.samples.json`, holding the input and expected output for each mapping.
- **`rpcn-test`:**
  - writes the samples file when there is none, with expected outputs taken from the mapping's intent, never from running it;
  - runs every sample with `rpcn_check blobl`;
  - reports each sample in the report's Bloblang samples section, with sample, expected and actual output for each mismatch;
  - fails the verdict on any mismatch;
  - proposes a diff to the `.blobl` file for Author to apply.

## Boundaries & Constraints

**Always:**
- **AD-6:** Author alone writes `.blobl` files. Test alone writes `<name>.samples.json`. Test never edits the pipeline or a `.blobl`.
- **Hashing:** each `.blobl` the pipeline loads is a hashed report input, so editing it makes the report stale. The samples file is not an input.
- **Expected values:** Test never changes an existing sample's expected value to match the actual output. A mismatch is reported, not "fixed" in the samples.
- **AD-15:** the path-resolution fact is proved by an `rpcn_check` test on both binaries, with a `SOURCES.md` row. Facts the binary can report are never restated in references.
- **Size:** `SKILL.md` files stay at 4,803 characters or less, so new behaviour goes in references. Shared files change only under `tools/shared/`, then `sync_shared.py` runs.
- **`test-report@1`:** stays at major 1. Adding `.blobl` inputs is additive.

**Never:**
- Samples for metadata, multi-message batches, or `branch`/`workflow` internals.
- A dry run of the pipeline (that's story 2.8).
- Changing an existing pipeline's inline mapping into a `.blobl` file unless a report proposes it.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Author, non-trivial mapping | A request needing a multi-line mapping | `<dir>/<name>.<label>.blobl` is written, the pipeline loads it, and lint is clean | — |
| Author, trivial mapping | A one-line `root = this` style mapping | Stays inline | — |
| Test, samples pass | A pipeline, its `.blobl`, and a correct `samples.json` | One `pass` row per sample, verdict `pass`, samples file unchanged | — |
| Test, deliberate bug | The same, with a wrong `.blobl` | A `fail` row with sample, expected and actual; verdict `fail`; a proposed diff to the `.blobl`; samples unchanged | — |
| Test, no samples file | A pipeline with a `.blobl` and no samples | `samples.json` is written and parses per the format, and every sample is run | — |
| Mapping doesn't parse | A broken `.blobl` | A `fail` row with the parse error, verdict `fail` | `blobl` exit 1 is a check failure, not `blocked` |
| A `.blobl` changes after the report | The report's `.blobl` hash no longer matches | `hash --check` reports not ready | — |

**Decisions (2026-11-10, user):**
- **`.blobl` path:** a pipeline loads its `.blobl` with a path from the project root, such as `from "./pipes/orders.enrich.blobl"`. On both binaries `from` resolves from the process's working directory, and the skills already run everything from the project root. Deploy (epic 5) handles the working directory.
- **Comparison:** samples are compared in `rpcn_check`, through `blobl <mapping> --samples <name>.samples.json`. It parses and validates the samples file, runs each sample for that mapping, compares outputs as JSON values, and returns a pass or fail result per sample with expected and actual. This is an additive change to AD-4's `blobl`, recorded in `SCHEMA.md`.
- **Scope:** only `.blobl` files get samples. Inline mappings are trivial by Author's rule.
- **Plan size:** the plan is kept whole, over the size guideline.

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`. `T` = `rpcn-test-skills`, local only, with baseline `32fafd1aa687f8c45087537e65bad66ae7e8b1d4`.

- **`R/tools/shared/rpcn_check/rpcn_check.py`:**
  - `blobl` per `SCHEMA.md` 247-300: `--input` gives one JSON document per line, and `results[]` holds `line`, `output` and `error`.
  - Add `--samples` and a `parse_samples()`, with tests in `tests/test_rpcn_check.py` (fake binaries and both real ones). A samples file that is invalid is exit 2, with an error naming the line or key. Each failed sample is exit 1.
  - Add one real-binary test: `from` resolves from the working directory.
- **New `R/tools/shared/formats/samples-format.md`:** the shape (`format: samples@1`, `pipeline`, `mappings: {<file>: [{name, input, output | deleted: true}]}`), the rules, the readiness list, and an example checked by the tests. It is synced into `rpcn-test` (and `rpcn-author`, if Author reads it).
- **`R/tools/shared/formats/test-report-format.md`:**
  - Header `inputs` gains "each `.blobl` file the pipeline loads".
  - The Bloblang samples section points at `samples-format.md`.
  - The example hashes stay valid.
- **`R/skills/rpcn-test/`:** `SKILL.md` (4,701 characters) gets a fenced `blobl` command and one step pointer. A new `references/samples.md` covers when to write samples, expected values from intent, never rewriting expected values, rows and diffs. `references/report-writing.md` stops saying `Not run` for samples. `shared.txt` gains the new format.
- **`R/skills/rpcn-author/`:** `SKILL.md` (4,801 characters, so a pointer only) and `references/pipeline-files.md` gain the `.blobl` rule: when a mapping is non-trivial (more than 3 lines), the file name, and the `from` path from the project root.
- **`R/SOURCES.md`:** a row for the `from` path fact, with source the benthos Bloblang import resolution at the version connect pins, and proof the new `rpcn_check` test.
- **`R/evals/`:** one trigger positive ("check my Bloblang mapping against its samples" for `rpcn-test`), plus README counts.
- **New `T/scenarios/`**, each with `no_cd` and `pipes/`:
  - `rpcn-test__samples_pass`: report ready, verdict `pass`, `unchanged` samples
  - `rpcn-test__samples_bug`: verdict `fail`; `[[file]]` report contains the expected and actual values; `unchanged` samples
  - `rpcn-test__samples_written`: the samples file exists and is valid per the format
  - `rpcn-author__write_blobl`: a `.blobl` exists, the pipeline contains `from "`, lint ok
- **`T/tests/test_run_scenarios.py`:** `NAMES` and the fixture tests for these.

## Tasks & Acceptance

**Execution:**
- [x] `R/tools/shared/rpcn_check/` (code, `SCHEMA.md`, tests) and `R/tools/shared/formats/` (`samples-format.md`, `test-report-format.md`), then `sync_shared.py`.
- [x] `R/skills/rpcn-test/` and `R/skills/rpcn-author/`, within the size limit.
- [x] `R/SOURCES.md` and `R/evals/` (case and README).
- [x] `T/scenarios/` (the four above) and `T/tests/test_run_scenarios.py`.

**Acceptance Criteria:**
- **Given** the repo, **when** the validator, `sync_shared --check`, all `tools/` suites and the `rpcn_check` tests on both binaries run, **then** all pass, and neither skill has a new warning.
- **Given** both binaries, **when** the new scenarios and the existing author and test scenarios smoke-run (`--runs 1 --no-judge`), **then** all pass.
- **Given** the reviewed, committed tree, **when** `run_evals.py` runs (about $20), **then** it passes and a `dirty: false` record is committed.

## Implementation Notes

- **`blobl --samples`:** mutually exclusive with `--input`. The samples file is parsed (`parse_samples`, duplicate JSON keys rejected) and its entry found by the mapping's file name before the binary is looked up, so a bad file is exit 2 with `binary` null. The samples run as one temp `--input` file through the unchanged `blobl` core (refactored into `_blobl_exec`). `data` adds `samples_file`, `samples[]` (`name`, `input`/`expected` as compact sorted-key JSON, `deleted`, `actual`, `error`, `result`), `passed` and `failed`; without `--samples` the shape is unchanged. Comparison is `json_equal` (`1 == 1.0`, `true != 1`); a non-JSON output compares as a raw string; an empty output counts as deleted. Recorded in `SCHEMA.md` as an additive `blobl --samples` section.
- **`mappings` keys are bare `.blobl` file names**, matched by basename. That lets Test verify a proposed `.blobl` fix on a temp copy with the same name against the real samples file.
- **test-report-format example:** its pipeline's mapping is inline (2 lines), so its Bloblang samples section is now `Not run: no .blobl file.` A failing-row illustration was added outside the example files. Header hashes are unchanged.
- **`samples-format.md`** is synced into `rpcn-test` only: Author never reads or writes samples, and `pipeline-files.md` says so.
- **SKILL.md sizes:** `rpcn-test` 4,794 characters (the description gains the samples job and the phrase "check my Bloblang mapping against its samples"; wording tightened elsewhere); `rpcn-author` 4,801 (a pointer in Step 5; "ask the user" became "ask", "no header or comment block" became "no comment block"). The validator reports only the pre-existing `rpcn-test` design-format warning.
- **`checks.tests`** in rpcn-test's status block now reports the samples (`pass`/`fail`/`skipped`), as AD-8's `tests` values allow.
- **SOURCES.md:** the `from` row cites benthos (MIT) at connect v4.100.0 (benthos v4.76.0) and v4.115.0 (benthos v4.84.0), read with `go version -m` on the cached binaries.
- **T:** the four scenarios and a `ShippedSamplesScenarioTests` class; `rpcn-author__write_blobl` joins `ShippedAuthorScenarioTests.NAMES`. `run_scenarios.py` is unchanged: `samples_written`'s "valid per the format" is shown by `checks.tests = pass` with verdict `pass` (the `blobl --samples` exit 0) plus `[[file]] contains`.
- **Smoke run 1 (new scenarios, both binaries):** 4/4 pass, $1.21 (`T/runs/20261110-110842`).
- **Smoke run 2 (all `rpcn-author__*`, `rpcn-test__lint_*`, `rpcn-test__npx_*`, `rpcn-test__compare_lint` with `--no-judge`, both binaries):** 18/18 pass, exit 0 (`T/runs/20261110-111123`).
- **Matrix audit follow-up (user's choice):** the report `[[file]] contains` in `rpcn-test__samples_pass` and `rpcn-test__samples_bug` gains `"- file: orders.enrich.blobl"`, so both scenarios prove the `.blobl` is a hashed report input. Both reports recorded it that way in smoke run 1. The shipped-scenario tests pin it. T's 196 tests pass, and `samples_pass` re-ran 1/1 on both binaries, $0.32 (`T/runs/20261110-112843`).
- **Review fixes:**
  - **Comparison:** an expected JSON string is compared with the raw output text, because the binary prints a string root without quotes (`root = "123"` prints `123`). Other values are parsed and compared as JSON. `NaN` and `Infinity` are rejected through a `parse_constant` sentinel, with the error naming the key.
  - **Real-binary proof:** `test_blobl_samples` adds a `facts.blobl` (string root, `deleted()`, `format_json()` text), with its own `SOURCES.md` row.
  - **Shared file:** the `from` fact moved to the shared `tools/shared/formats/blobl-files.md`, copied into both skills. Both skills' references now point to it, and the `SOURCES.md` row names it.
  - **samples.md §2–3:** exit 1 with no samples is now "the mapping didn't run", 1 failed. Counts are summed over the `.blobl` files. On exit 2, Test fixes its own file's shape once; if it still exits 2, that is a `fail` row, so the verdict is `fail`. Non-deterministic mappings are `Not run: non-deterministic (<function>)`.
  - **Author:** keeps clock, uuid and random values in a separate inline `mapping` (starting with `root = this`).
  - **Step 3:** the `blobl` command gains `[--env-file <file>]`.
  - **test-report-format:** the Bloblang samples columns keep the old `mapping` superset; `sample` and the `deleted` value are additive. The failing-row example now follows §3 and the samples-format example.
  - **SKILL.md sizes:** `rpcn-test` 4,800 characters, `rpcn-author` 4,792 (trimmed to name `references/blobl-files.md`).
  - **Tests and smoke runs:** `rpcn_check` tests pass on both binaries (169). The scenarios were not re-run after these fixes.
- **Not done here:** review, commits (R and T), and the paid `run_evals.py` (AC 3, about $20), which needs the reviewed, committed tree.
- **After the review patches:** the validator passes with no new warning (`rpcn-author` 4,792 characters, `rpcn-test` 4,800), and so do `sync_shared --check`, all four `tools/` suites, `rpcn_check` on both binaries, and T's 196 tests. Smoke run of 20 scenarios (all author scenarios, plus `rpcn-test__lint_*`, `npx_*` and `samples_*`): 20/20 pass on both binaries (`T/runs/20261110-113938`).

## Plan Change Log

## Review Triage Log

Quick pass: 0 high, 3 medium, 9 low, 0 false, 0 maybe-false.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `compare_sample` parses a string output as JSON, so `"123"` fails | medium | patch | On both binaries `root = "123"` and `root = 123` both print `123`. An expected string is now compared with the raw text, with tests on the real binaries. |
| An invalid samples file the run didn't write gives `Not run`, so the verdict passes | medium | patch | Test fixes its own file's shape once. If it still exits 2, the result is a `fail` row and `checks.tests` is `fail`. |
| Mappings using `now()` or `uuid_v4()` can't be sampled, and the `write_blobl` prompt asks for one | medium | patch | Author keeps such values in a separate inline mapping. Test marks any that remain `Not run: non-deterministic`. |
| The deleted and raw-string output facts have no proof on the real binaries (AD-15) | low | patch | `test_blobl_samples` now covers them, with a `SOURCES.md` row. |
| The `from` fact is stated in two skill-owned files (AD-15) | low | patch | It moved to the shared `formats/blobl-files.md`, synced into both skills. |
| Summary shows "0 failed" for a mapping that doesn't parse, and counts aren't summed | low | patch | A mapping that didn't run counts as 1 failed, and counts are summed over files. |
| Exit 1 with no samples is labelled a parse error | low | patch | It is now labelled "the mapping didn't run (`errors[0]`)". |
| The `blobl` command drops `--env-file` | low | patch | Added, with the same rule as lint. |
| The samples columns narrowed `test-report@1` | low | patch | `mapping` keeps the superset, and `sample` and `deleted` are described as additive. |
| The format's example row doesn't follow `samples.md` §3 | low | patch | Fixed. |
| `parse_samples` accepts `NaN` and `Infinity` | low | patch | Rejected through `parse_constant`, with a test. |
| `samples_written` validity rests on the model's own status | low | defer | The runner has no samples-file check, a gap that predates this story. Logged in `deferred-work.md`. |

## Design Notes

- **Why expected values come from intent:** if Test derived them by running the mapping, every sample would pass by construction. They come from the request, the design note, or what the mapping's name says it should do. When intent is unclear, the sample goes in `open_questions` instead.

## Verification

**Commands:**
- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`, every `tools/tests` suite, and `rpcn_check` tests with `RPCN_TEST_BINARIES`: all pass.
- In `T`: `uv run tests/test_run_scenarios.py`, then the smoke run in the AC.
