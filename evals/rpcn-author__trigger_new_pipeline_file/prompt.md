---
max_turns: 2
allowed_tools: [Skill]
tags: [trigger, positive]
---

I need a new pipeline in ingest/events.yaml: consume from the Redpanda topic events, add a processed_at timestamp to each message, and write them to Postgres.
