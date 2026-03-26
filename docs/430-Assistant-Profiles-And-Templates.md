# Assistant Profiles And Templates

## Goal

Define how the product packages assistant behavior into reusable profiles and reusable prompt or workflow templates.

This document assumes the profile model described in `docs/330-Generic-Assistant-Platform.md` and the adaptive layering described in `docs/460-Adaptive-Evolution-Model.md` [1][2].

## Scope

### Included

- assistant profile definition
- profile versioning
- template packs
- default capability bindings
- output style and formatting rules
- publish and visibility rules

### Excluded

- raw prompt strings as the only configuration surface
- unversioned profile mutation for production-critical assistants

## Assistant Profile

An assistant profile is the main behavioral unit of the product. A profile should define:

- name and description
- instruction set
- default tone and output style
- enabled tools and risk defaults
- knowledge and retrieval defaults
- memory rules
- task behavior defaults
- visibility and ownership

This follows the industry shift toward explicit base configuration combined with learned state around that base, rather than hidden profile mutation [2][3].

## Effective Behavior

The profile is the stable baseline, not the entire assistant state.

Runtime behavior may additionally depend on:

- approved adaptive overlays
- active memory
- current workspace policy

Published profile versions should remain stable even while learned overlays evolve around them [2].

## Template Types

- starter prompt
- parameterized prompt
- workflow starter
- structured form template

Templates help users begin work faster, but they should not replace the underlying runtime model.

## Versioning Rules

- profiles should be versioned
- template packs should be versioned
- published versions should be immutable
- drafts may evolve until published
- learned overlays may later promote into a new published profile version

Promotion from learned overlay to published version should be governed rather than implicit [2][3].

## Binding Rules

- a workspace may set one default profile
- a request may override the default profile when policy allows
- templates may suggest a profile, but should not silently bypass workspace policy
- profiles may bundle default templates, tools, and retrieval settings

## Data Impact

Recommended entities:

- `assistant_profiles`
- `profile_versions`
- `template_packs`
- `template_items`
- `profile_bindings`
- `adaptive_overlays`
- `profile_promotions`

## Client Impact

- clients should let users select a profile explicitly
- profile and template metadata should be visible before execution
- users should be able to distinguish draft, published, and deprecated profile versions
- clients should expose the difference between base profile behavior and learned behavior

## References

[1] `docs/330-Generic-Assistant-Platform.md`

[2] `docs/460-Adaptive-Evolution-Model.md`

[3] `docs/450-Industry-Patterns-For-Adaptive-Assistants.md`
