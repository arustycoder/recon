# Memory Model

## Goal

Define how the assistant stores, retrieves, updates, and deletes durable context without turning memory into an opaque side effect.

This document assumes the profile and adaptive layering defined in `docs/330-Generic-Assistant-Platform.md` and `docs/460-Adaptive-Evolution-Model.md` [1][2].

## Scope

### Included

- conversation summary memory
- user memory
- workspace memory
- profile memory
- memory proposal, approval, retrieval, and deletion
- retention and forgetting rules

### Excluded

- hidden self-editing memory with no user visibility
- global cross-organization memory
- unlimited automatic memory growth

## Memory Scopes

- `profile`: reusable defaults bundled with an assistant profile
- `user`: personal preferences and stable working habits
- `workspace`: shared context for a project or team space
- `conversation`: compressed state for one thread

## Memory Classes

- `instruction`
- `preference`
- `fact`
- `summary`
- `constraint`

Each memory record should have exactly one scope and one class.

## Retrieval Order

Prompt assembly should resolve memory in this order:

1. profile instructions
2. approved adaptive overlays
3. user memory
4. workspace memory
5. conversation summary
6. recent messages

The runtime should load only relevant memory, not every stored item.

## Behavior

- the assistant may propose memory candidates, but durable writes should be explicit by default
- every durable memory item must show source, scope, status, and last-used time
- users must be able to pin, edit, archive, and delete memory
- summaries may refresh automatically because they are compression artifacts, not durable truth
- memory retrieval should prefer pinned, recent, and high-salience items
- adaptive overlays should not be stored as memory records, even when they are learned from repeated behavior [2]

## Retention Rules

- summaries may be regenerated
- facts and preferences should be versioned instead of silently overwritten
- archived memory should be excluded from default retrieval
- deleted memory should stop participating in retrieval immediately

## Data Impact

Recommended entities:

- `memory_records`
- `memory_versions`
- `memory_references`

Suggested fields:

- `id`
- `scope_type`
- `scope_id`
- `class`
- `content`
- `status`
- `source_type`
- `source_id`
- `pinned`
- `last_used_at`
- `created_at`
- `updated_at`

## Client Impact

- clients should expose memory as a first-class asset, not a hidden internal state
- durable memory actions should be explicit
- memory surfaced in answers should be inspectable when it materially affected the result

## References

[1] `docs/330-Generic-Assistant-Platform.md`

[2] `docs/460-Adaptive-Evolution-Model.md`
