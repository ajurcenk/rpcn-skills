# Change proposal format, `change@1`

The change proposal `<name>.change.md` is what rpcn-author writes in change
mode: a change the user asked for to an existing pipeline `<name>.yaml` or
`<name>.yml`, as diffs to review before they land. It sits beside the
pipeline in the developer's project, and rpcn-author is its only writer.
Writing it changes no other file: rpcn-author's apply step (Step 7) applies
a ready proposal later, the same way it applies a test report, and never
edits the proposal. Its header follows `handoff-header.md`, with:

```yaml
artifact: change
format: change@1
```

A breaking change to this format (a section renamed, removed or reordered,
or the item shape changed) bumps the major to `change@2`. Readers reject a
major they do not know, through `rpcn_check.py hash --check`.

## Header

- `pipeline`: `<name>`, the pipeline the proposal changes.
- `produced_by`: `rpcn-author@<plugin version>`.
- `rpcn_version`: the binary the diffs were checked on.
- `inputs`: every file the change was made from, hashed as it was read,
  before the diffs were made:
  - the pipeline, `<name>.yaml` or `<name>.yml`, always first and as a bare
    file name, even when no diff changes it;
  - then each resources file and each `.blobl` file the pipeline loads,
    whether a diff changes it or not, and `.env.example` when a diff
    changes it, recorded relative to the proposal's folder (such as
    `<name>.resources.yaml` or `../resources.yaml`).

  A file a diff creates (`--- /dev/null`) is not an input: there is nothing
  to hash. A design note the change was read against is not an input either.

When any input changes, `hash --check` reports the proposal as not ready,
so a proposal is never applied to a file it was not made against.

## Status

- `ready`: every part of the request has its diff, and Open decisions holds
  no `[blocking]` item.
- `draft`: some part of the request has no diff (such as a component the
  binary doesn't list), and a `[blocking]` item says why. A draft is never
  applied.
- `superseded` is not used: rpcn-author writes a new proposal over its own
  old one.

## Sections

After a `# <name>: change proposal` title, the body has exactly these three
`##` sections, with these headings, in this order:

1. **Request**: the change asked for, in the user's words, as one quoted
   paragraph (`> …`). Nothing is added to it.
2. **Proposed changes**: one numbered item per change, in the item shape of
   `test-report-format.md`'s Proposed changes:
   - a title line saying what changes;
   - a cause line, `Cause: <the part of the request it carries out>`;
   - a fenced `diff` block in unified format against the file to change
     (`--- a/<file>`, `+++ b/<file>`, relative to the proposal's folder),
     with three lines of context. A new file is `--- /dev/null` and
     `+++ b/<file>`, all `+` lines.

   Each diff changes only what its item needs: every other line of the file
   stays as it is. The diffs of all items apply in order, matched on
   content: each hunk's context and `-` lines are unique in the file as the
   earlier items left it. rpcn-author checks each diff on a copy outside
   the project (lint, with at most two revisions); a diff that still fails,
   or that can't be checked, ends its title with `(unverified)`. With no
   diff at all, the section is `None.` and the proposal is `draft`. A
   request the pipeline already meets gets no proposal at all.
3. **Open decisions**: one bullet per choice the request leaves open, or
   `None.`:
   - `[blocking] <what>`: a part of the request with no diff, and why (a
     component the binary doesn't list, a field none fits). Any such item
     makes the proposal `draft`.
   - `[non-blocking] <question> Picked: <the choice the diffs make>`: a
     choice made in place of a question, and a departure from a ready
     design note, which names the note's section. These leave it `ready`.

## Readiness list

After `rpcn_check.py hash --check <name>.change.md` reports `ready: true`,
every reader checks:

- [ ] The three sections are present, with the headings above, in order.
- [ ] The first input is the pipeline, `<name>.yaml` or `<name>.yml`, as a
      bare file name.
- [ ] Proposed changes has at least one item, each with a title, a
      `Cause:` line and a `diff` block.
- [ ] Every file a diff changes, other than a file it creates, is in
      `inputs`, and so is every resources and `.blobl` file the pipeline
      loads.
- [ ] Open decisions has no `[blocking]` item.

If any item fails, the reader treats the proposal as not ready and applies
nothing.

## Example

The pipeline is the example `orders.yaml` in `test-report-format.md`. The
request: "drop test orders before posting". The proposal:

<!-- The sha256 is the real hash of the example orders.yaml in test-report-format.md, and
     the diff applies to it; the rpcn_check tests check both. -->
<!-- example-file: orders.change.md -->
````markdown
---
artifact: change
format: change@1
pipeline: orders
status: ready
produced_by: rpcn-author@0.1.0
rpcn_version: 4.117.0
inputs:
  - file: orders.yaml
    sha256: 77c752d3d897336753043dd647d081da3caae2669b3c6bc7169fa80b44729e56
updated: 2026-11-25
---

# orders: change proposal

## Request

> drop test orders before posting

## Proposed changes

1. Drop test orders after the `total_cents` mapping.
   Cause: the request, "drop test orders before posting": a message whose
   `test` field is `true` is deleted before the HTTP output.

```diff
--- a/orders.yaml
+++ b/orders.yaml
@@ -9,6 +9,7 @@
     - mapping: |
         root = this
         root.total_cents = (this.total * 100).round()
+    - mapping: 'root = if this.test == true { deleted() } else { this }'
 
 output:
   fallback:
```

## Open decisions

- [non-blocking] Which orders are test orders? Picked: a message whose
  `test` field is `true`; one without the field is posted.
````
