---
name: rpcn-author
description: 'Writes new Redpanda Connect pipelines from a plain request, or builds from a ready <name>.design.md, using only components and fields the installed binary reports, and lints them until clean. Also applies the proposed changes in a <name>.test-report.md. Use when the user says "write me a Redpanda Connect pipeline", "create a pipeline that reads from … and writes to …", "build a Redpanda Connect config", "generate a pipeline YAML", "new pipeline", "build the pipeline from its design note", "apply the test report", "fix my pipeline from its test report" or "rpcn-author", and when the user describes a data flow (source, processing, sink) and asks for its Redpanda Connect config. Not for linting or testing a pipeline (use rpcn-test), or deploying it.'
compatibility: "Requires rpk with Redpanda Connect >= 4.100.0, and uv."
license: Apache-2.0
metadata:
  plugin-version: "0.1.0"
---

# rpcn-author

Run one `uv run …/rpcn_check.py` command per Bash call: no `cd`, `&&`, `;`,
variables, `cat` or heredocs. Use Read, Write and Edit for files.

**Headless** when the prompt says unattended, headless or non-interactive,
or a script reports `data.headless: true`: never ask, put gaps in
`open_questions`, end with the status block.

## Step 1: Check the binary

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py binary
```

If `${CLAUDE_SKILL_DIR}` is not expanded, use this SKILL.md's folder's
absolute path, here and below.

Each call prints a JSON object (`ok`, `binary`, `errors`, `data`). **Exit 2**
in any step (but Step 2's design-note check) means stop: write nothing,
show each `errors[].message` (headless: `blocked`).

## Step 2: Name the files

If the user names or asks to apply a `<name>.test-report.md`, go to Step 7.

`<pipeline>` is the file the user names, with its extension (`<name>.yaml`
or `.yml`), else a short snake_case `<name>.yaml`; if only a `.design.md` is
named, `<name>` is its `pipeline`. `<dir>/` is the folder of the file the
user names (pipeline or `.design.md`), or nothing for the project root.

If `<dir>/<pipeline>` exists, never write over it: ask
(headless: `blocked`, question in `open_questions`).

Check `<file>` = `<dir>/<name>.design.md`:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py hash --check <file>
```

- Exit 2, not found: no note, go on.
- Exit 0, `data.ready: true`: follow `references/design-note.md`, with
  `references/design-format.md`.
- Else: not ready; say why, build from the request, never touch it.

## Step 3: Pick components

For each part (input, processors, output, resources):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py list <category>
```

`<category>` is `inputs`, `processors`, `outputs`, `caches`, … Use only
names in `data.components`.

## Step 4: Check the fields

For each component:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py fields <category> <component>
```

Set only paths in `data.fields[].path` (as `tls.enabled` or `a[].b`),
and every field with `required: true`. On exit 1, `data.components` holds
close matches: pick one that fits, else ask (headless:
`open_questions`). Never write a component the binary doesn't list.

## Step 5: Write the files

Write `<dir>/<pipeline>`: plain YAML, no comment block. Secrets, addresses
and credentials are always `${ENV_VAR}`, never inline. For a resource, env
var or mapping over 3 lines, follow `references/pipeline-files.md`
(with `references/blobl-files.md`).

## Step 6: Lint

`<res>` is `<dir>/<name>.resources.yaml` (`.resources.yml` for a `.yml`
pipeline) when there is one:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py lint <dir>/<pipeline> [--resources <res>]
```

On exit 1, fix each entry in `errors` (check new fields as in Step 4) and
lint again, at most 3 revisions. Still failing: report the errors (headless:
`blocked`, `reason` the first).

Reply with the files, components and lint result.

## Step 7: Apply a test report

Run Step 2's `hash --check` on `<file>` = `<dir>/<name>.test-report.md`
(`<dir>/` its folder); go on only on exit 0 with `data.ready: true`, else
stop as on exit 2 (`state: changed` means stale).

Follow `references/apply-report.md`, with `references/test-report-format.md`.

## Next

- Lint clean, or report applied: test with rpcn-test.
- Lint failing: fix it, lint with rpcn-test.
- Report not ready: re-run rpcn-test.
- File exists: re-run with a new name.
- Binary missing or old: fix, re-run.

## Status block (headless only)

End with exactly one fenced `json` block, then nothing:

```json
{"status": "<complete|blocked>", "skill": "rpcn-author", "reason": null, "artifacts": [], "checks": {"lint": "<pass|fail|skipped>", "tests": "skipped"}, "open_questions": []}
```

Fill it as `references/status-block.md` says.
