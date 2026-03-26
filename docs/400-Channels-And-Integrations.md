# Channels And Integrations

## Goal

Define how the assistant is delivered through multiple clients and integrations without coupling core behavior to any one interface.

This document assumes the shared runtime contract defined in `docs/330-Generic-Assistant-Platform.md` and the canonical request lifecycle in `docs/420-Request-Runtime.md` [1][2].

## Scope

### Included

- first-party clients
- HTTP API
- webhook and event callbacks
- future chat and messaging connectors
- multimodal input normalization
- shared request, task, and approval contracts

### Excluded

- connector-specific business logic in the core runtime
- channel-specific policy bypasses

## Channel Types

- web client
- desktop client
- mobile client
- direct API client
- connector client such as chat, email, or workflow tools

## Canonical Contracts

Every channel should map onto the same core concepts:

- actor
- workspace
- conversation
- request
- task
- resource
- profile

## Supported Interaction Modes

- synchronous response
- streamed response
- asynchronous task creation
- approval request and approval response
- event subscription or polling

## Modality Rules

- text, files, URLs, images, and audio should normalize into shared resource records when possible
- channel adapters should preserve source metadata
- channels may differ in presentation, but not in orchestration semantics
- temporary or no-learning channel modes should still map onto the same request and policy model [2]

## Client Responsibilities

- collect input
- present streaming output
- surface approvals, citations, and task state
- capture feedback

## Runtime Responsibilities

- policy enforcement
- context assembly
- retrieval
- tool use
- task execution
- persistence

## Data Impact

Recommended entities:

- `channel_bindings`
- `channel_sessions`
- `event_subscriptions`

## References

[1] `docs/330-Generic-Assistant-Platform.md`

[2] `docs/420-Request-Runtime.md`
