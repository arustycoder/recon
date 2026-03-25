# Memory Model

## Goal

Define how `recon` stores, retrieves, updates, and deletes assistant memory so the product can go beyond stateless chat while staying inspectable and controllable.

## Scope

### Included

- recent conversation context
- session summary memory
- workspace-scoped saved memory
- profile-scoped default memory
- memory approval, pinning, and deletion
- memory retrieval rules for prompt construction

### Excluded

- hidden self-modifying memory with no user visibility
- unconstrained autonomous memory writes
- cross-tenant global memory sharing

## Memory Layers

Prompt assembly should treat memory as layered context:

1. system and profile instructions
2. workspace structured context
3. session summary
4. selected saved memories
5. recent messages

The assistant should not load all stored memory blindly. It should load only the minimum relevant memory for the current request.

## Memory Types

### Session Summary

- concise recap of the current conversation
- refreshed periodically or at explicit checkpoints
- used to compress older turns without losing continuity

### Saved Memory

- durable fact or preference worth reusing later
- examples: preferred language, project goals, recurring constraints, stable user preferences
- may be user-created, user-approved, or system-imported

### Profile Memory

- default memory bundled with an assistant profile
- examples: house style, team conventions, domain guardrails

### Workspace Memory

- memory visible to all conversations inside one workspace
- suitable for project goals, terminology, stakeholders, and standing instructions

## Behavior

- the assistant may propose memory candidates, but durable writes should require explicit approval in the first phase
- users must be able to pin, edit, archive, and delete saved memory
- each memory item should record scope, source, and last-used time
- session summaries may be refreshed automatically because they are compression artifacts, not durable facts
- memory retrieval should prefer high-salience, recent, and explicitly pinned items

## Data Impact

Recommended new entities:

- `memory_records`
- `memory_links`

Suggested `memory_records` fields:

- `id`
- `scope_type` such as `profile`, `workspace`, `session`
- `scope_id`
- `kind` such as `summary`, `fact`, `preference`, `instruction`
- `content`
- `status` such as `active`, `archived`, `deleted`
- `source_type`
- `source_id`
- `pinned`
- `last_used_at`
- `created_at`
- `updated_at`

## UI Impact

- memory should be visible in a dedicated manager, not hidden inside raw database state
- session summaries may stay lightweight in the conversation UI
- durable memory actions should be available as explicit user controls: `保存为记忆`, `固定`, `删除`

## Implementation Notes

- the first implementation can stay local and deterministic for summary refresh and ranking
- memory retrieval should happen in the gateway so desktop and future channels share the same behavior
- later phases can add assistant-suggested memory extraction and confidence scoring

## Relationship To Existing Docs

- complements `docs/90-Session-Summaries.md`
- complements `docs/330-Generic-Assistant-Platform.md`
