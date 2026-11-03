---
title: 'rpcn_check blobl, list, fields, run and test'
type: 'feature'
ticket: '8'
created: '2026-10-30'
status: done
baseline_revision: '050ba1c15265ace2c33c70c18765072a6ab8ed61'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md', '{project-root}/tools/shared/rpcn_check/SCHEMA.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `rpcn_check` has `binary`, `lint` and `hash`, but AD-4 also promises `blobl`, `list`, `fields`, `run` and `test`. Without them, epic 2's Author and Test skills can't check Bloblang against samples, check component fields against the installed binary (R2), dry-run a pipeline, or run `rpk connect test` cases.

**Approach:** Add the five subcommands to `tools/shared/rpcn_check/rpcn_check.py`. Each one prints the schema-1 envelope, uses the existing lookup and binary-version floor, and uses exit codes 0, 1 and 2. Each is covered by fake-binary tests and by real-binary tests on 4.100.0 and 4.115.0, which already run in CI.

## Boundaries & Constraints

**Always:**
- **The five subcommands:**
  - **`blobl <mapping> [--input <file>] [--env-file <file>]`**
    - **How it runs:** `blobl [--env-file f] --file <mapping> [--input <file>]`, with stdin empty when there's no `--input`. The input is one JSON document per line.
    - **Data:** `{"mapping", "results": [{"line": int, "output": str|null, "error": str|null}]}`. stdout holds one output per input line that succeeded, and stderr holds one `failed to execute map: …` per line that failed (verified). Results are matched to input lines in order.
    - **Exit 1:** the mapping doesn't parse (stderr `failed to parse mapping: line L char C: <msg>`, turned into an error with `file` set to the mapping and its line and column), or any line failed.
    - **Exit 0:** every line succeeded.
  - **`list <category> [--status stable|beta|experimental]`**
    - **How it runs:** `list --format json [--status s] <category>`.
    - **Data:** `{"category", "components": [names]}`. `category` must be one of the top-level keys of `list --format json` with no argument (for example `inputs`, `processors`, `outputs`, `caches`, `bloblang-functions`). An unknown category exits 2.
  - **`fields <category> <component>`**
    - **How it runs:** `list --format json-full <category>`. It finds the component by `name` and flattens its `config.children` tree into dotted `path`s, with array elements as `path[]`.
    - **Data:** `{"category", "component", "status", "fields": [{"path", "type", "kind", "required", "default"?, "advanced", "deprecated", "secret", "description"}]}`.
      - `required` is true when there's no `default` and no `is_optional`.
      - The flags are true only when their `is_*` key is present and true, because json-full leaves them out otherwise (verified).
      - `description` is the first line of the description.
    - **Exit 1:** the component doesn't exist in that category. The error says so, and `data.components` holds the close matches by prefix.
  - **`run <config> [--input <file>] [--resources <file>]... [--env-file <file>] [--timeout <s>]`** (default timeout 10 s)
    - **How it runs:** `run --set http.enabled=false` (AD-4), then resources, then env file, then the config. `--input` is passed as stdin; with no input, stdin is empty.
    - **Data:** `{"config", "outputs": [stdout lines], "exit": int}`.
    - **Exit 1:** a non-zero exit. Each stderr line `Config lint error … lint="<file>(<l>,<c>) <msg>"` becomes a file error. Any other non-zero exit becomes an error carrying the stderr tail.
    - **Exit 2:** a timeout. The outputs collected so far are kept, and the error says `timed out after <s>s`.
    - **Exit 0:** the binary exits 0.
  - **`test <target> [--resources <file>]... [--env-file <file>]`**
    - **How it runs:** `test [--resources f]... [--env-file f] <target>`, where the target is a config or a `<name>_benthos_test.yaml`. The default suffix was confirmed on both versions: `test p_benthos_test.yaml` runs the cases against `p.yaml`.
    - **Parsing:** ANSI escapes are stripped (they appear even with `NO_COLOR=1`). The output is parsed into `{"targets": [{"file", "passed"}], "failures": [{"target", "case", "line": int|null, "message"}], "passed": int, "failed": int}`, from the verified text: `Test '<f>' failed` / `--- <f> ---` / `<case> [line N]:` followed by indented detail lines. The success text is to be verified by the implementer on both versions.
    - **Exit codes:** 0 when every test passes; 1 when any case fails, a target fails to initialise (`Failed to execute test target …`), or `No tests were found`; 2 as usual.
- **Shared behaviour:**
  - **Files first:** every file argument (`--input`, `--resources`, `--env-file`, the mapping, config and target) is checked before the binary runs. A missing file exits 2 and names the file.
  - **Glob escaping:** targets and resources are escaped as in `lint`.
  - **Bounded runs:** every run except `run` has a 60 s timeout, and timeouts kill the process group.
  - **Decoding:** UTF-8 with `errors="replace"`, as in `lint`.
- **No copying:** this story copies nothing from the `redpanda-data/connect` plugin.
  - **Decision (planning, 2026-10-30):** the planned per-file licence check of `format-component-fields.py` and `format-bloblang.py` found no licence header in either file, and no root `LICENSE` in that repo. The repo mixes Apache-2.0 and RCL, so their licence can't be confirmed.
  - **Consequence:** the fields and Bloblang logic are written independently from `json-full` and the `blobl` CLI, and `SOURCES.md` is unchanged.
- **`SCHEMA.md`:** a section for each new subcommand, with its arguments, data shape and exit codes.
- **The skill copy:** re-synced with `uv run tools/sync_shared.py`.
- **Tests:** fake-binary tests for every matrix row. The real-binary tests also cover each subcommand on every path in `RPCN_TEST_BINARIES`. They use new fixtures in `tests/fixtures/`: `double.blobl`, `bad.blobl`, `samples.jsonl` with a bad line, `stdin_pipeline.yaml`, and `stdin_pipeline_benthos_test.yaml` with one passing case and one failing case.

**Never:**
- changing `binary`, `lint` or `hash`
- using any flag AD-4 forbids (`-v`, `--verbose`, `-`, `--chilled`)
- running `rpk connect install`
- changing `skills/rpcn-test/SKILL.md` (epic 2 uses these subcommands)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| blobl ok | `double.blobl` and a 1-line sample | exit 0, one result with an output | — |
| blobl bad line | a sample containing `notjson` | exit 1, that line's `error` set, the other lines' outputs kept | — |
| blobl bad mapping | `bad.blobl` | exit 1, an error with the mapping file, line and column | — |
| list | `list inputs` | exit 0, includes `generate` and `stdin` | — |
| list bad category | `list nope` | exit 2 | — |
| fields known | `fields inputs generate` | exit 0, `mapping` required, `interval` with its default | — |
| fields nested | a component with object children | dotted paths such as `tls.enabled` | — |
| fields unknown | `fields inputs nope` | exit 1, "not found" | — |
| run ok | `stdin_pipeline.yaml` with an input file | exit 0, the outputs | — |
| run lint error | a config with a lint error | exit 1, a file error parsed from the log | — |
| run timeout | a never-ending pipeline, `--timeout 2` | exit 2, `timed out` | — |
| test pass/fail | the test file with one failing case | exit 1, `failed: 1`, a failure naming the case and line | — |
| test none | a target with no tests | exit 1, "No tests were found" | — |
| missing file | any file argument | exit 2, the binary not run | — |

</frozen-after-approval>

## Code Map

- **`tools/shared/rpcn_check/rpcn_check.py`** (663 lines):
  - **Reuse:** `require_binary`, `_envelope`, `_emit`, `_error`, `escape_glob`, `_run_bounded` (process group, decoding), `_unique`, the files-first pattern in `cmd_lint`, `_Parser` and the subparser registration around lines 621–630.
  - **Add:** `cmd_blobl`, `cmd_list`, `cmd_fields`, `cmd_run` and `cmd_test`, with their parsers.
- **Verified binary behaviour** (2026-10-30, 4.100.0 and 4.115.0, which behave the same):
  - **`blobl --file`** prints the output lines on stdout and `failed to execute map: …` per failed line on stderr. It exits 0 even when lines fail, and exits 1 when the mapping doesn't parse (`failed to parse mapping: line 2 char 1: required: expected query` plus a caret block). Options: `--input`, `--env-file`, `--raw`, `--pretty`.
  - **`list --format json`** gives `{"inputs": [...], …}`.
  - **`list --format json-full inputs`** gives `{"version", "date", "docs_format", "config", "buffers", "caches", "inputs", …}`. Each component has `name`, `type`, `status`, `config.children[]`, and each child has `name`, `type`, `kind`, `description`, `examples`, plus `default`, `is_advanced`, `is_deprecated`, `is_secret` or `is_optional` only when set.
  - **`run --set http.enabled=false`** on a stdin pipeline with input piped in prints the output and exits 0. Lint errors go to stderr as `level=error msg="Config lint error" lint="p.yaml(5,28) …"`, with exit 1.
  - **`test <x>_benthos_test.yaml`** targets `<x>.yaml`. On failure it prints `Test 'p.yaml' failed`, `Failures:`, `--- p.yaml ---`, then `<case> [line 8]:` and the detail, with ANSI colours even under `NO_COLOR=1`, and exits 1. An initialisation failure prints `Failed to execute test target '<f>': …` and exits 1. `test ./` prints `No tests were found` and exits 1.
- **Tests:** `tools/shared/rpcn_check/tests/test_rpcn_check.py` has the `CheckTestBase` fake-binary helpers and `RealBinaryLintTest`. Add the new classes there.
- **CI** already runs that file with `RPCN_TEST_BINARIES` on both versions, so it needs no change.
- **Eval record:** syncing changes `skills/rpcn-test/scripts/rpcn_check.py`, so the skills hash changes. A new `run_evals.py` record is required before CI goes green (story 11).

## Tasks & Acceptance

**Execution:**
- [x] `tools/shared/rpcn_check/rpcn_check.py` -- the five subcommands per the Boundaries -- the AD-4 adapter completed
- [x] `tools/shared/rpcn_check/tests/fixtures/` -- the new fixtures (our own) -- real-binary inputs
- [x] `tools/shared/rpcn_check/tests/test_rpcn_check.py` -- fake-binary tests for every matrix row, plus real-binary tests per subcommand -- R2 evidence
- [x] `tools/shared/rpcn_check/SCHEMA.md` -- the new sections -- the contract
- [x] `skills/rpcn-test/scripts/rpcn_check.py` -- re-synced -- skill copy
- [x] (orchestrator) `uv run tools/run_evals.py`, then commit the record -- CI green under story 11

**Acceptance Criteria:**
- Given `RPCN_TEST_BINARIES` set to the fetched 4.100.0 and 4.115.0, when the test script runs, then every new real-binary test passes on both, including `run`'s timeout and `fields inputs generate`.
- Given a push, when CI runs, then the drift check, the record check and the tests on both versions are green.

## Implementation Notes

Decisions where the Boundaries left room (all documented in `SCHEMA.md`):

- **blobl ordering:** stderr is merged into the stdout pipe so each line's output or `failed to execute map:` stays in input order. String outputs can span several lines (verified: `root = "a\nb"` prints two lines), so when the printed line count differs from the input line count, each input line is re-run alone on stdin, inside the same 60 s budget. `error` is the message without the `failed to execute map: ` prefix. A deleted message is `output: ""`.
- **test counts:** `passed`/`failed` count targets, because passing cases are only printed with `-v`, which AD-4 forbids. An init failure marks its target failed and adds an error; it is not a `failures` entry. stdout and stderr are parsed separately (init failures go to stderr).
- **test success text** verified on 4.100.0 and 4.115.0: `Test '<f>' succeeded`, exit 0. `<f>` is relative or absolute as the target was given.
- **Glob escaping:** verified that `test` targets and `--resources` are globbed (escaping works) but the `run` config is not (`run 'g\[1\].yaml'` fails to open), so the run config and blobl mapping are passed unescaped.
- **fields paths:** array children `a[].b`, 2D arrays `a[][].b`, maps `a.*.b`; a root config of kind array (`switch`, `group_by`) prefixes `[].`. `config` is rejected as a category. Close matches: names sharing at least the first 3 characters, longest shared prefix first.
- **run:** `exit` is `null` on timeout; lint errors are parsed from the logfmt `lint="…"` value (escapes decoded); otherwise the last 10 non-empty stderr lines. Output order is the binary's (4.100.0 printed `{"doubled":6}` before `{"doubled":2}` once), so real-binary tests check membership, not order.
- **Fixtures:** the never-ending pipeline for the timeout test is written to a temp dir inside the real-binary test, not added as a fixture.

## Plan Change Log
- **Orchestrator verification (2026-10-30), after the review fixes:**
  - **Tests:** 133 pass with `RPCN_TEST_BINARIES` set to 4.100.0 and 4.115.0, and the drift check is green.
  - **Evals:** `run_evals.py` gave trigger accuracy 1.0 and `rpcn-test__lint_broken` PASS 3/3. Record `evals/results/2026-10-30-83f54a3fa504.json`, $4.20.
  - **Record check:** exit 0.
  - **Architecture:** AD-4 amended so `fields` reads `json-full`.

## Review Triage Log

**Pass 1 (quick):** 5 → patch, 2 rejected.

| # | Finding | Verdict | Route | Evidence |
|---|---|---|---|---|
| 1 | The `blobl` fallback's budget starts after the first run, so a call can take about 120 s | low | patch | It breaks the 60 s bound in the Boundaries and SCHEMA.md. The fix moves the start time. |
| 2 | `fields` leaves `status` and `fields` out of `data` on error paths | low | patch | The other subcommands start `data` in full shape, as SCHEMA.md's shared rule requires. |
| 3 | `list`/`fields` don't validate the category against the unfiltered key list | medium | patch | `list <valid> --status <s>` with an empty result is wrongly reported as an unknown category. |
| 4 | `blobl`'s silent non-zero exit gives 1, not 2 | low | patch | That goes against the shared exit-code table, and `lint` and `test` give 2. |
| 5 | Matching outputs by position can drift when an extra stderr line coincides with a line that prints nothing | low | reject | It needs two unlikely events together. The count check already sends most mismatches to the per-line fallback. |
| 6 | The fallback's per-line runs ignore their return code | medium | patch | A crashed per-line run is recorded as a success. |
| 7 | The CI-green acceptance criterion isn't met by the diff (no eval record) | low | reject (false) | The record is the orchestrator's task, after review. |

## Verification

**Who runs what:** the implementer runs the unit tests, with and without `RPCN_TEST_BINARIES`, and the drift check. The orchestrator runs `run_evals.py`, about $4.30, with live progress, then commits the record.

**Commands:**
- `B=$(uv run tools/fetch_rpcn.py | python3 -c 'import json,sys;print(":".join(json.load(sys.stdin)))'); RPCN_TEST_BINARIES=$B uv run tools/shared/rpcn_check/tests/test_rpcn_check.py` -- expected: all pass, none skipped
- `uv run tools/sync_shared.py --check` -- expected: exit 0
- `uv run tools/run_evals.py && uv run tools/eval_record_check.py` -- expected: exit 0
