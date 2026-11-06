---
max_turns: 2
allowed_tools: [Skill]
tags: [trigger, positive]
---

Create a pipeline that reads from the Redpanda topic clicks and writes the messages to an S3 bucket as newline-delimited JSON. I use Redpanda Connect.
