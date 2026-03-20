# Skill Execution Phases

## Goal

Make skill behavior more predictable by separating context injection, prompt shaping, and deterministic post-processing.

## Scope

### Included

- `pre_context` skills
- `prompt_shaping` skills
- `post_processing` skills
- phase visibility in persisted gateway request records

### Excluded

- external tool execution
- async background skill workers
- human-in-the-loop checkpoints

## Phase Behavior

### `pre_context`

- injects domain context before the user message
- suited for project metadata, run conditions, and session context

### `prompt_shaping`

- adds output constraints or analysis style instructions
- suited for structured output, safety language, and role framing

### `post_processing`

- runs after the model returns
- can wrap, append, or normalize the final answer deterministically
- current streaming implementation buffers provider chunks when post-processing is active, then emits the processed result

## Data And API Impact

- `GET /api/skills` now returns `phase`
- `GET /api/requests/{request_id}` persists the current `phase`

## Implementation Notes

- phases are deterministic and intentionally simpler than graph orchestration
- this is the bridge between prompt-only skills and future tool-capable workflows
