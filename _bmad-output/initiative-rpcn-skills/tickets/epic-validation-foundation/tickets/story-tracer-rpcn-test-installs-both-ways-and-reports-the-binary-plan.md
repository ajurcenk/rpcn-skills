---
title: 'Tracer: rpcn-test installs both ways and reports the binary'
type: 'feature'
ticket: '1'
created: '2026-10-23'
status: done
baseline_revision: '363e3f34f58272b30fa3d41259efc0921bd70610'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The repo has planning documents but no skill, plugin manifest, check script or CI, so nothing proves that a skill can install through both channels and reach the user's `rpk connect` binary.

**Approach:** This is the thinnest end-to-end slice. It adds the plugin manifest, a minimal `rpcn-test` skill whose one job is "check my Redpanda Connect binary", the `rpcn_check.py binary` subcommand with the schema-1 JSON envelope and binary lookup (AD-4), unit tests, and a one-job GitHub Actions workflow. Pushing to `ajurcenk/rpcn-skills` makes both installs testable.

## Boundaries & Constraints

**Always:**
- **Skill folder:** `rpcn-test` uses only files inside `skills/rpcn-test/` (AD-1).
- **Two copies:** the canonical source is `tools/shared/rpcn_check/rpcn_check.py`, and `skills/rpcn-test/scripts/rpcn_check.py` is a byte-identical hand copy (AD-2; story 3 automates it).
- **Script runtime:** a PEP 723 header with `requires-python = ">=3.10"`, standard library only, run as `uv run` (AD-3).
- **JSON envelope:** `{"schema":1,"ok","command","binary":{"path","version"},"errors":[],"data":{}}`. `binary`'s data is `{"plugin_version","refs_version","newer_than_refs","headless"}`, with `refs_version: null` and `newer_than_refs: false` until epic 4 generates references.
- **Exit codes:** 0 for ok, 2 for a usage or environment error. Exit 1 is reserved for failed checks (story 2).
- **Binary lookup:**
  1. `RPCN_BINARY` or `EVAL_RPCN_BINARY`
  2. `rpk` on PATH, run as `rpk connect`
  3. `redpanda-connect` on PATH

  The version comes from the `Version:` line with a leading `v` stripped. A version below 4.100.0 exits 2.
- **Headless:** `headless` is true when `RPCN_HEADLESS=1` or `EVAL_RPCN_HEADLESS=1`.
- **Plugin version:** `plugin_version` is the constant `0.1.0`, the same as `plugin.json`.
- **SKILL.md** follows AD-9:
  - a description with quoted "Use when" phrases
  - `compatibility: "Requires rpk with Redpanda Connect >= 4.100.0, and uv."`
  - calls `uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py binary`, with a note that the path is relative to the SKILL.md folder when the variable isn't expanded
  - ends with a Next step: re-run `rpcn-test` after fixes
  - the AD-8 status block when headless
- **Plugin name:** `rpcn-skills`.

**Never:**
- running `rpk connect` outside `rpcn_check`
- `python` or `pip` commands, or `jq`
- lint and the other subcommands (stories 2, 4 and 8)
- `sync_shared` (story 3)
- the validator (story 9)
- anything committed under `.claude/skills` or `.agents/skills`
- a `bin/` folder, which would stop claude.ai from installing the plugin

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| rpk present | `rpk` on PATH; `rpk connect --version` prints `Version: 4.112.0` | exit 0; `ok:true`; path is rpk; version `4.112.0` | — |
| Override | `RPCN_BINARY` set to a `redpanda-connect` printing `Version: v4.100.0` | version `4.100.0`; the override wins over PATH | — |
| Fallback | no rpk; `redpanda-connect` on PATH | that binary is used | — |
| Too old | the binary prints `Version: 4.99.0` | exit 2; `ok:false` | error message names the 4.100.0 floor |
| Missing | nothing on PATH, no override | exit 2; `ok:false`; `binary` null | error says how to install |
| rpk without connect | `rpk connect --version` fails | falls back to `redpanda-connect`, else exit 2 | error message mentions `rpk connect install` |
| Headless | `EVAL_RPCN_HEADLESS=1` | `data.headless: true` | — |
| Bad args | an unknown subcommand | exit 2, with a usage message in `errors` | — |

</frozen-after-approval>

## Code Map

- **Already present, keep as is:**
  - `.gitignore`, which already ignores `.claude/skills/`, `.agents/skills/`, `_bmad/render/` and `_bmad/custom/*.user.toml`
  - `skills-lock.json` and `LICENSE` (Apache-2.0)
- **Not touched:** `_bmad-output/` holds the planning documents.
- **Local binaries for checks:**
  - `~/.local/bin/rpk`: `rpk connect` is 4.112.0, using the `rpk` v26.2.2 managed plugin
  - `~/.local/bin/redpanda-connect`: 4.100.0, a source build that prints `Version: v4.100.0`
  - Installing a specific version uses `rpk connect install --connect-version <v>`, one managed version at a time
- **Repo state:** `ajurcenk/rpcn-skills` on GitHub is empty and public, so the first push needs no pull.
- **Current versions:** `actions/checkout` v7 (7.0.1) and `astral-sh/setup-uv` v10 (10.3.2).
- **Manifests** (verified in the architecture research):
  - `plugin.json` needs only `name`, and `skills/` is scanned by default
  - `marketplace.json` needs `name`, `owner` and `plugins[{name, source:"./"}]`
- **No prior code to reuse.** The binary-lookup and version rules come from AD-4.

## Tasks & Acceptance

**Execution:**
- [x] `.claude-plugin/plugin.json` -- name `rpcn-skills`, version `0.1.0`, description, author, Apache-2.0 -- Claude Code plugin identity
- [x] `.claude-plugin/marketplace.json` -- marketplace `rpcn-skills`, owner `ajurcenk`, one plugin with `source: "./"` -- `claude plugin marketplace add ajurcenk/rpcn-skills`
- [x] `tools/shared/rpcn_check/rpcn_check.py` -- argparse CLI with the `binary` subcommand, envelope, lookup, version parsing and floor, headless flag, exit codes -- the AD-4 adapter seed
- [x] `tools/shared/rpcn_check/SCHEMA.md` -- the envelope and `binary` data schema, version 1 -- the contract that later subcommands extend
- [x] `tools/shared/rpcn_check/tests/test_rpcn_check.py` -- PEP 723 unittest script using fake binaries (temporary shell scripts) and controlled PATH and env, covering every matrix row -- runnable as `uv run …`, no real binary needed
- [x] `skills/rpcn-test/scripts/rpcn_check.py` -- byte-identical copy of the source -- self-contained skill
- [x] `skills/rpcn-test/SKILL.md` -- frontmatter (name, AD-9 description, compatibility, license, metadata plugin-version) and a body under 800 tokens: when it applies, run `binary`, report path and version, explain exit 2, Next, headless status block -- the minimal skill
- [x] `SOURCES.md` -- a header and an empty table (file, source, licence, notes) -- stories 5 and 8 append to it
- [x] `README.md` -- what it is, both install commands, requirements, licence -- the user-facing entry
- [x] `.github/workflows/ci.yml` -- on push and pull_request: checkout@v7, setup-uv@v10, run the unit test script, `cmp` the two `rpcn_check.py` copies -- the one-job CI later stories extend

**Acceptance Criteria:**
- Given the repo pushed to `main`, when `npx skills add ajurcenk/rpcn-skills --list` runs, then it lists `rpcn-test` and no BMad skill.
- Given Claude Code, when the `rpcn-skills` marketplace is added and the plugin installed, then `rpcn-test` appears, and asking "check my Redpanda Connect binary" returns the binary's path and version from the JSON.
- Given a push to `main`, when CI runs, then the job is green.

## Implementation Notes

- **`errors[].file` is `null`** for errors not tied to a file (all `binary` errors). AD-4 types `file` as `str`; `null` is documented in `SCHEMA.md` as the not-file-bound case. Revisit if story 2 prefers `""`.
- **`data` is filled even when `ok` is false** for `binary`, so the skill can still read `headless` when the binary is missing or too old. Usage errors return `data: {}` and `command` as the raw first argument (`""` when none).
- **Too old** still reports `binary` (path and version); only "missing" and usage errors give `binary: null`.
- **Overrides** accept a path or a command name; a broken override is exit 2 with no fallback. An override whose file is named `rpk` runs as `rpk connect`.
- **Local `npx skills add . --list`** in the working tree also shows `bmad-retrospective`, because `.claude/skills/bmad-retrospective` exists on disk (gitignored, a real folder rather than a symlink). A copy of only the git-visible files (`git ls-files -co --exclude-standard`) lists `rpcn-test` alone, which is what a push publishes.
- **Smoke test:** `claude --plugin-dir . -p "check my Redpanda Connect binary"` triggered `rpcn-test` and reported `~/.local/bin/rpk`, 4.112.0. `claude plugin validate` passes (only warning: no plugin icon).

## Plan Change Log

## Review Triage Log

**Pass 1 (quick):** 2 medium/low → patch, 1 maybe-false → defer, 2 rejected.

| # | Finding | Verdict | Route | Evidence |
|---|---|---|---|---|
| 1 | `binary --help` prints help to stdout and exits via argparse | medium | patch | `_Parser` overrides only `error()`. argparse's help action writes the subparser help to stdout, which breaks SCHEMA.md's "one JSON object on stdout". Top-level help goes to stderr, so the two paths are inconsistent. |
| 2 | `4.100.0-rc1` passes the 4.100.0 floor | low | patch | `_version_tuple` keeps only the numbers, so a pre-release compares equal to its release. The fix is a direct correction of the comparison. |
| 3 | A real `rpk` may auto-download Connect on `rpk connect --version` | maybe-false | defer | The fake `rpk` always exits 1. Settling it needs a run of `rpk connect --version` with the Connect plugin uninstalled. Severity if true: medium (a timeout or a side-effect install). |
| 4 | The plan's local `npx skills add . --list` also lists `bmad-retrospective` | false | reject | The fix would edit this build's plan. The published tree has only `rpcn-test`, because `.claude/skills/` is gitignored. Acceptance criterion 1 is checked after the push. |
| 5 | Acceptance criteria 1–3 are not shown by the diff | false | reject | They are hands-on checks after the push by design (`hitl = true`). This is not a defect in the change. |

## Design Notes

**Why `binary` only.** It proves every layer (install, skill, script, binary, JSON) with the least logic. `lint` needs text parsing and is high risk on its own (story 2).

**How the skill calls the script:**

```
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py binary
```

**Why fake binaries in tests.** They make every lookup and version case deterministic, and CI needs no Redpanda Connect download until story 2.

## Verification

**Commands:**
- `uv run tools/shared/rpcn_check/tests/test_rpcn_check.py` -- expected: all tests pass
- `cmp tools/shared/rpcn_check/rpcn_check.py skills/rpcn-test/scripts/rpcn_check.py` -- expected: no output
- `uv run skills/rpcn-test/scripts/rpcn_check.py binary` -- expected: exit 0, JSON with `rpk` and `4.112.0`
- `RPCN_BINARY=~/.local/bin/redpanda-connect uv run skills/rpcn-test/scripts/rpcn_check.py binary` -- expected: version `4.100.0`
- `npx skills add . --list` (from the repo root) -- expected: only `rpcn-test` is listed

**Manual checks (hitl, after the user pushes):**
- `npx skills add ajurcenk/rpcn-skills` and `claude plugin marketplace add ajurcenk/rpcn-skills` on a clean folder offer only `rpcn-test`
- the GitHub Actions run on `main` is green
