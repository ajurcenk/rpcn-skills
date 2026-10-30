---
name: rpcn-test
description: 'Checks Redpanda Connect pipelines and the binary they run on. Lints a pipeline YAML, explains each error with its cause and a proposed fix, and writes a <name>.test-report.md beside it. Also finds rpk connect (or redpanda-connect) and reports its path and version against the supported 4.100.0 floor. Use when the user says "lint my pipeline", "check this Redpanda Connect config", "why does my pipeline fail lint", "test my pipeline", "check my Redpanda Connect binary", "which rpk connect version do I have", "is Redpanda Connect installed" or "rpcn-test", and when the user pastes a Redpanda Connect config (YAML with input, pipeline or output) and asks what is wrong with it or why it fails. Not for writing, designing or deploying pipelines.'
compatibility: "Requires rpk with Redpanda Connect >= 4.100.0, and uv."
license: Apache-2.0
metadata:
  plugin-version: "0.1.0"
---

# rpcn-test

Call the binary only through the bundled script, one `uv run …/rpcn_check.py`
command per Bash call: no `cd`, `&&`, `;`, variables, `cat` or heredocs. Read
and write files with the Read and Write tools. Never edit the pipeline YAML:
propose fixes as diffs.

**Headless** when the prompt says the run is unattended, headless or
non-interactive, or the script reports `data.headless: true`: never ask
anything, and end with the status block.

## Step 1: Check the binary

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py binary
```

If `${CLAUDE_SKILL_DIR}` is not expanded, replace it with the absolute path of
the folder that holds this SKILL.md, in this and every call below.

Each call prints one JSON object (`ok`, `binary`, `errors`, `data`). **Exit 2**
from any call means the run can't test: write no report, show each
`errors[].message`, and for a binary error the matching fix:
- nothing found: `rpk connect install`, `redpanda-connect` on PATH, or
  `RPCN_BINARY=<path>`
- below 4.100.0: `rpk connect upgrade`, or `rpk connect install --connect-version <version>`

If the user asked only about the binary, report `binary.path` and
`binary.version` (a path ending in `rpk` runs as `rpk connect`), then go to Next.

**Pasted config:** when the user pastes the YAML instead of naming a file, write
it unchanged to a temporary file outside the project with the Write tool, then
run Steps 3 and 4 on that file, giving diffs against the pasted text. Skip
Step 2 and Step 5: write no test report, and in headless mode report
`artifacts: []`. Offer to save it as `<name>.yaml` so a report can be written.

## Step 2: Hash the inputs

The pipeline is `<name>.yaml`. Run every call from its folder. Hash it, then
`<name>.resources.yaml` if that file exists:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py hash <name>.yaml [<name>.resources.yaml]
```

## Step 3: Lint

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py lint <name>.yaml [--resources <name>.resources.yaml] [--env-file <file>]
```

Pass `--env-file` only when the user names one.

## Step 4: Explain the errors

Only when there are errors, read `references/lint-errors.md`. For every entry
in `errors`, in order, give its file, line and column, the cause, and the fix
as a unified diff against that file. Never add or drop an error. Check the
fixes: write the fully fixed pipeline to a temporary file outside the project
and lint it with the same `--resources` and `--env-file` as Step 3, revising
until it is clean.

## Step 5: Write the report

Write `<name>.test-report.md` beside the pipeline, following
`references/test-report-format.md` and `references/handoff-header.md`:
- header: `status: ready`, `produced_by: rpcn-test@<data.plugin_version>`,
  `rpcn_version` from `binary.version`, `inputs` from Step 2 in that order
- Summary: `**Verdict:** pass` only with 0 lint errors, else `fail`
- Lint: `0 errors.` or the error table
- Bloblang samples, Unit tests, Design check: `Not run: not in this version of rpcn-test.`
- Proposed changes: one numbered item and `diff` block per fix, or `None.`

Then run `rpcn_check.py hash --check <name>.test-report.md`; it must report
`data.ready: true`. If it doesn't, fix the report once and check again. If it
still isn't ready (for example an input changed after hashing), set
`status: draft`, say why, and in headless mode report `blocked`.

Reply with the verdict, the explained errors and diffs, and the report path.

## Next

- Errors found: apply the proposed changes, then re-run rpcn-test.
- 0 errors: nothing to fix.
- Binary fixed: re-run rpcn-test to confirm it.

## Status block (headless only)

End the reply with exactly one fenced `json` block, and nothing after it:

```json
{"status": "<complete|blocked>", "skill": "rpcn-test", "reason": null, "artifacts": [], "checks": {"lint": "<pass|fail|skipped>", "tests": "skipped"}, "open_questions": []}
```

- `blocked` (with `reason` the first error) only after an exit 2 or a report
  that stays not ready; otherwise `complete`, even when lint fails.
- `checks.lint`: `pass`, `fail`, or `skipped` when lint did not run.
- `artifacts`: the report path, or `[]`. Questions go in `open_questions`.

