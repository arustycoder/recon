# Collaboration And Automation Model

## Goal

Define how the product supports shared work, approvals, ownership, and repeatable automation without turning assistant execution into invisible background behavior.

This document builds on the task runtime in `docs/350-Task-Runtime.md`, the identity model in `docs/390-Identity-And-Collaboration.md`, and the shared channel model in `docs/400-Channels-And-Integrations.md` [1][2][3].

## Scope

### Included

- task ownership and assignment
- workspace collaboration
- approval inbox behavior
- recurring and event-triggered work
- automation visibility and control

### Excluded

- real-time co-authoring
- unconstrained autonomous agent swarms
- organization-wide workflow engines beyond the assistant boundary

## Collaboration Model

The shared unit of work is the workspace, but the shared unit of execution is the task.

This means:

- knowledge, profiles, and policies may be shared at workspace scope
- responsibility should still attach to concrete tasks, approvals, and artifacts
- ownership, edit rights, and task responsibility must remain distinct concepts

## Core Collaborative Surfaces

### Shared Workspace

A workspace should expose shared sources, active tasks, default profiles, and recent outputs.

### Task Responsibility

Tasks should support:

- creator
- current responsible actor
- watchers or followers
- approval owner when a step is blocked on human review

### Approval Inbox

Approvals should feel like first-class work items rather than hidden modal interruptions.

They should show:

- what is being approved
- why approval is required
- what scope and side effects are involved
- what happens after approval or denial

## Automation Model

Automation should be modeled as managed task creation, not as a separate hidden execution universe.

Each automation run should resolve to:

- one workspace
- one profile context
- one policy context
- one visible task or task run

## Automation Levels

### Manual Reuse

A user reruns a known task pattern intentionally.

### Scheduled Automation

A task pattern runs on a schedule with visible ownership and outputs.

### Event-Triggered Automation

An external event creates a task using a predefined workspace and profile binding.

### Approval-Bounded Continuous Work

The system may keep processing repeat work, but risky or side-effecting steps still stop at approval gates.

## Product Rules

- automations should be easy to inspect, pause, disable, and audit
- automation should inherit the same policy boundaries as interactive work
- automation should publish visible outputs, notifications, or approval requests rather than silent mutations
- shared automations should have clear owners and scopes
- learning from automation should be more conservative than learning from explicit user interaction

## Product Implications

- the product should have a clear inbox for tasks, approvals, and automation runs
- connectors and APIs should map into the same task and approval model rather than bypassing it
- shared work should look like work with owners and histories, not like unexplained assistant magic

## References

[1] `docs/350-Task-Runtime.md`

[2] `docs/390-Identity-And-Collaboration.md`

[3] `docs/400-Channels-And-Integrations.md`
