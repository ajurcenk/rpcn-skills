---
name: rpcn-author
description: 'Writes new Redpanda Connect pipelines from a plain request. Picks components and fields that the installed rpk connect (or redpanda-connect) binary reports, writes <name>.yaml (plus <name>.resources.yaml and .env.example when needed) and lints it until clean. Use when the user says "write me a Redpanda Connect pipeline", "create a pipeline that reads from … and writes to …", "build a Redpanda Connect config", "generate a pipeline YAML", "new pipeline" or "rpcn-author", and when the user describes a data flow (a source, processing and a sink) and asks for the Redpanda Connect config. Not for linting or testing a pipeline: use rpcn-test. Not for deploying pipelines.'
compatibility: "Requires rpk with Redpanda Connect >= 4.100.0, and uv."
license: Apache-2.0
metadata:
  plugin-version: "0.1.0"
---

# rpcn-author

Call the binary only through the bundled script, one `uv run …/rpcn_check.py`
command per Bash call: no `cd`, `&&`, `;`, variables, `cat` or heredocs. Read
and write files with the Read and Write tools.

**Headless** when the prompt says the run is unattended, headless or
non-interactive, or the script reports `data.headless: true`: never ask
anything, record each gap in `open_questions`, and end with the status block.

## Step 1: Check the binary

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py binary
```

If `${CLAUDE_SKILL_DIR}` is not expanded, replace it with the absolute path of
the folder that holds this SKILL.md, in this and every call below.

Each call prints one JSON object (`ok`, `binary`, `errors`, `data`). **Exit 2**
in any step means the run can't continue: write nothing, show each
`errors[].message`, and in headless mode report `blocked`.

## Step 2: Name the files

`<pipeline>` is the file the user names, with its extension (`<name>.yaml`
or `.yml`), else a short snake_case `<name>.yaml`. `<dir>/` is its folder as
the user gave it (for example `pipes/`), or nothing for the project root.

If `<dir>/<pipeline>` already exists, never write over it: ask the user, or
in headless mode stop with `blocked` and the question in `open_questions`.

## Step 3: Pick components

For each part of the request (input, processors, output, caches and other
resources), list what the binary has:

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

Set only paths in `data.fields[].path` (children come after parents, as
`tls.enabled` or `a[].b`), and every field with `required: true`. On exit 1,
`data.components` holds close matches: pick one that fits, else ask (headless:
add to `open_questions`). Never write a component the binary doesn't list.

## Step 5: Write the files

Write `<dir>/<pipeline>` with the Write tool: plain YAML, no header or
comment block at the top. Secrets, addresses and credentials are always
`${ENV_VAR}`, never inline values. When the pipeline uses a resource or an
env var, read `references/pipeline-files.md` and write the resources file
and `<dir>/.env.example` as it says.

## Step 6: Lint

`<res>` is `<dir>/<name>.resources.yaml` (`.resources.yml` for a `.yml`
pipeline) when Step 5 wrote one:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py lint <dir>/<pipeline> [--resources <res>]
```

On exit 1, fix each entry in `errors` (check new fields as in Step 4), write
the file again and lint again, at most 3 revisions. If it still fails,
report the remaining errors; in headless mode report `blocked` with `reason`
the first one.

Reply with the files written, the components used, and the lint result.

## Next

- Lint clean: test it with rpcn-test.
- Lint still failing: fix the reported errors, then lint with rpcn-test.

## Status block (headless only)

End the reply with exactly one fenced `json` block, and nothing after it:

```json
{"status": "<complete|blocked>", "skill": "rpcn-author", "reason": null, "artifacts": [], "checks": {"lint": "<pass|fail|skipped>", "tests": "skipped"}, "open_questions": []}
```

- `blocked` (with `reason`) only after an exit 2, an existing file, or lint
  still failing after 3 revisions; otherwise `complete`.
- `checks.lint`: `pass`, `fail`, or `skipped` when lint did not run.
- `artifacts`: every file written, as paths from the project root.
