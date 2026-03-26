# Identity And Collaboration

## Goal

Define how the product supports users, teams, ownership, sharing, and role-based collaboration.

This document assumes the workspace-centered architecture in `docs/330-Generic-Assistant-Platform.md` and the policy layering in `docs/370-Safety-And-Permissions.md` [1][2].

## Scope

### Included

- user identities
- team membership
- service actors
- workspace sharing
- profile and source visibility
- ownership and audit attribution

### Excluded

- SSO provider implementation details
- real-time co-editing requirements
- enterprise org hierarchy modeling beyond teams

## Core Actors

- `user`
- `team`
- `service_actor`

## Core Roles

- `owner`
- `editor`
- `viewer`
- `operator`

Roles should apply consistently to workspaces, profiles, sources, and tasks.

## Ownership Rules

- every durable asset should have an owner scope
- assets may be private, shared, team-scoped, or global
- destructive actions should require owner-level or operator-level permission
- audit events must attribute important changes to a named actor
- adaptive overlays and profile promotions should inherit ownership and visibility from their scope [1][2]

## Data Impact

Recommended entities:

- `users`
- `teams`
- `team_memberships`
- `service_actors`
- `workspace_acl`
- `profile_acl`
- `source_acl`

## Client Impact

- clients should show who owns a workspace, profile, source, or task
- sharing state should be visible before a user publishes or deletes an asset

## References

[1] `docs/330-Generic-Assistant-Platform.md`

[2] `docs/370-Safety-And-Permissions.md`
