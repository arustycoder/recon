# Generic Assistant Platform

## Goal

Explore how `recon` can evolve from an energy-domain conversational workbench into a general-purpose, customizable AI assistant product without discarding the useful runtime and operations work that already exists.

## Companion Design Docs

This document is the platform overview. Detailed follow-on designs live in:

- `docs/340-Memory-Model.md`
- `docs/350-Task-Runtime.md`
- `docs/360-Knowledge-System.md`
- `docs/370-Safety-And-Permissions.md`
- `docs/380-Evaluation-And-Quality.md`
- `docs/390-Identity-And-Collaboration.md`
- `docs/400-Channels-And-Integrations.md`

## Current Reusable Assets

The project already has several platform-ready building blocks:

- desktop chat shell with session persistence
- provider abstraction for `mock`, `ollama`, `openai_compatible`, and `http_backend`
- gateway routing with fallback, cooldown, and request tracking
- gateway-side skill pipeline with phased prompt shaping
- attachment persistence and richer message rendering
- request metrics, token accounting, cost estimation, and provider health inspection
- a first admin surface for gateway operations

These are meaningful assets. The project does not need a rewrite. It needs decoupling and generalization.

## Current Platform Blockers

The main constraint is not the runtime stack. It is the product model.

### 1. Domain-specific project metadata is hard-coded

The core `Project` model, storage schema, gateway request schema, and UI forms all assume these fixed fields:

- `plant`
- `unit`
- `expert_type`

This makes every conversation inherit an energy-operations worldview, even when the underlying provider/gateway stack is generic.

### 2. Prompt shaping is biased toward one operating style

The default skill registry injects:

- project context in energy terms
- a fixed output format: `【结论】【原因分析】【优化建议】【影响评估】`
- operational guardrails tuned for plant analysis

That is useful for one domain, but it is not a safe default for a general assistant.

### 3. Scenario entry points are fixed and domain-bound

The desktop scenario library is currently hard-coded around categories such as:

- `供汽与热力`
- `负荷与调度`
- `能效与设备`

This prevents the app from becoming a configurable assistant workspace for different users, teams, or industries.

### 4. Customization is configuration-driven, not product-driven

Providers and skills can already be loaded from environment JSON, but there is no first-class product model for:

- assistant profiles
- workspace templates
- user-defined prompt packs
- knowledge sources
- tool permissions
- tenant or team presets

The runtime is configurable. The product is not yet customizable.

### 5. Branding and package boundaries need deeper cleanup than naming alone

The repository is now branded as `recon`, but the product model, storage schema, and interaction patterns still reflect the old energy-domain prototype. Naming is now aligned, but deeper platform generalization is still required.

## Recommended Target Product Model

The project should shift from `Project-centric domain console` to `Workspace + Assistant Profile`.

### Core Entities

#### Workspace

A container for:

- conversations
- attached resources
- context values
- enabled tools
- selected assistant profile

Workspaces can still model domain-specific projects, but they should not require it.

#### Assistant Profile

A versioned assistant definition that controls:

- system prompt / persona
- output style
- enabled skills
- preferred providers
- tool policy
- optional starter templates

This becomes the main customization boundary.

#### Conversation

A reusable conversation thread decoupled from domain-only metadata.

#### Resource / Context Item

A generalized replacement for one-off project fields and raw attachments. Examples:

- uploaded files
- notes
- URLs
- structured key-value context
- external records or future knowledge references

#### Skill / Tool Definition

The gateway skill concept should expand into two related concepts:

- prompt-time skills
- executable tools

Skills shape the request. Tools perform actions or retrieve data.

## Recommended Architecture Direction

### Keep

- desktop app for local-first usage
- gateway service as the orchestration boundary
- provider registry and fallback behavior
- request observability and cost tracking

### Change

#### 1. Replace fixed project metadata with flexible context

Move from:

- `name`
- `plant`
- `unit`
- `expert_type`

To something closer to:

- `name`
- `workspace_type`
- `context_json`
- optional typed metadata templates

The first migration should preserve old fields by mapping them into `context_json`.

#### 2. Introduce assistant profiles as a stored entity

Profiles should live in storage instead of only environment variables. A profile should define:

- label and description
- default system prompt
- enabled skill ids
- default provider strategy
- output preferences
- visibility and default flags

This is the missing product primitive for customization.

#### 3. Turn the scenario library into a template library

Replace domain scenes with a generic template system that supports:

- categories
- reusable starter prompts
- parameterized templates
- favorites / recents
- per-profile template packs

#### 4. Separate skill configuration from code defaults

The current skill registry is a good runtime start, but productization requires:

- persisted skill definitions
- explicit parameter schemas
- enable/disable control per profile or workspace
- better distinction between prompt transforms and callable tools

#### 5. Normalize assistant output rules

Structured output should become a profile-level preference, not a global assumption. Examples:

- structured analyst
- concise copilot
- research assistant
- coding assistant
- customer support assistant

#### 6. Prepare for retrieval and tools

To become a serious general assistant, the next capability layer after profiles/templates should be:

- resource indexing / retrieval
- HTTP or API tools
- local command/tool execution policy
- tool audit trail in request records

The gateway already provides a natural place for this.

## Suggested Delivery Phases

### Phase 1: De-domain the core model

- rename product-facing copy from energy console to generic assistant workspace
- replace hard-coded project fields with flexible workspace context
- keep backward compatibility for existing stored records
- convert the fixed scenario library into config-backed template definitions

### Phase 2: Add assistant profiles

- add storage tables and models for assistant profiles
- let each workspace select a profile
- move default prompt shaping and output style into profiles
- allow profile-specific default providers and skills

### Phase 3: Productize skills and templates

- persist skill definitions
- add parameter schemas and UI editing surfaces
- support template packs and starter workflows
- expose profile/template management in the desktop app and gateway admin

### Phase 4: Add generalized knowledge and tools

- resource library with indexing hooks
- profile-level retrieval settings
- gateway tool execution interface
- request records that show which tools and resources were used

### Phase 5: Harden the platform surface

- finish removing domain-first assumptions from the public product surface
- align docs, packaging, and release metadata with `recon`
- decide whether desktop remains primary or a web workspace joins it

## Immediate Implementation Priorities

The first wave should stay narrow and structural:

1. replace `Project` with a backward-compatible `Workspace` model
2. store flexible metadata as JSON instead of fixed `plant / unit / expert_type`
3. move scenario definitions out of `ui.py` into persisted or file-backed templates
4. make default gateway skills generic and profile-driven
5. add an `AssistantProfile` model before building more domain features

If these are done first, later features will land on the right abstraction.

## Risks

- forcing a full rename too early can create churn before the product model is fixed
- keeping domain defaults too long will make every new feature inherit the wrong abstraction
- adding tools before assistant profiles will create brittle behavior coupling
- exposing too much configuration in the UI before the data model stabilizes will slow delivery

## Recommendation

Do not start with a cosmetic rename alone.

Start with model generalization and assistant profiles. The current gateway/provider work is strong enough to support a generic assistant, but the storage model, prompt defaults, and UI entry points must be redesigned first.
