# Safety And Permissions

## Goal

Define how the system controls data access, tool execution, approvals, and secret use so the assistant remains useful without becoming unsafe or opaque.

This document assumes the adaptive behavior model in `docs/460-Adaptive-Evolution-Model.md` and the industry control patterns summarized in `docs/450-Industry-Patterns-For-Adaptive-Assistants.md` [1][2].

## Scope

### Included

- actor and role-based access checks
- tool risk tiers
- approval policies
- secret handling
- output safety and refusal rules
- auditability

### Excluded

- organization-specific IAM implementation details
- unrestricted tool access by default
- side effects with no audit record

## Policy Layers

- identity policy
- workspace policy
- profile policy
- data visibility policy
- tool execution policy

The effective decision should be the intersection of these layers, not whichever one is most permissive.

Adaptive overlays may refine behavior, but they must never override policy decisions [1].

## Tool Risk Tiers

- `read_only`
- `external_read`
- `local_write`
- `external_write`

Higher-risk tiers require stronger approval and audit requirements.

## Approval Rules

- safe reads may run automatically when policy allows
- external reads should respect allowlists, timeouts, and size bounds
- write actions should be explicit and inspectable
- external writes should require approval in the default policy set
- learned behavior must not auto-promote into new write permissions or broader data visibility [1][2]

## Secret Rules

- secrets must be stored separately from general prompt data
- the runtime should expose only the minimum secret material needed for one invocation
- raw secrets must not appear in conversation history, user-visible traces, or general logs

## Output Safety Rules

- unsupported claims should be downgraded or labeled as uncertain
- policy-restricted requests should fail with explicit refusal reasons
- responses involving sensitive sources or tools should preserve provenance and audit data

## Data Impact

Recommended entities:

- `policy_records`
- `approval_records`
- `audit_events`
- `secret_references`

## Client Impact

- blocked actions should explain why they are blocked
- approvals should show actor, action, target, and risk tier
- users should be able to inspect what the assistant did, not only what it said

## References

[1] `docs/460-Adaptive-Evolution-Model.md`

[2] `docs/450-Industry-Patterns-For-Adaptive-Assistants.md`
