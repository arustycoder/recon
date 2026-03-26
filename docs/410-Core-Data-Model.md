# Core Data Model

## Goal

Define the canonical entities and relationship rules for the product so channels, runtime, knowledge, memory, and control surfaces all operate on the same model.

This data model follows the system architecture in `docs/330-Generic-Assistant-Platform.md` and the adaptive separation defined in `docs/460-Adaptive-Evolution-Model.md` [1][2].

## Core Entities

- `actor`
- `workspace`
- `assistant_profile`
- `adaptive_overlay`
- `conversation`
- `message`
- `resource`
- `memory_record`
- `knowledge_collection`
- `knowledge_source`
- `task`
- `task_run`
- `task_step`
- `tool_definition`
- `request_record`
- `adaptation_event`
- `adaptation_candidate`
- `profile_promotion`
- `audit_event`

## Relationship Rules

- every conversation belongs to one workspace
- every task belongs to one workspace and may link to one conversation
- every memory record belongs to exactly one scope
- every adaptive overlay belongs to exactly one scope and references one profile or workspace context
- every adaptation candidate may promote into an adaptive overlay or expire without activation [2]
- every knowledge source belongs to one collection and one visibility scope
- every assistant profile has an owner scope and visibility rules
- every request record links to the actor, workspace, profile, and resulting outputs

## Cross-Cutting Fields

Durable entities should carry:

- stable id
- owner scope
- visibility
- status
- created_at
- updated_at
- version when mutation history matters

## Modeling Rules

- user-visible objects should have stable identifiers
- mutable projections are allowed, but important actions should also generate immutable audit or event records
- soft delete is preferred for inspectable product assets
- policy, ownership, and visibility should be modeled explicitly, not inferred from path or naming

## Recommended First-Class Assets

The product should treat these as inspectable assets rather than hidden internal state:

- profiles
- memories
- sources
- tasks
- tools
- adaptive overlays
- evaluations

## Non-Goals

- channel-specific schemas as the system of record
- implicit ownership
- unversioned profile mutation for production-critical assistants

## References

[1] `docs/330-Generic-Assistant-Platform.md`

[2] `docs/460-Adaptive-Evolution-Model.md`
