# Status block

In headless mode, end the reply with exactly one fenced `json` block, then
nothing:

```json
{"status": "<complete|blocked>", "skill": "rpcn-design", "reason": null, "artifacts": [], "checks": {"lint": "skipped", "tests": "skipped"}, "open_questions": []}
```

Fill it this way:

- `status`: `blocked` (with `reason`) only after:
  - an exit 2 in Step 1, 3 or 4 (`reason` the first error)
  - an existing design note at Step 2 (`reason` names it; nothing is
    written)
  - a Step 6 `hash --check` that still fails after 2 fixes of the header

  Otherwise `complete`. A pick made in place of a question never blocks.
  Neither does a `draft` note with a `[blocking]` open decision: the run
  ends `complete`, and that item goes in `open_questions`.
- `checks.lint` and `checks.tests`: always `skipped`. rpcn-design writes
  no pipeline, so nothing is linted or tested.
- `artifacts`: the note, as a path from the project root, when it was
  written; else `[]`.
- `open_questions`: one line per open decision: `Assumed: <pick>
  (<question>)` for each `[non-blocking]` pick, and the question for each
  `[blocking]` one.
