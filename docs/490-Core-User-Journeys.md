# Core User Journeys

## Goal

Define the canonical user journeys that make the product understandable from the outside in.

This document translates the product positioning in `docs/480-Product-Positioning-And-User-Segments.md` into concrete interaction paths, using the request and task boundaries defined in `docs/420-Request-Runtime.md` and `docs/350-Task-Runtime.md` [1][2][3].

## Scope

### Included

- workspace setup
- grounded conversation
- task handoff
- approval flow
- learning flow
- team handoff
- recurring or triggered work

### Excluded

- low-level client wireframes
- admin-only operations

## Interaction Ladder

Users should experience four progressively stronger modes of work:

1. `answer`: resolve the request inline
2. `guided action`: use tools or retrieval inside the same foreground interaction
3. `task`: create durable work with steps, artifacts, and review points
4. `automation`: create recurring or event-triggered task creation with visible ownership

The product should make these modes feel like one continuum, not four unrelated features.

## Canonical Journeys

### 1. Start A Workspace

- create or choose a workspace for a project, team, or durable work area
- choose a default assistant profile
- attach initial sources, notes, or templates
- leave with a clear mental model of what context the assistant is operating inside

### 2. Ask A Grounded Question

- ask in conversation
- optionally attach files, URLs, or existing sources
- receive an answer with citations or an explicit signal that evidence is weak
- continue inline when the work remains small and self-contained

### 3. Turn A Request Into Durable Work

- create a task when the ask needs multiple steps, more time, or visible state
- track progress, outputs, and retries without losing the original request context
- publish the result back into the conversation or workspace

### 4. Review Or Approve A Risky Action

- see what action is proposed, why it needs approval, and what workspace or source scope it affects
- approve, deny, or defer the step
- keep a durable task and audit record of the decision

### 5. Correct And Teach The Assistant

- edit a reply, provide direct feedback, or correct a repeated behavior
- let the system propose memory or learned-behavior changes at the right scope
- keep the distinction between remembered facts and learned preferences visible

### 6. Share And Handoff Work

- share a workspace, source library, or task with teammates
- assign or transfer task responsibility while keeping ownership and audit attribution clear
- let multiple people work with the same assistant context without losing traceability

### 7. Repeat Work Through Automation

- take a repeatable task pattern and bind it to a schedule or external trigger
- keep each run visible as a task or task run
- allow pause, review, and approval without turning the assistant into hidden background software

## Decision Rules

Stay inline when:

- the work fits one foreground interaction
- no durable artifact or follow-up state is needed
- no approval or long wait is expected

Create a task when:

- the work needs multiple steps or durable progress
- the result should be inspectable later
- approvals, retries, or handoff are likely

Create automation when:

- the task pattern repeats predictably
- ownership, workspace, and policy are already clear
- the user can tolerate task-based asynchronous execution

## Product Implications

- the product home should highlight workspaces, active tasks, approvals, and sources, not only chat history
- chat should feel like the lightest entry point into a larger work system
- users should never have to guess whether something remained inline, became a task, or became automation

## References

[1] `docs/480-Product-Positioning-And-User-Segments.md`

[2] `docs/420-Request-Runtime.md`

[3] `docs/350-Task-Runtime.md`
