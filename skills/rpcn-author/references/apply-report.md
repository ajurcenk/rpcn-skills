# Applying a test report or change proposal

rpcn-test writes `<name>.test-report.md` and never edits the pipeline. Its
Proposed changes are diffs that rpcn-author applies (AD-6). Use the report
only after `hash --check` in Step 7 reported `data.ready: true`. The report
may have the verdict `pass` or `fail`.

A change proposal `<name>.change.md` (`format: change@1`, written by
rpcn-author's change mode, `change.md`) is applied the same way: below,
"the report" means the proposal too, with the differences each section
names. Never edit the proposal.

## 1. Check the readiness list

First, Step 7's `hash --check` on `<file>` = `<dir>/<name>.test-report.md`
(`<dir>/` its folder): go on only on exit 0 with `data.ready: true`, else
stop as on exit 2 (`state: changed` means stale). For a proposal,
`<file>` is `<dir>/<name>.change.md`.

Then read the report and check the readiness list in `test-report-format.md`
(in this folder): the sections in order (seven for `format: test-report@2`;
six for `test-report@1`, which has no Dry run), a `**Verdict:**` line, and
each section that did not run says `Not run` and why. Both formats are read
the same way otherwise: the Dry run section only informs, and its fixes, if
any, are Proposed changes items like any other. A proposal's readiness
list is in `change-format.md` (in this folder): its three sections, the
pipeline as `inputs[0]`, at least one item, a diff against the design note
that only appends Deviations rows and sets `updated`, and no `[blocking]`
Open decision (so a `draft` is never applied). If an item fails, treat the
report as not ready: change nothing, say which item failed, and in
headless mode report `blocked` with that as `reason`.

## 2. Find the files

The report's `inputs` are relative to the report's folder `<dir>/`:

- `<pipeline>` is `inputs[0]` (`<name>.yaml` or `<name>.yml`), so the
  pipeline is `<dir>/<pipeline>`.
- Each resources input (such as `<name>.resources.yaml` or
  `../resources.yaml`) is a `<res>`, as a path from the project root.
- `<name>` is the report's `pipeline` header field.

A proposal's files are found the same way: `inputs[0]` is the pipeline,
and each resources input is a `<res>` for lint, whether a diff changes it
or not. A `<name>.design.md` input is the design note, never a `<res>`.

## 3. Pick the changes

Proposed changes holds numbered items, each a title, a `Cause:` line and
a fenced `diff` block, or `None.`. An older item with one line on why in
place of the title and `Cause:` line is applied the same way. With
`None.` there is nothing to apply: change no file, say so, and skip lint.

Apply an item, of any kind (a lint fix, a design fix, a requested change
or any other change), only when its diff is against one of these files:

- the report's pipeline, `inputs[0]`
- a resources file listed in the report's `inputs`
- that pipeline's own Bloblang files, `<name>.<label>.blobl`
- `.env.example` in `<dir>/`
- for a proposal only: its design note `<name>.design.md` in `<dir>/`,
  listed in its `inputs`, when every hunk of the diff either appends
  Deviations table rows after the table's last line (only `+` lines, each a
  table row) or changes the header's `updated:` line (one `-` and one `+`
  line, both `updated:`). Any other hunk against the note fails the
  readiness list: the proposal is not ready, change nothing (§1). Skip the
  item when the item it records (its `Cause:`
  names it) was not applied, or only partly: name it in the reply. Apply
  it as §4 says, Edits only; it needs no lint.

Skip every other target and name it in the reply, with why: the test
report or proposal itself, `<name>_benthos_test.yaml`, a samples file or
any other file rpcn-test owns (rpcn-test applies its own files), a design
note (but a proposal's Deviations item, above), another pipeline, or any
file not in the list above. Never edit the report or proposal.

A proposal's diff may create a file (`--- /dev/null`): the pipeline's own
`<name>.resources.yaml` (`.resources.yml`), a `<name>.<label>.blobl`, or
`.env.example` in `<dir>/`, applied as §4 says.

An item whose title ends with `(applied by rpcn-test)` is already applied
to rpcn-test's own file: skip it and say so. An item whose title ends with
`(unverified)` is still applied: lint decides.

## 4. Apply each diff

The `--- a/<file>` and `+++ b/<file>` paths are relative to `<dir>/`. Apply
each diff with the Edit tool, one hunk at a time, in the report's order:

- `old_string` is the hunk's context and `-` lines, exactly as in the file;
  `new_string` is the same lines with the `-` lines dropped and the `+`
  lines added. Strip the one-character diff prefix (space, `-` or `+`).
- Match on content, not on the `@@` line numbers: an earlier item may have
  moved lines.
- Before editing, Read the file and check that every hunk of the item is in
  it exactly once. If one isn't, don't guess: apply no hunk of that item,
  name the item in the reply, add it to `open_questions`, and go on with the
  next item. Items already applied stay applied.

A diff that creates a file (`--- /dev/null`, all `+` lines) has no hunk
to match: if the file doesn't exist, Write it with the `+` lines (prefix
stripped); if it exists, skip that item, say so, and add it to
`open_questions`. A created resources file is a `<res>` for lint.

When the host refuses an Edit (or a Write that creates a file), that hunk
or file doesn't land: never try that change another way, such as a Write
or a different Edit. Apply no more hunks of that item, and go on with the
next item. Hunks of the item that landed before the refusal (in that file
or another) stay applied: never undo them. Report the item as not applied
when nothing of it landed, else as partly applied, naming what landed and
what was refused. A lint revision never redoes a refused item, whole or
part. Lint what landed, as below.

After the edits, lint as in Step 6, but pass `--resources <res>` for each
resources input found in section 2 (paths from the project root). On a lint
failure, revise as Step 6 says.

## 5. Reply

List each item by number with its result: applied (a created file says
so; a note item names its Deviations row: section, what, why), skipped (the file and why, such as a file to create that exists) or
not applied (the hunk that didn't match, or the Edit the host refused),
or partly applied (the hunks that landed, and the refused one). Then the
files edited and the lint result. The run ends `complete` even when some
items were not applied.
