---
name: rpcn-test
description: 'Checks Redpanda Connect pipelines and the binary they run on. Lints a pipeline YAML, explains each error with its cause and a proposed fix, and writes a <name>.test-report.md beside it. Also finds rpk connect (or redpanda-connect) and reports its path and version against the supported 4.100.0 floor. Use when the user says "lint my pipeline", "check this Redpanda Connect config", "why does my pipeline fail lint", "test my pipeline", "check my Redpanda Connect binary", "which rpk connect version do I have", "is Redpanda Connect installed" or "rpcn-test", and when the user pastes a Redpanda Connect config (YAML with input, pipeline or output) and asks what is wrong with it or why it fails. Not for writing pipelines or applying a report''s changes: use rpcn-author. Not for designing or deploying them.'
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
in Steps 1–3 means the run can't test: write no report, show each
`errors[].message`, and for a binary error read
`references/binary-fixes.md` and show its fix.

If the user asked only about the binary, report `binary.path` and
`binary.version` (a path ending in `rpk` runs as `rpk connect`), then go to Next.

**Pasted config:** if the user pastes YAML instead of naming a file, first
read `references/pasted-config.md` and follow it.

## Step 2: Hash the inputs

`<pipeline>` is the pipeline's file name, with its real extension
(`<name>.yaml` or `.yml`). In every call, `<dir>/` is its folder as the
user gave it (for example `pipes/`), or nothing when it is in the project
root. `<res>` is the resources file the user names (such as a shared
`resources.yaml`), else `<dir>/<name>.resources.yaml` (`.resources.yml` for
a `.yml` pipeline) if it exists, else none. Hash the pipeline, then `<res>`:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py hash <dir>/<pipeline> [<res>]
```

## Step 3: Lint

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py lint <dir>/<pipeline> [--resources <res>] [--env-file <file>]
```

Pass `--env-file` only when the user names one.

## Step 4: Explain the errors

Only when there are errors, read `references/lint-errors.md`. For every entry
in `errors`, in order, give its file, line and column, the cause, and the fix
as a unified diff against that file. Never add or drop an error. Then write
the fully fixed pipeline to
`<system temp dir>/rpcn-test-${CLAUDE_SESSION_ID}/<pipeline>` (if the variable
is not expanded, end the folder in 8 random letters instead), read
`references/fix-check.md` and follow it.

## Step 5: Write the report

Write `<name>.test-report.md` beside the pipeline: read
`references/report-writing.md` and follow it, with
`references/test-report-format.md` and `references/handoff-header.md`.

Check it:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py hash --check <dir>/<name>.test-report.md
```

It must report `data.ready: true`. On exit 1 or 2, fix only the report's own
header or format once and check again; never re-hash an input or change its
`sha256`. If it still isn't ready (such as an input changed after
hashing), set `status: draft`, say why, and in headless mode report `blocked`.

Reply with the verdict, the explained errors and diffs, and report path.

## Next

- Errors found: apply the proposed changes with rpcn-author, then re-run rpcn-test.
- 0 errors: nothing to fix.
- Binary fixed: re-run rpcn-test to confirm it.
- No pipeline yet, or write a new one: use rpcn-author.

## Status block (headless only)

End the reply with exactly one fenced `json` block, and nothing after it:

```json
{"status": "<complete|blocked>", "skill": "rpcn-test", "reason": null, "artifacts": [], "checks": {"lint": "<pass|fail|skipped>", "tests": "skipped"}, "open_questions": []}
```

Read `references/status-block.md` and fill the block as it says.
