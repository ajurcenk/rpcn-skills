# Changing an existing pipeline

Read this from Step 2 when `<dir>/<pipeline>` exists and the request asks
to change that pipeline: "change `orders.yaml` to drop test orders",
"update `pipes/orders.yaml` so it retries the API", "add a DLQ to my
pipeline `orders.yaml`". A request to apply a design change is one too:
"apply the design change in `pipes/orders.design.md`", "bring
`orders.yaml` in line with its design note" (§1 says what the change is).
Both modes make and verify the same diffs (§1 to §4), then:

- **Headless** never edits the pipeline or any of its files. It writes one
  file, the proposal `<dir>/<name>.change.md` in `change-format.md` (in
  this folder), and Step 7 applies it later, when the user asks ("apply
  `<name>.change.md`") (§5).
- **Interactive** applies the diffs to the files themselves with Edit, one
  hunk per Edit, so the host can show each one as a diff to approve or
  refuse (§6). It writes no `.change.md` and no status block.

Not change mode, so Step 2 as today:

- a request to write, create or generate a pipeline in a file that exists
  ("write a pipeline in `orders.yaml` that …"): never write over it, ask
  (headless: `blocked`);
- the named pipeline doesn't exist: there is nothing to change; build it
  new, as Steps 3 to 6 say;
- a named `<name>.test-report.md` or `<name>.change.md` to apply: Step 7.

## 1. Read

Read these files with the Read tool, and edit none of them before §6 (the
note only as §6 says):

- the pipeline `<dir>/<pipeline>`;
- its resources file `<dir>/<name>.resources.yaml` (`.resources.yml` for
  `.yml`), when it exists;
- each `.blobl` file a `from "<path>"` in the pipeline names (the path is
  from the project root);
- `<dir>/.env.example`, when it exists;
- the design note: first run Step 2's `hash --check` on
  `<dir>/<name>.design.md` (the one command here). When it is ready (and
  passes `design-format.md`'s readiness list), read it and keep the change
  in line with it. A missing note changes nothing here. A not-ready note
  is not used: say why in the reply, and headless add `status-block.md`'s
  one not-ready line to `open_questions` (it never blocks).

**A design change.** For a request to apply a design change, the note is
required: with no note, or a note that is not ready, change nothing and
write nothing, and say why (no note, or not ready and the readiness item
that failed); headless ends `blocked`, `reason` naming it. With a ready
note, the change is what the pipeline needs to do what the note says. Read
each section it builds from (Components, Inputs, Outputs, Error handling,
Delivery and ordering, Idempotency, Batching) as `design-note.md` §2 (in
this folder) does: where the pipeline already does what the section says,
there is no item; where it doesn't, the item makes it, and its `Cause:`
names the section and what it says. A departure an open Deviations row
(`resolved: no`) already records is accepted: leave it as it is, no item.
The proposal's Request quotes the user's words. Then §2 to §7 as for any
request.

**A departure.** A change that departs from a ready note (it does what a
section says otherwise, as `design-note.md` §3 defines it) is still made,
and recorded as a Deviations row, one per choice, in `design-note.md` §3's
row shape (`resolved` `no`, today's date). That is the one edit rpcn-author
makes to a note here: the row and `updated`, never another line. A
departure an open row already records gets no new row. Headless, the row is
one more item (§3); interactive, two Edits after the item lands (§6).

## 2. Pick and check

Each new component and each new field the change needs: `list` and
`fields`, as Steps 3 and 4 say. A component the binary doesn't list, with
no listed one that fits: no diff for that part, and a `[blocking] <the
component> is not listed by Redpanda Connect <binary.version>.` item in
Open decisions, so the proposal is `draft` (interactive: no Edit for that
part; name it in the reply). Never write a component the binary doesn't
list.

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
line naming the part of the request (for a design change, the note's
section and what it says), and a `diff` per file, relative to `<dir>/`,
with three lines of context. Make each hunk's context and `-` lines unique
in the file as the earlier items left it.

Headless, each departure (§1) adds one item right after the item that
departs: a title such as "Record the departure in the design note", a
`Cause:` line naming that item, the note's section and what it says, and
a diff against `<name>.design.md` with two hunks: one appends the row
after the Deviations table's last line (the separator row when it has no
row), and one changes the header's `updated:` line to today (left out
when the line already says today, such as for a second departure). No
other hunk.

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
   `.env.example` diff and a design note diff need no lint.

A no-op diff is never a change: in each hunk the `-` lines equal its `+`
lines, in the same order, or the patched file equals the original. Drop
it. When the pipeline already does what the request asks, so no diff is
left (for a design change: the pipeline already does what the note says,
or departs only where an open row records it): write no proposal and make
no Edit, say so in the reply, and (headless) end `complete` with
`artifacts: []`.

## 5. Write the proposal (headless)

Hash the inputs, as `change-format.md` says, with one command (paths from
the project root):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py hash <dir>/<pipeline> [<each other file in inputs>]
```

The other files are every file §1 read but the note (the resources file,
each `.blobl`), `.env.example` when a diff changes it, and last the note
`<dir>/<name>.design.md` when a diff changes it (a departure's row); never
a file a diff creates.

Record each `file` relative to `<dir>/` (`orders.yaml`, not
`pipes/orders.yaml`). Then Write `<dir>/<name>.change.md`: the header
(`status: ready`, or `draft` with a `[blocking]` item), `# <name>: change
proposal`, then Request (the user's words), Proposed changes and Open
decisions. It is rpcn-author's own file: an existing one is written over.
Write nothing else in the project: the pipeline, its resources, `.blobl`
and `.env.example` files and the design note stay byte-identical (the
note's row lands when the proposal is applied).

## 6. Apply the diffs with Edit (interactive)

Apply each verified item to the files themselves, in order, as
`apply-report.md` §4 (in this folder) says: Read the file first, then one
Edit per hunk, `old_string` matched on content. Never Write an existing
file, nor replace a whole file with one Edit: the pipeline, its resources,
`.blobl` and `.env.example` files change only by these hunks. A diff that
creates a file (`--- /dev/null`) is Written only when the file is absent,
as `apply-report.md` §4 says. An item whose title ends with `(unverified)`
is still applied: lint decides (`apply-report.md` §3). What
`apply-report.md` §4 adds to `open_questions` goes in the reply instead:
interactive runs have no status block.

A refused Edit doesn't land: never try that change another way. Apply no
more hunks of that item, and go on with the next. Hunks of the item that
landed before it stay applied; report the item as not applied, or as
partly applied naming what landed (`apply-report.md` §4). After the last
item, lint what landed as Step 6 does (with `--resources` the resources
file when there is one), up to 3 revisions, each one an Edit. A revision
never redoes a refused item, whole or part.

A departure (§1): once its item has landed whole, record the row on the
note with `design-note.md` §3's two Edits (the row after the table's last
line, then `updated:`, unless it already says today), Read first. Never Write the note. When the item is
not applied or only partly applied, add no row, and name the departure in
the reply. A refused note Edit is not retried: the pipeline change stays,
and the reply says the row is not recorded.

## 7. Reply

Interactive: name each item (title, file) as applied, partly applied
(what landed, and the refused Edit) or not applied (a refused Edit, or a
hunk that didn't match), each `(unverified)` item as unverified, each
change left out, each Deviations row added to the note (section, what,
why) or not recorded, and the lint result. Next: test it with rpcn-test.

Headless: name the proposal, each item (title, file, verified or
`(unverified)`), each Deviations row a note item adds (section, what,
why) and each open decision. Next: review it, then "apply
`<dir>/<name>.change.md`". End `complete`, the proposal in `artifacts`,
`checks.lint` `pass` when every linted copy was clean (`fail` when one
wasn't, `skipped` when none was linted), each `[non-blocking]` pick in `open_questions`. A
`[blocking]` item ends `blocked`, `reason` naming it, with the draft
proposal in `artifacts`.
