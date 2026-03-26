# Product Positioning And User Segments

## Goal

Define what `recon` is for, who it is for first, and what kind of assistant product it is not.

This document narrows the workspace-centered architecture in `docs/330-Generic-Assistant-Platform.md` using the collaboration and channel boundaries defined in `docs/390-Identity-And-Collaboration.md` and `docs/400-Channels-And-Integrations.md` [1][2][3].

## Scope

### Included

- product thesis
- primary users and teams
- initial product wedge
- non-goals
- packaging stance

### Excluded

- pricing and commercial packaging
- brand positioning and marketing copy
- implementation sequencing

## Product Thesis

`recon` is a workspace-centered AI assistant for knowledge-heavy work that moves between conversation, retrieval, task execution, approvals, and collaboration.

It is not primarily a consumer companion, a generic model playground, or an unrestricted autonomous employee.

## Primary Outcomes

- keep working context durable across sessions
- ground answers in managed sources
- turn ambiguous requests into trackable work
- learn stable preferences without silent drift
- let teams share context, approvals, and results

## Primary User Segments

### Expert Individual

A single user with durable projects, reusable working styles, and repeated outputs.

Typical needs:

- one place for notes, files, links, and conversations
- a preferred assistant working mode
- repeatable research, writing, or operational support

### Small Operational Team

A team that shares sources, tasks, approvals, and output expectations inside one workspace.

Typical needs:

- shared knowledge and reusable assistant profiles
- visible task ownership and review points
- bounded automations instead of opaque background activity

### Embedded Or Platform Team

A product or operations team that needs the assistant runtime through API or controlled integrations after the core workspace model is stable.

Typical needs:

- consistent request and task semantics
- inspectable traces and policy enforcement
- predictable profile and workspace binding

## Initial Product Wedge

The first strong wedge should be expert individuals and small teams doing repeated knowledge-heavy work with bounded execution.

Typical work looks like:

- answer with evidence from managed sources
- assemble briefs, reports, or summaries
- continue work across sessions instead of starting from scratch
- turn larger asks into inspectable tasks
- use approvals for side effects or shared decisions

This wedge fits the current architecture better than a broad “assistant for everything” story because the product is strongest where workspace context, retrieval, tasks, and governed learning all matter together.

## Product Stance

- `workspace` is the primary home, not the conversation list
- `profile` is a reusable working mode, not a novelty persona
- `task` is a durable work record, not hidden agent behavior
- `automation` should create inspectable task runs, not silent background execution
- `adaptive learning` is a governed product feature, not invisible model drift

## Non-Goals

- consumer companionship as the initial product
- unrestricted autonomous delegation with no approval boundary
- a thin chat wrapper over third-party model APIs
- connector-first bot distribution before the core workspace experience is strong
- profile marketplace mechanics as the first wedge

## Packaging Stance

- `personal`: one user with durable workspaces and learned preferences
- `team`: shared workspaces, approvals, source libraries, and task collaboration
- `platform`: API and integration surfaces after first-party flows are stable

## References

[1] `docs/330-Generic-Assistant-Platform.md`

[2] `docs/390-Identity-And-Collaboration.md`

[3] `docs/400-Channels-And-Integrations.md`
