# Task Runtime

## Goal

Define how the assistant executes work that is too long, too stateful, or too approval-heavy for one foreground response.

This document assumes the request lifecycle in `docs/420-Request-Runtime.md` and the approval model in `docs/370-Safety-And-Permissions.md` [1][2].

## Scope

### Included

- task creation from any channel
- background execution
- step tracking
- approval checkpoints
- retries, cancellation, and resume
- task outputs and artifacts

### Excluded

- unrestricted autonomous multi-agent swarms
- hidden side effects with no task record
- distributed job orchestration requirements in the first architecture cut

## Core Objects

### Task

A user-visible unit of work with an owner, scope, goal, and status.

### Task Run

A concrete execution attempt for one task.

### Task Step

A bounded stage such as planning, retrieval, tool use, synthesis, or approval wait.

### Task Artifact

A durable output such as a report, file, citation set, or structured result.

## Status Model

- `draft`
- `queued`
- `running`
- `waiting_approval`
- `blocked`
- `completed`
- `failed`
- `canceled`

## Behavior

- a request may complete inline or create a task
- side-effecting steps should support approval gates before execution
- retries should create a new run while preserving task identity
- canceled tasks should remain inspectable
- completed tasks may publish a result back to the originating conversation or channel
- approval-gated steps should inherit the same policy constraints as foreground requests [2]

## Execution Rules

- each step should record intent, inputs, outputs, and error state
- long-running tasks should be resumable after process restarts
- tasks should be idempotent at the step boundary where possible
- approval waits should be modeled as first-class task states, not ad hoc pauses

## Data Impact

Recommended entities:

- `tasks`
- `task_runs`
- `task_steps`
- `task_artifacts`
- `task_approvals`

Suggested fields:

- owner, workspace, and conversation linkage
- requested profile and policy context
- current status and active step
- approval state
- timestamps
- output summary
- correlation ids for request, tool, and audit events

## Client Impact

- clients should show tasks separately from transient chat output
- task details should expose steps, approvals, outputs, and errors
- tasks should be pollable and subscribable across channels

## References

[1] `docs/420-Request-Runtime.md`

[2] `docs/370-Safety-And-Permissions.md`
