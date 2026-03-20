# Skill Pipeline

## Goal

Upgrade gateway skills from fixed prompt snippets into configurable prompt templates with explicit parameter injection, merge rules, and execution phases.

## Scope

### Included

- built-in skills with default enablement
- provider-level default skills
- request-time skill selection
- request-time skill arguments
- deterministic template rendering against request context
- phased execution for `pre_context`, `prompt_shaping`, and `post_processing`

### Excluded

- arbitrary code execution skills
- external tool invocation
- user-authored untrusted sandboxed skills
- dynamic marketplace distribution

## Behavior

- skills render against structured request context such as:
  - project name
  - plant
  - unit
  - expert role
  - session name
  - user message
- each skill can define default parameters
- callers can override skill parameters per request
- each skill belongs to one execution phase:
  - `pre_context`
  - `prompt_shaping`
  - `post_processing`
- `skill_mode=merge` combines:
  - built-in default skills
  - provider default skills
  - request skill ids
- `skill_mode=request_only` disables defaults and only uses explicitly requested skills

## API Impact

### Chat request

The request model now accepts:

- `skill_mode`
- `skill_arguments`

### Skill discovery

`GET /api/skills` now includes:

- `phase`
- `enabled_by_default`
- `parameter_keys`

This makes it possible for future clients to build a real skill picker UI instead of hard-coding assumptions.

## Implementation Notes

- skill templates use safe string substitution so missing values remain visible instead of crashing the request
- rendered `pre_context` and `prompt_shaping` skills are injected into the model request as structured gateway sections
- `post_processing` skills run after the provider reply and can wrap or append deterministic output transforms
- the first phase keeps skills prompt-only and deterministic; tool-using skills can layer on later
