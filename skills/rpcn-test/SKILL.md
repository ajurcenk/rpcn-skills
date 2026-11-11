---
name: rpcn-test
description: 'Checks Redpanda Connect pipelines and the binary they run on. Lints a pipeline YAML, runs its Bloblang mappings against their samples, dry-runs it, explains each error or mismatch with its cause and a proposed fix, and writes a <name>.test-report.md beside it. Also reports the rpk connect (or redpanda-connect) path and version against the 4.100.0 floor. Use when the user says "lint my pipeline", "check this Redpanda Connect config", "why does my pipeline fail lint", "test my pipeline", "check my Bloblang mapping against its samples", "dry-run my pipeline", "check my Redpanda Connect binary", "which rpk connect version do I have", "is Redpanda Connect installed" or "rpcn-test", and when the user pastes a Redpanda Connect config (YAML with input, pipeline or output) and asks what is wrong with it or why it fails. Not for writing pipelines or applying a report''s changes (use rpcn-author), designing or deploying them.'
compatibility: "Requires rpk with Redpanda Connect >= 4.100.0, and uv."
license: Apache-2.0
metadata:
  plugin-version: "0.1.0"
---

# rpcn-test

Run the binary only as one `uv run …/rpcn_check.py` command per Bash call:
no `cd`, `&&`, `;`, variables, `cat` or heredocs. Use Read and Write for
files. Never edit the pipeline or a `.blobl`: propose fixes as diffs.

**Headless** when the prompt says unattended, headless or non-interactive,
or the script reports `data.headless: true`: never ask, and end with the
status block.

## Step 1: Check the binary

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py binary
```

If `${CLAUDE_SKILL_DIR}` is not expanded, use this file's folder's
absolute path, here and below.

Each call prints one JSON object. **Exit 2** in Steps 1–3 (but `blobl`,
`run`) means it can't test: write no report, show each `errors[].message`;
for a binary error show the fix in `references/binary-fixes.md`.

If asked only about the binary, report `binary.path` and `binary.version`
(`…/rpk` runs as `rpk connect`), then go to Next.

**Pasted config** (not a file name): follow
`references/pasted-config.md`.

## Step 2: Hash the inputs

`<pipeline>` is the pipeline's file name (`<name>.yaml` or `.yml`). `<dir>/`
is its folder as the user gave it (such as `pipes/`), or nothing for the
project root. `<res>` is the resources file the user names (such as a shared
`resources.yaml`), else `<dir>/<name>.resources.yaml` (`.resources.yml` for
`.yml`) if it exists. `<blobl>` is each `from "<path>"` file it loads. Hash
them all:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py hash <dir>/<pipeline> [<res>] [<blobl>]...
```

## Step 3: Lint

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py lint <dir>/<pipeline> [--resources <res>] [--env-file <file>]
```

Pass `--env-file` only when the user names one (or `dry-run.md` says),
here and below. For each `<blobl>`, follow `references/samples.md` (with
`references/samples-format.md`, `references/blobl-files.md`):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py blobl <blobl> --samples <dir>/<name>.samples.json [--env-file <file>]
```

Then follow `references/dry-run.md`:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py run <dir>/<pipeline> --bounded --input <msgs> [--resources <res>] [--env-file <file>]
```

## Step 4: Explain the errors

Only on lint errors, read `references/lint-errors.md`. For every entry
in `errors`, in order, give its file, line and column, the cause, and the fix
as a unified diff. Never add or drop an error. Write the fixed pipeline to
`<system temp dir>/rpcn-test-${CLAUDE_SESSION_ID}/<pipeline>` (variable not
expanded: end the folder in 8 random letters), read
`references/fix-check.md` and follow it.

## Step 5: Write the report

Write `<dir>/<name>.test-report.md` as `references/report-writing.md` says,
with `references/test-report-format.md` and `references/handoff-header.md`.

Check it:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py hash --check <dir>/<name>.test-report.md
```

It must report `data.ready: true`. If not, fix only the report's header or
format once and recheck; never re-hash an input or change a `sha256`.
Still not ready: set `status: draft`, say why, headless report `blocked`.

Reply with the verdict, errors, diffs and report path.

## Next

- Errors or failed checks: apply the proposed changes with rpcn-author, then re-run rpcn-test.
- Binary fixed: re-run rpcn-test.
- No pipeline yet: use rpcn-author.

## Status block (headless only)

End with exactly one fenced `json` block, then nothing:

```json
{"status": "<complete|blocked>", "skill": "rpcn-test", "reason": null, "artifacts": [], "checks": {"lint": "<pass|fail|skipped>", "tests": "<pass|fail|skipped>"}, "open_questions": []}
```

Fill it as `references/status-block.md` says.
