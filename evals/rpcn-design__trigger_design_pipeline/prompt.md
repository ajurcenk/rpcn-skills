---
max_turns: 2
allowed_tools: [Skill]
tags: [trigger, positive]
---

Design a Redpanda Connect pipeline that reads orders from a Redpanda topic and posts each one to our fulfilment HTTP API. Failed orders should go to a dead-letter queue.
