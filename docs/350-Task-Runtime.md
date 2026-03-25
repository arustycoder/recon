# Task Runtime

## Goal

Define how `recon` executes multi-step assistant work that cannot be completed inside one foreground chat request.

## Scope

### Included

- task creation from chat or API
- background execution
- step tracking
- approval checkpoints
- retries, cancellation, and resume
- user-visible task state

### Excluded

- unrestricted autonomous agent swarms
- cron-style scheduling in the first phase
- distributed queue infrastructure

## Core Model

### Task

A user-facing unit of work such as:

- summarize a document set
- compare providers
- gather references
- run a tool-backed workflow

### Task Run

A concrete execution attempt for one task.

### Task Step

A tracked unit inside one run, such as planning, retrieval, tool call, synthesis, or approval wait.

## Status Model

Recommended task statuses:

- `draft`
- `queued`
- `running`
- `waiting_approval`
- `blocked`
- `completed`
- `failed`
- `canceled`

## Behavior

- a chat turn may return a final answer or create a task when the work is long-running
- side-effecting steps should support approval gates before execution
- each step should record input summary, output summary, and error state
- retries should attach to the same task but create a new run record
- canceled tasks should remain inspectable after cancellation

## Data Impact

Recommended new entities:

- `tasks`
- `task_runs`
- `task_steps`
- `task_approvals`

Suggested tracked fields:

- task identity and workspace/session linkage
- requested profile and provider strategy
- current status and active step
- approval state
- correlation ids for tool calls and gateway requests
- timestamps and summarized outputs

## UI Impact

- desktop should show tasks separately from raw chat history
- a task detail view should expose steps, approvals, outputs, and errors
- completed tasks may post a summary back into the conversation that created them

## Implementation Notes

- the gateway should own task execution so all clients share one runtime model
- the first phase can use in-process execution with persisted state
- request observability should extend to tasks instead of creating a parallel opaque subsystem

## Relationship To Existing Docs

- complements `docs/150-Skill-Pipeline.md`
- complements `docs/170-Gateway-Observability.md`
- complements `docs/330-Generic-Assistant-Platform.md`
