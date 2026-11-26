# Changing an existing pipeline

Read this from Step 2 when `<dir>/<pipeline>` exists and the request asks
to change that pipeline: "change `orders.yaml` to drop test orders",
"update `pipes/orders.yaml` so it retries the API", "add a DLQ to my
pipeline `orders.yaml`". Change mode never edits the pipeline or any of its
files. It writes one file, the proposal `<dir>/<name>.change.md` in
`change-format.md` (in this folder), and Step 7 applies it later, when the
user asks ("apply `<name>.change.md`").

Not change mode, so Step 2 as today:

- a request to write, create or generate a pipeline in a file that exists
  ("write a pipeline in `orders.yaml` that …"): never write over it, ask
  (headless: `blocked`);
- the named pipeline doesn't exist: there is nothing to change; build it
  new, as Steps 3 to 6 say;
- a named `<name>.test-report.md` or `<name>.change.md` to apply: Step 7.

Interactive runs write the same proposal as headless ones.

## 1. Read

Read these files with the Read tool, and edit none of them:

- the pipeline `<dir>/<pipeline>`;
- its resources file `<dir>/<name>.resources.yaml` (`.resources.yml` for
  `.yml`), when it exists;
- each `.blobl` file a `from "<path>"` in the pipeline names (the path is
  from the project root);
- `<dir>/.env.example`, when it exists;
- the design note: first run Step 2's `hash --check` on
  `<dir>/<name>.design.md` (the one command here). When it is ready (and passes `design-format.md`'s readiness list), read
  it, never edit it, and keep the change in line with it. A change that
  departs from it (the request asks for something a section says
  otherwise) is still made, and named in Open decisions as
  `[non-blocking] <what departs> (design note, <section>). Picked: <what
  the diff does>`. No Deviations row: rpcn-author never edits the note in
  change mode. A missing note changes nothing here. A not-ready note is
  not used: say why in the reply, and headless add `status-block.md`'s
  one not-ready line to `open_questions` (it never blocks).

## 2. Pick and check

Each new component and each new field the change needs: `list` and
`fields`, as Steps 3 and 4 say. A component the binary doesn't list, with
no listed one that fits: no diff for that part, and a `[blocking] <the
component> is not listed by Redpanda Connect <binary.version>.` item in
Open decisions, so the proposal is `draft`. Never write a component the
binary doesn't list.

Questions: only what the change leaves open (`questions.md`), in its one
round, interactive. Headless never asks: use your pick, and name it in Open
decisions as `[non-blocking] <question> Picked: <pick>`.

## 3. Make the diffs

Change only what the request needs:

- every existing label, comment, field order, blank line and unrelated part
  stays as it is: never reformat, reorder or rename;
- an inline mapping stays inline: never move it into a `.blobl` file
  unless the request asks;
- `.env.example` only gains `NAME=` lines (`pipeline-files.md`); a new
  secret or address is `${NAME}`, never inline;
- a new resource or `.blobl` file follows `pipeline-files.md`, as a diff
  that creates it (`--- /dev/null`).

One item per change, in `change-format.md`'s shape: a title, a `Cause:`
line naming the part of the request, and a `diff` per file, relative to
`<dir>/`, with three lines of context. Make each hunk's context and `-`
lines unique in the file as the earlier items left it.

## 4. Verify each diff on a copy

As rpcn-test's fix check does, never beside the pipeline:

1. Write each changed file, with every item's diff applied, under its own
   name into `<system temp dir>/rpcn-author-${CLAUDE_SESSION_ID}/` (if the
   variable is not expanded, end the folder name in 8 random letters).
   `<system temp dir>` is `/tmp` (on Windows, `%TEMP%`): never run a
   command to learn the temp dir or the session ID. A changed `.blobl` copy: in the pipeline copy, point
   its `from` at the copy's absolute path.
2. Lint the pipeline copy as Step 6 does, with `--resources` the resources
   file (its copy when a diff changes it).
3. On exit 1, revise the diffs, at most 2 times. A diff that still fails,
   or that can't be checked, ends its title with `(unverified)`. A
   `.env.example` diff needs no lint.

A no-op diff is never a change: in each hunk the `-` lines equal its `+`
lines, in the same order, or the patched file equals the original. Drop
it. When the pipeline already does what the request asks, so no diff is
left: write no proposal, say so in the reply, and end `complete` with
`artifacts: []`.

## 5. Write the proposal

Hash the inputs, as `change-format.md` says, with one command (paths from
the project root):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py hash <dir>/<pipeline> [<each other file in inputs>]
```

The other files are every file §1 read but the note (the resources file,
each `.blobl`), and `.env.example` when a diff changes it; never a file a
diff creates.

Record each `file` relative to `<dir>/` (`orders.yaml`, not
`pipes/orders.yaml`). Then Write `<dir>/<name>.change.md`: the header
(`status: ready`, or `draft` with a `[blocking]` item), `# <name>: change
proposal`, then Request (the user's words), Proposed changes and Open
decisions. It is rpcn-author's own file: an existing one is written over.
Write nothing else in the project: the pipeline, its resources, `.blobl`
and `.env.example` files stay byte-identical.

## 6. Reply

Name the proposal, each item (title, file, verified or `(unverified)`) and
each open decision. Next: review it, then "apply `<dir>/<name>.change.md`".
Headless: `complete`, the proposal in `artifacts`, `checks.lint` `pass`
when every linted copy was clean (`fail` when one wasn't, `skipped` when
none was linted), each `[non-blocking]` pick in `open_questions`. A
`[blocking]` item ends `blocked`, `reason` naming it, with the draft
proposal in `artifacts`.
