---
name: rpcn-author
description: 'Writes new Redpanda Connect pipelines from a plain request, using only components and fields the installed binary reports, plus resources and .env.example files when needed, and lints them until clean. Also applies the proposed changes in a <name>.test-report.md. Use when the user says "write me a Redpanda Connect pipeline", "create a pipeline that reads from … and writes to …", "build a Redpanda Connect config", "generate a pipeline YAML", "new pipeline", "apply the test report", "fix my pipeline from its test report" or "rpcn-author", and when the user describes a data flow (source, processing, sink) and asks for its Redpanda Connect config. Not for linting or testing a pipeline (use rpcn-test), or deploying it.'
compatibility: "Requires rpk with Redpanda Connect >= 4.100.0, and uv."
license: Apache-2.0
metadata:
  plugin-version: "0.1.0"
---

# rpcn-author

Call the binary only through the bundled script, one `uv run …/rpcn_check.py`
command per Bash call: no `cd`, `&&`, `;`, variables, `cat` or heredocs. Use
the Read, Write and Edit tools for files.

**Headless** when the prompt says unattended, headless or non-interactive,
or a script call reports `data.headless: true`: never ask, put each gap in
`open_questions`, and end with the status block.

## Step 1: Check the binary

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py binary
```

If `${CLAUDE_SKILL_DIR}` is not expanded, use the absolute path of this
SKILL.md's folder, here and below.

Each call prints one JSON object (`ok`, `binary`, `errors`, `data`). **Exit 2**
in any step means the run can't continue: write nothing, show each
`errors[].message`, and in headless mode report `blocked`.

## Step 2: Name the files

If the user names or asks to apply a `<name>.test-report.md`, go to Step 7
instead.

`<pipeline>` is the file the user names, with its extension (`<name>.yaml`
or `.yml`), else a short snake_case `<name>.yaml`. `<dir>/` is its folder as
the user gave it (such as `pipes/`), or nothing for the project root.

If `<dir>/<pipeline>` already exists, never write over it: ask the user
(headless: stop `blocked`, with the question in `open_questions`).

## Step 3: Pick components

For each part of the request (input, processors, output, resources), list
what the binary has:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py list <category>
```

`<category>` is `inputs`, `processors`, `outputs`, `caches`, … Use only
names in `data.components`.

## Step 4: Check the fields

For every component you use:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py fields <category> <component>
```

Set only paths in `data.fields[].path` (such as `tls.enabled` or `a[].b`),
and every field with `required: true`. On exit 1, `data.components` holds
close matches: pick one that fits, else ask (headless: add to
`open_questions`). Never write a component the binary doesn't list.

## Step 5: Write the files

Write `<dir>/<pipeline>`: plain YAML, no header or comment block. Secrets,
addresses and credentials are always `${ENV_VAR}`, never inline. For a
resource or an env var, read `references/pipeline-files.md` and write the
files it says.

## Step 6: Lint

`<res>` is `<dir>/<name>.resources.yaml` (`.resources.yml` for a `.yml`
pipeline) when there is one:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py lint <dir>/<pipeline> [--resources <res>]
```

On exit 1, fix each entry in `errors` (check new fields as in Step 4), save
the file and lint again, at most 3 revisions. If it still fails, report the
remaining errors; in headless mode report `blocked` with `reason` the first.

Reply with the files, components and lint result.

## Step 7: Apply a test report

`<dir>/` is the report's folder:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py hash --check <dir>/<name>.test-report.md
```

Go on only on exit 0 with `data.ready: true`; otherwise stop as on exit 2
(an input `state: changed` means the report is stale).

Read `references/apply-report.md` and follow it, with
`references/test-report-format.md`.

## Next

- Lint clean, or report applied: test it with rpcn-test.
- Lint still failing: fix the reported errors, then lint with rpcn-test.
- Report not ready (stale, draft or incomplete): re-run rpcn-test for a fresh one.
- File already exists: re-run rpcn-author with a new name.
- Binary missing or too old: fix it as reported, then re-run rpcn-author.

## Status block (headless only)

End the reply with exactly one fenced `json` block, then nothing:

```json
{"status": "<complete|blocked>", "skill": "rpcn-author", "reason": null, "artifacts": [], "checks": {"lint": "<pass|fail|skipped>", "tests": "skipped"}, "open_questions": []}
```

Fill it as `references/status-block.md` says.
