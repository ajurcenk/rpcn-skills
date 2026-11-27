---
name: rpcn-author
description: 'Writes new Redpanda Connect pipelines from a plain request, or builds from a ready <name>.design.md, using only components and fields the binary reports, and lints them until clean. Also applies a <name>.test-report.md''s or <name>.change.md''s proposed changes. Use when the user says "write me a Redpanda Connect pipeline", "create a pipeline that reads from … and writes to …", "build a Redpanda Connect config", "generate a pipeline YAML", "new pipeline", "change my pipeline to …", "apply the design change …", "build the pipeline from its design note", "apply the test report", "fix my pipeline from its test report" or "rpcn-author", and when the user describes a data flow (source, processing, sink) and asks for its Redpanda Connect config. Not for designing a pipeline before it is built or describing an existing pipeline as a design note (use rpcn-design), linting or testing it (use rpcn-test), or deploying it.'
compatibility: "Requires rpk with Redpanda Connect >= 4.100.0, and uv."
license: Apache-2.0
metadata:
  plugin-version: "0.1.0"
---

# rpcn-author

One `uv run …/rpcn_check.py` command per Bash call: no `cd`, `&&`, `;`,
variables, `cat` or heredocs. Use Read, Write and Edit for files.

**Headless** when the prompt says unattended, headless or non-interactive,
or a script reports `data.headless: true`: never ask, put gaps in
`open_questions`, end with the status block.

## Step 1: Check the binary

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py binary
```

Unexpanded `${CLAUDE_SKILL_DIR}`: use this folder's absolute path.

Calls print JSON (`ok`, `errors`, `data`). **Exit 2**
in any step (but Step 2's note check) means stop: write nothing,
show each `errors[].message` (headless: `blocked`).

## Step 2: Name the files

If the user names or asks to apply a `<name>.test-report.md` or
`.change.md`, go to Step 7.

`<pipeline>` is the named file, with its extension (`<name>.yaml`
or `.yml`), else a short snake_case `<name>.yaml`; if only a `.design.md` is
named, `<name>` is its `pipeline`. `<dir>/` is the named file's folder, or
nothing (project root).

If `<dir>/<pipeline>` exists: to change it, see `references/change.md`;
else never write over it: ask in Step 5's round (headless: stop,
`blocked`, question in `open_questions`).

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

`<category>` is `inputs`, `processors`, `outputs`, … Use only
names in `data.components`.

## Step 4: Check the fields

For each component:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py fields <category> <component>
```

Set only `data.fields[].path` paths (`tls.enabled`, `a[].b`),
and every `required: true` field. On exit 1, pick a close match in
`data.components` that fits, else ask in Step 5's round (headless:
`blocked`). Never write a component the binary doesn't list.

## Step 5: Ask, then write

First follow `references/questions.md`. Then write `<dir>/<pipeline>`:
plain YAML, no comment block. Secrets, addresses and credentials are
always `${ENV_VAR}`, never inline. For a resource, env var or mapping over
3 lines, follow `references/pipeline-files.md` (with
`references/blobl-files.md`).

## Step 6: Lint

`<res>` is `<dir>/<name>.resources.yaml` (`.resources.yml` for `.yml`), if
any:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py lint <dir>/<pipeline> [--resources <res>]
```

On exit 1, fix each `errors` entry (new fields: Step 4), lint
again; at most 3 revisions. Still failing: report the errors (headless:
`blocked`, `reason` the first).

Reply with the files, components and lint result.

## Step 7: Apply a report or proposal

Run Step 2's `hash --check` on the `.test-report.md` or
`.change.md` (`<dir>/` its folder), then `references/apply-report.md`
(§1 says when to stop), with `references/test-report-format.md` or
`references/change-format.md`.

## Next

- Lint clean, report applied, or change made or applied: test
  with rpcn-test.
- Lint failing: fix it, lint with rpcn-test.
- Report or proposal not ready: re-run its writer.
- Proposal written: review, then apply it.
- Design note not ready: update it with rpcn-design.
- File exists: re-run with a new name.
- Binary missing or old: fix, re-run.

## Status block (headless only)

End with exactly one fenced `json` block, then nothing, as
`references/status-block.md` says.
