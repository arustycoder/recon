# Identity And Collaboration

## Goal

Define how `recon` supports users, teams, shared workspaces, and ownership so the product can move from local single-user usage toward real collaborative assistant workflows.

## Scope

### Included

- user identity
- team membership
- workspace sharing
- profile visibility
- role-based access
- ownership and audit attribution

### Excluded

- SSO implementation details in the first phase
- complex enterprise org chart modeling
- real-time multiplayer editing

## Core Roles

Recommended initial roles:

- `owner`
- `editor`
- `viewer`
- `operator`

These roles should apply to workspaces first, then to profiles, sources, and future task operations.

## Behavior

- a workspace may be private, shared, or team-scoped
- assistant profiles may be personal, team-scoped, or global
- ownership should determine who can delete, transfer, or publish shared assets
- audit trails should attribute important changes to a user identity, not only to a machine process

## Data Impact

Recommended new entities:

- `users`
- `teams`
- `team_memberships`
- `workspace_acl`
- `profile_acl`

## Migration Direction

- the desktop app may remain effectively single-user at first
- the storage and API model should still prepare for explicit user ids instead of assuming one unnamed operator forever
- local-first mode can map to one default owner account until remote collaboration is added

## Implementation Notes

- identity rules should be enforced in the gateway so future channels inherit the same model
- collaboration should remain asset-centric: workspaces, profiles, sources, and tasks each need ownership and visibility

## Relationship To Existing Docs

- complements `docs/230-Gateway-Admin-Panel.md`
- complements `docs/330-Generic-Assistant-Platform.md`
