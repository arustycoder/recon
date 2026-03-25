# Safety And Permissions

## Goal

Define how `recon` controls tool execution, data access, approvals, and secrets so the assistant remains useful without becoming unsafe or opaque.

## Scope

### Included

- tool risk tiers
- approval policies
- workspace and profile access rules
- secret handling
- data minimization and auditability
- operator-visible safety decisions

### Excluded

- full enterprise IAM integration in the first phase
- background side effects with no audit trail
- unrestricted tool access by default

## Tool Risk Tiers

Recommended default tiers:

- `read_only`: safe reads such as retrieval and local inspection
- `external_read`: outbound fetches or third-party API reads
- `local_write`: modifies local files or local state
- `external_write`: sends data or changes state outside the product

The higher the tier, the stronger the approval requirement.

## Approval Rules

- read-only actions may run automatically when the workspace policy allows them
- external reads should respect allowlists, timeouts, and source bounds
- local writes should be explicit and inspectable
- external writes should require user approval in the first phase

## Secret Handling

- secrets should be stored separately from general prompt content
- the model should receive only the minimum credential form needed for a specific call
- raw secrets must not appear in chat history, request logs, or user-visible tool traces

## Data Access Rules

- retrieval and tools must honor workspace visibility before execution
- profile defaults must not bypass workspace restrictions
- safety decisions should be enforced in the gateway, not only in the desktop UI

## Audit Model

Important actions should be auditable:

- who requested the action
- which profile and workspace were active
- which tool or source was used
- whether approval was required
- the final outcome

## Data Impact

Recommended new entities:

- `tool_policies`
- `approval_records`
- `audit_events`
- `secret_references`

## Implementation Notes

- the first phase can keep policy evaluation rule-based and explicit
- approval UX should explain why a step is blocked, not only that it is blocked
- safety policy should integrate with task runtime so approval waits become first-class states

## Relationship To Existing Docs

- complements `docs/230-Gateway-Admin-Panel.md`
- complements `docs/330-Generic-Assistant-Platform.md`
