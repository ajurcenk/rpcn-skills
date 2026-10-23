---
title: 'Hand-off formats and the hash check'
type: 'feature'
ticket: '4'
created: '2026-10-23'
status: done
baseline_revision: 'bb8ee06ab91a3d4a51c0e0c26770f9dc1ea83ecc'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md', '{project-root}/tools/shared/rpcn_check/SCHEMA.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Skills hand work to each other only through files (AD-6, AD-7), but no format defines those files, and nothing can tell that a hand-off has gone stale. For example, a test report can still say `ready` after its pipeline has changed.

**Approach:** Write three shared format documents in `tools/shared/formats/`, synced into `rpcn-test`:
- the hand-off header and readiness rules
- the design-note format
- the test-report format

Then add `rpcn_check.py hash`. It returns file hashes, and with `--check <hand-off file>` it reads the file's header, compares each recorded input hash with the current file, and reports the result. Skills don't hash in prose.

## Boundaries & Constraints

**Always:**
- **Header syntax:** the header is YAML frontmatter in a strict subset that `rpcn_check` parses with the standard library only:
  - one `key: value` per line for `artifact`, `format`, `pipeline`, `status`, `produced_by`, `rpcn_version` and `updated`
  - `inputs:` followed by block items of exactly `  - file: <path>` and `    sha256: <64 hex>`
  - `file` paths are relative to the hand-off file's folder

  The header doc gives a complete example.
- **`hash <file>...`** returns `data: {"hashes": [{"file", "sha256"}]}` with exit 0. A missing file exits 2 and names the file.
- **`hash --check <handoff.md>`** returns `data: {"artifact", "status", "format", "format_known": bool, "inputs": [{"file", "recorded", "current", "state": "match"|"changed"|"missing"}], "ready": bool}`.
  - `ready` is true only when every input matches, `status` is `ready` and `format_known` is true.
  - Exit codes: 0 when ready, 1 when not ready, 2 when the file is missing or its header can't be parsed (the error gives the line number).
- **Known formats:** `rpcn_check` holds the table `KNOWN_FORMATS = {"design": 1, "test-report": 1}`. A format is known when its artifact is in the table and its major equals the table's value. Later epics add entries next to their own format docs.
- **Neither mode needs the Redpanda Connect binary.** `binary` in the envelope is `null`.
- **`design-format.md`** follows AD-7:
  - the 11 sections in order
  - the Deviations table (section, what, why, date, resolved)
  - who may edit what
  - the Ready rule
  - a readiness list the reader checks
  - a filled example
- **`test-report-format.md`** has these sections:
  - Summary
  - Lint (the error table from `rpcn_check lint`)
  - Bloblang samples
  - Unit tests
  - Design check (`mismatch` or `deviation-recorded` per AD-7)
  - Proposed changes (diffs for Author, AD-6)

  It also gives its readiness list and a filled example. Its `inputs` are the pipeline YAML plus any resources files and design note used. Sections that didn't run say "not run".
- **Format versions:** each format doc states its `format` line, for example `test-report@1`, and says that a breaking change bumps the major.
- **Syncing:** `skills/rpcn-test/shared.txt` adds all three docs as `references/handoff-header.md`, `references/design-format.md` and `references/test-report-format.md`, and `sync_shared.py --check` stays green.
- **Copies:** the skill copy of `rpcn_check.py` is re-synced, not hand-edited.

- **Decision (user, 2026-10-23), option B:** a test report's `status: ready` means the run is complete. Pass or fail is the separate `**Verdict:** pass|fail` line. `hash --check` also returns `data.verdict` (`pass`, `fail` or null) and `data.pipeline_ready`, which is true only when the report is ready, its pipeline input matches and the verdict is `pass`. A pipeline counts as ready only when `pipeline_ready` is true.

**Never:**
- full YAML parsing or a third-party library
- changing `binary` or `lint`
- editing `skills/rpcn-test/SKILL.md` (story 5)
- capacity, deploy, tune or migration formats (later epics)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Hash files | two existing files | exit 0, one sha256 each, in the order given | — |
| Hash missing | a path that does not exist | exit 2, error names it | — |
| Fresh report | a `ready` test report whose input hash matches the pipeline | exit 0, `ready:true`, input state `match` | — |
| Stale report | the same report after the pipeline YAML changed | exit 1, `ready:false`, state `changed`, with recorded and current hashes | — |
| Input deleted | the recorded input no longer exists | exit 1, state `missing` | — |
| Draft | `status: draft`, all inputs match | exit 1, `ready:false` | — |
| Unknown major | `format: test-report@2` | exit 1, `format_known:false` | — |
| Unknown artifact | `artifact: capacity` | exit 1, `format_known:false` | — |
| No inputs | a header with no `inputs` items | readiness depends on status and format only | — |
| Bad header | no frontmatter, a malformed `inputs` item or a bad hash | exit 2, error gives the line | — |
| Relative paths | an input listed as `pipe.yaml`, with `--check` run from another folder | resolved against the hand-off file's folder | — |

</frozen-after-approval>

## Code Map

- **`tools/shared/rpcn_check/rpcn_check.py`:** reuse `_envelope`, `_emit`, `_error`, `_Parser`, the exit constants and the subparser pattern. Add `cmd_hash` and a small `parse_handoff_header()`. `require_binary` is not called.
- **`tools/shared/rpcn_check/SCHEMA.md`:** add a `hash` section with both modes.
- **`tools/shared/rpcn_check/tests/test_rpcn_check.py`:** add hash tests using temporary files and the existing envelope assertions.
- **`skills/rpcn-test/shared.txt`:** append the three format mappings. `tools/sync_shared.py` copies them, so run it after writing the docs.
- **`.github/workflows/ci.yml`:** no change needed. The drift check and the `rpcn_check` tests already cover the new files and tests.
- **Sources for the rules:** the ARCHITECTURE-SPINE's AD-6 (header fields, readiness, one writer, proposed diffs) and AD-7 (design sections, deviations, test check). The docs restate those rules for skill readers and add the syntax and examples.

## Tasks & Acceptance

**Execution:**
- [x] `tools/shared/formats/handoff-header.md` -- the header fields and strict syntax, the status lifecycle (draft → ready → superseded), the readiness rules, how to compute and check hashes with `rpcn_check.py hash`, and a full example -- the contract every hand-off follows
- [x] `tools/shared/formats/design-format.md` -- `design@1`: the AD-7 sections, the Deviations table, edit rights, the Ready rule, the readiness list and an example -- the Design to Author contract
- [x] `tools/shared/formats/test-report-format.md` -- `test-report@1`: the sections, the inputs, the readiness list and an example -- what rpcn-test writes
- [x] `tools/shared/rpcn_check/rpcn_check.py` -- the `hash` subcommand with both modes, `KNOWN_FORMATS` and the header parser -- staleness check
- [x] `tools/shared/rpcn_check/tests/test_rpcn_check.py` -- every matrix row -- tests
- [x] `tools/shared/rpcn_check/SCHEMA.md` -- the `hash` section -- the contract
- [x] `skills/rpcn-test/shared.txt` -- three format mappings; then run `uv run tools/sync_shared.py` -- the docs ship with the skill

**Acceptance Criteria:**
- Given the example test report in `test-report-format.md`, with its example pipeline written to disk and hashed, when `hash --check` runs, then it is `ready`. After the pipeline changes, it is not ready, with state `changed`.
- Given the repo after sync, when `uv run tools/sync_shared.py --check` runs, then it exits 0, with four `rpcn-test` copies in state `ok`.

## Implementation Notes

- **Header parser** (`parse_handoff_header`): all eight keys are required; unknown or repeated keys, empty values, a `status` outside `draft|ready|superseded`, absolute input paths and sha256 values that are not 64 lowercase hex are exit 2 with the line. `inputs: []` and a bare `inputs:` with no items both mean no inputs. Values may be wrapped in matching quotes. A missing key is reported at the closing `---` line.
- **`format_known`** also requires the `format` artifact to equal `artifact` (`artifact: test-report` with `format: design@1` is unknown). A malformed `format` value is unknown (exit 1), not a header error.
- **Not-ready `errors`:** `hash --check` lists one error per reason (changed or missing input, status not ready with its line, unknown format with its line), so `ok` equals `ready`. On exit 2 `data` is `{}`; `hash <file>...` with a missing file gives `data: {"hashes": []}`.
- **Doc examples are executable:** the format docs mark example files with `<!-- example-file: NAME -->`. The test `test_doc_example_report_is_ready_then_stale` writes `orders.yaml`, `orders.design.md` and `orders.test-report.md` from the docs and checks ready, then stale. Editing either example means updating the hashes in `test-report-format.md` (and the header example in `handoff-header.md`, also tested). The example pipeline lints clean on 4.100.0 and 4.115.0.
- **Interpretation, test report readiness:** `status: ready` means the report is complete for one run; the Summary carries `**Verdict:** pass|fail`. The readiness list has a general part (every reader, including rpcn-author reading Proposed changes from a failing report) and an extra part (verdict `pass`, lint ran) for readers that need the pipeline itself to be ready.
- **Design note conventions added:** Open decisions bullets start `[blocking]` or `[non-blocking]`; Components is a `kind | component | role` table; Deviations `resolved` is `no` or `yes`; design notes normally have `inputs: []`.
- **Settled (2026-10-23):** the user confirmed test-report readiness as option B. `hash --check` now reports `verdict` and `pipeline_ready`, and AD-6 is amended to match.

## Plan Change Log

## Review Triage Log

**Pass 1 (quick):** 1 intent gap (resolved by the user, option B), 6 → patch.

| # | Finding | Verdict | Route | Evidence |
|---|---|---|---|---|
| 1 | The header doc's pipeline-ready rule ignores the verdict | medium | intent_gap → resolved (B) | AD-6 can be read two ways: ready meaning passed, or ready meaning complete. The user chose B. The code is kept, and `hash --check` adds `verdict` and `pipeline_ready`. |
| 2 | An unreadable input crashes `hash --check` with a traceback | medium | patch | The `sha256_file` `OSError` isn't caught in `_check_handoff`, so no envelope is printed and the exit code collides with not-ready. |
| 3 | The example DLQ key `json("id")` groups nothing | medium | patch | The order id is unique, while the design note orders per `customer_id`. Skills will copy the reference example. |
| 4 | The Bloblang samples `mapping` column is defined differently from the example | low | patch | Direct correction of the definition. |
| 5 | SCHEMA's `binary` row omits `hash` as a null case | low | patch | Direct doc correction. |
| 6 | `handoff-header.md` has no `${CLAUDE_SKILL_DIR}` fallback | low | patch | AD-3 requires the fallback line, and the file ships under `references/`. |
| 7 | A literal BOM in the `lstrip` argument | low | patch | Replace it with the `\ufeff` escape. |

## Design Notes

**Example header** (the shape the parser accepts):

```yaml
---
artifact: test-report
format: test-report@1
pipeline: orders
status: ready
produced_by: rpcn-test@0.1.0
rpcn_version: 4.115.0
inputs:
  - file: orders.yaml
    sha256: 3f5a…(64 hex)
updated: 2026-10-23
---
```

**Why the check lives in the script:** comparing hashes is deterministic work, and AD-3 and the determinism rule keep that out of prose. The readiness *list*, the judgement items in each format doc, stays with the reading skill.

## Verification

**Commands:**
- `uv run tools/shared/rpcn_check/tests/test_rpcn_check.py` -- expected: all pass (real-binary tests skipped)
- `uv run tools/sync_shared.py --check` -- expected: exit 0, 4 copies `ok`
- `uv run skills/rpcn-test/scripts/rpcn_check.py hash tools/shared/formats/handoff-header.md` -- expected: exit 0 with one sha256
