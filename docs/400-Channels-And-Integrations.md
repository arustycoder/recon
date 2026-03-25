# Channels And Integrations

## Goal

Define how `recon` exposes the assistant through multiple clients and integrations without coupling core behavior to the current desktop UI.

## Scope

### Included

- desktop client
- HTTP API
- webhook and callback patterns
- future chat and messaging connectors
- multimodal input as channel payloads
- shared correlation and attachment rules

### Excluded

- implementing every external connector now
- channel-specific business logic that bypasses the gateway

## Channel Model

Every channel should map onto the same core concepts:

- user identity
- workspace
- conversation
- task
- resources
- profile

The channel adapter should translate channel-specific input into the shared gateway model rather than inventing its own workflow.

## Supported Interaction Modes

- synchronous request/response
- streamed response
- asynchronous task creation with later callback or polling

## Integration Surfaces

Recommended first-class surfaces:

- desktop app
- gateway HTTP API
- webhook callbacks for task completion or approval requests
- future connectors for chat platforms and email

## Attachment And Modality Rules

- channels may submit text, files, URLs, and later audio or images
- all non-text inputs should normalize into shared resource records before model use when possible
- channel adapters should preserve source metadata so downstream citations and audits remain accurate

## Implementation Notes

- the gateway should remain the source of truth for orchestration, policies, memory, and task state
- the desktop app should be treated as one client, not the product boundary
- new channels should reuse the same request ids, task ids, and audit model

## Relationship To Existing Docs

- complements `docs/120-Gateway-and-Service-Layer.md`
- complements `docs/290-Attachments-And-Rich-Content.md`
- complements `docs/330-Generic-Assistant-Platform.md`
