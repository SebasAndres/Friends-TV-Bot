---
name: load
description: Load a document into memory for RAG
type: handler
handler: src.skills.handlers.handle_load
---

Usage: /load <path-to-file>

Loads a text, image, or PDF file into the agent's document store for retrieval-augmented generation.
