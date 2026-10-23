---
title: 'rpcn_check lint: text parsing, exit codes and flags on both binaries'
type: 'feature'
ticket: '2'
created: '2026-10-23'
status: done
baseline_revision: 'fbe04fe2092052034ed9f99bedbdb9851b58a936'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md', '{project-root}/tools/shared/rpcn_check/SCHEMA.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `rpcn_check` can find the binary but can't lint, so no skill can check a pipeline. Linting must give the same structured result on every tested Redpanda Connect version, but `rpk connect lint` has no JSON output and its error order differs between versions.

**Approach:** Add a `lint` subcommand that runs `lint --deprecated --skip-env-var-check` with the fixed flags, parses its text into the schema-1 `errors` array and maps outcomes to exit codes 0, 1 and 2. Test it two ways: with fake binaries for every parsing and exit case, and against the real 4.100.0 and newest (4.115.0) binaries. CI downloads both versions. One version list serves CI and local runs.

## Boundaries & Constraints

**Always:**
- **Arguments:** `lint <file>... [--resources <file>]... [--env-file <file>]`. The binary is called as `lint --deprecated --skip-env-var-check`, then `--resources <f>` once per unique file, then `--env-file <f>`, then the targets with glob characters escaped. `NO_COLOR=1` is set. `-v`, `--verbose`, `-` and `--chilled` are never passed (AD-4).
- **Parsing:** each output line matching `<file>(<line>,<col>) <message>` becomes one error. Any other non-empty line becomes an error with `file`, `line` and `column` set to null. Errors are sorted by file, line and column, so every version gives the same order.
- **Exit codes:**
  - 0 when the binary exits 0 and nothing parsed as an error
  - 1 when the binary reports errors
  - 2 for a missing target, resources or env file (checked before running), no usable binary, a lint timeout (60 s), or a non-zero exit with no output
- **Data:** `{"files": [the targets as given], "error_count": int}`.
- **Tested versions:** `tools/rpcn_versions.txt` lists `4.100.0` and `4.115.0`. It is the only place versions are named. `tools/fetch_rpcn.py` uses it.
- **Fetching binaries:** `tools/fetch_rpcn.py` downloads the plain release build (`redpanda-connect_<v>_<os>_<arch>.tar.gz` from github.com/redpanda-data/connect releases), checks it against the published `.sha256`, and unpacks it into `.cache/rpcn/<v>/`. It is standard library only and runs with `uv run`.
- **Tests on real binaries** run only when `RPCN_TEST_BINARIES` lists binary paths. Locally, without it, they are skipped and say so.
- **Copies:** the skill copy of `rpcn_check.py` stays byte-identical to the source.

**Never:**
- changing `binary`'s behaviour or its data shape
- copying fixtures from other repos (write our own)
- `rpk connect install` in CI or tests, because it replaces the user's managed version
- `python` or `pip`, or `jq`
- touching `skills/rpcn-test/SKILL.md` (story 5)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid | a clean pipeline | exit 0, `ok:true`, `errors:[]`, `error_count:0` | — |
| Several errors | a file with 4 lint errors | exit 1, 4 errors with file, line and column, sorted | — |
| Deprecated component | a `kafka` input | exit 1, message "component kafka is deprecated" | — |
| YAML syntax error | malformed YAML | exit 1, one error at (1,1) | — |
| Several files | two broken files | exit 1, errors from both, sorted by file | — |
| Unset env var | `${LIMIT}`, with no env file | exit 0 (`--skip-env-var-check`) | — |
| Missing target | a path that does not exist | exit 2, error names the file, binary not run | — |
| Missing resources or env file | a bad `--resources` or `--env-file` path | exit 2, binary not run | — |
| No targets | `lint` with no files | exit 2, usage message | — |
| No or old binary | as in `binary` | exit 2 | same messages as `binary` |
| Text that doesn't parse | the binary prints an unformatted line and exits 1 | exit 1, an error with null file, line and column | — |
| Silent failure | the binary exits non-zero with no output | exit 2 | message gives the exit code |
| Timeout | the binary runs longer than 60 s | exit 2 | "timed out" |
| Glob characters | a target named `a[1].yaml` | linted as that exact file | — |
| Flags | any lint call | argv is exactly the fixed flags, then resources, then env file, then targets | — |

</frozen-after-approval>

## Code Map

- **`tools/shared/rpcn_check/rpcn_check.py`:** reuse `require_binary()`, which returns `argv` (`[rpk, "connect"]` or `[path]`), plus `_envelope`, `_emit`, `_error`, `_Parser` and the exit constants (`EXIT_CHECK_FAILED = 1` already exists). Add `cmd_lint` and the subparser. Leave `cmd_binary` and lookup unchanged.
- **`tools/shared/rpcn_check/tests/test_rpcn_check.py`:** reuse `write_exe` and the fake-binary pattern. A fake `rpk` can print canned lint output and write its argv to a file so flags can be asserted.
- **`tools/shared/rpcn_check/SCHEMA.md`:** add a `lint` section, and mark exit 1 as used by `lint`.
- **`skills/rpcn-test/scripts/rpcn_check.py`:** re-copy from the source.
- **`.github/workflows/ci.yml`:** add steps to cache `.cache/rpcn` (keyed on `tools/rpcn_versions.txt`), run `uv run tools/fetch_rpcn.py`, then run the real-binary tests with `RPCN_TEST_BINARIES`. Keep `checkout@v7` and `setup-uv@v10.3.0`; moving major tags don't exist for setup-uv.
- **`.gitignore`:** add `.cache/`.
- **Verified `rpk connect lint` behaviour** (4.100.0 and 4.112.0, `NO_COLOR=1`):
  - **Line format:** `file(line,col) message`.
  - **Exit codes:** 0 when clean, 1 when there are errors.
  - **Missing files:** a missing file is reported as `f(1,1) open f: no such file or directory` with exit 1. That's why we check files first.
  - **Ordering:** the order of errors across files differs between versions, which is why we sort.
  - **Unset env vars:** an unset variable is an error without `--skip-env-var-check`.
- **`rpk connect install --connect-version <v>`** (AD-14's verification item) works, but it keeps one managed version and replaces the user's. So CI and tests use release tarballs instead. Record this in the Implementation Notes so the architecture can be updated.
- **Local binaries:**
  - `rpk connect` is 4.112.0
  - `~/.local/bin/redpanda-connect` is 4.100.0, a source build
  - `fetch_rpcn.py` provides 4.100.0 and 4.115.0 locally too
- **Release assets:** 4.115.0 (released 2026-10-22) and 4.100.0 each publish `linux_amd64` and `darwin_arm64` plain tarballs, each with a `.sha256` file.

## Tasks & Acceptance

**Execution:**
- [x] `tools/rpcn_versions.txt` -- `4.100.0` and `4.115.0`, one per line -- the single version list
- [x] `tools/fetch_rpcn.py` -- PEP 723 script: for each listed version, download, check the sha256 and unpack into `.cache/rpcn/<v>/`, skipping versions already present; print a JSON list of the binary paths; exit non-zero on a checksum failure or an unsupported platform -- reproducible binaries without `rpk`
- [x] `tools/shared/rpcn_check/rpcn_check.py` -- `lint` subcommand per the Boundaries and the matrix -- the core of R2
- [x] `tools/shared/rpcn_check/tests/fixtures/` -- our own `valid.yaml`, `multi_error.yaml`, `deprecated.yaml`, `bad_yaml.yaml`, `env_var.yaml` and `a[1].yaml` -- real-binary inputs
- [x] `tools/shared/rpcn_check/tests/test_rpcn_check.py` -- fake-binary tests for every matrix row, plus a real-binary class that runs the fixtures against each path in `RPCN_TEST_BINARIES`, skipped when it is unset -- one test script
- [x] `tools/shared/rpcn_check/SCHEMA.md` -- the `lint` arguments, data and exit codes -- the contract
- [x] `skills/rpcn-test/scripts/rpcn_check.py` -- re-copy -- byte-identical
- [x] `.github/workflows/ci.yml` -- cache, fetch and real-binary tests -- CI on both versions
- [x] `.gitignore` -- `.cache/` -- downloaded binaries are never committed

**Acceptance Criteria:**
- Given `uv run tools/fetch_rpcn.py`, when it finishes, then `.cache/rpcn/4.100.0` and `.cache/rpcn/4.115.0` each hold a working `redpanda-connect` whose version matches.
- Given `RPCN_TEST_BINARIES` set to both fetched binaries, when the test script runs, then every real-binary test passes on both, with the same sorted errors for each fixture.
- Given a push, when CI runs, then fetching and the tests on both versions are green.

## Implementation Notes

- **AD-14 install item (for the architecture):** `rpk connect install --connect-version <v>` works but keeps a single managed version and replaces the user's, so CI and tests use the plain release tarballs fetched by `tools/fetch_rpcn.py` instead. AD-14's "each version via `rpk connect install`" should be updated to this.
- **Glob escaping verified on real binaries:** unescaped `a[1].yaml` is treated as a pattern (it matches `a1.yaml`, or nothing and exits 0). Backslash escaping of `\ * ? [ ] { }` lints the exact file, and the binary prints the unescaped path. Resources files are escaped too, since `--resources` also takes globs; `--env-file` is not a glob and is passed as is.
- **Lint output goes to stderr** on both versions; stdout and stderr are both parsed.
- **Mixed argument order:** `lint a.yaml --resources r.yaml b.yaml` is accepted (argparse leaves later positionals over; `main` adds them to `files`). Extra `-`-prefixed arguments are still a usage error.
- **Missing files:** checked before the binary lookup, so `binary` is `null` in that case and the binary is not run. One error per missing file, with `file` set. `data.error_count` is `0` whenever lint did not run.
- **Sort order:** file, line, column, then message as a tiebreak; file-less errors last.
- **Timeout:** the lint runs in its own process group and the whole group is killed on timeout, so a grandchild (e.g. the plugin started by `rpk`) cannot keep the pipes open. The fake-binary timeout test imports the module and sets `LINT_TIMEOUT_S = 1` in-process; there is no public knob.
- **Exit 0 with parseable output** is treated as exit 1 (binary reported errors).
- **`fetch_rpcn.py`** prints absolute paths. CI converts the JSON list to a `:` list with `tr` (no `jq`) and fails if it is empty, so real-binary tests can't silently skip there. Cache key: OS, arch and the hash of `tools/rpcn_versions.txt`; `actions/cache@v6` (current major).
- **Real-binary tests** assert positions exactly and messages by substring, plus identical error lists across every binary. Also pass locally against `rpk connect` 4.112.0 and the `~/.local/bin/redpanda-connect` 4.100.0 source build.
- **Test structure:** the shared helpers moved into `CheckTestBase`; `RpcnCheckTest` (binary) and `LintTest` both extend it.

## Plan Change Log

## Review Triage Log

**Pass 1 (quick):** 4 → patch, 1 rejected.

| # | Finding | Verdict | Route | Evidence |
|---|---|---|---|---|
| 1 | Fetched or cached binaries are never checked against their version | medium | patch | `fetch()` returns early on any existing executable, and the real-binary test checks the path but not the version. A stale CI cache would pass, against acceptance criterion 1. |
| 2 | The greedy regex misparses a message that contains `(n,m) ` | low | reject | Not seen in any verified output. The fix (matching known paths) adds branches. This is a low-likelihood case, rejected under the low-plus-complexity rule. |
| 3 | Non-UTF-8 output raises an exception instead of printing the envelope | medium | patch | `Popen(text=True)` decodes strictly. `UnicodeDecodeError` is not caught, which breaks AD-4's one-JSON-object rule. The fix is `errors="replace"`. |
| 4 | Duplicate targets are linted twice and errors counted twice | low | patch | Targets aren't made unique, unlike resources. The fix is a direct correction. |
| 5 | The real missing-file test doesn't show the binary never ran | low | patch | It doesn't assert `binary` is null. The fix is one assertion. |

## Design Notes

**The parsing pattern** (greedy file part, so a path that contains parentheses still splits on the last `(line,col)`):

```
^(?P<file>.+)\((?P<line>\d+),(?P<col>\d+)\) (?P<message>.*)$
```

**Why check files first:** the binary turns a missing file into an ordinary lint error with exit 1. Checking first keeps "your pipeline is broken" (exit 1) separate from "the check couldn't run" (exit 2).

## Verification

**Commands:**
- `uv run tools/fetch_rpcn.py` -- expected: two paths, exit 0
- `RPCN_TEST_BINARIES=.cache/rpcn/4.100.0/redpanda-connect:.cache/rpcn/4.115.0/redpanda-connect uv run tools/shared/rpcn_check/tests/test_rpcn_check.py` -- expected: all pass, none skipped
- `uv run tools/shared/rpcn_check/tests/test_rpcn_check.py` -- expected: fake-binary tests pass, real-binary tests skipped
- `cmp tools/shared/rpcn_check/rpcn_check.py skills/rpcn-test/scripts/rpcn_check.py` -- expected: no output
- `uv run skills/rpcn-test/scripts/rpcn_check.py lint tools/shared/rpcn_check/tests/fixtures/multi_error.yaml` -- expected: exit 1, 4 sorted errors
