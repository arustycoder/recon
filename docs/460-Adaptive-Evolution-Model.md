# Adaptive Evolution Model

## Goal

Define how the assistant improves through use without turning automatic learning into silent, uncontrolled profile drift.

This model is informed by the industry patterns summarized in `docs/450-Industry-Patterns-For-Adaptive-Assistants.md` and by the sources cited there, especially [1][2][3][4][5].

## Core Idea

The assistant should not rewrite its published profile directly.

Instead, behavior should evolve through a separate adaptive layer:

- `published_profile`
- `adaptive_overlays`
- `memory`
- `policy`

The runtime should execute against the effective combination of these layers.

This separation follows the emerging pattern of stable base configuration plus scoped learned state rather than silent global mutation [1][2][3].

## Effective Assistant

Conceptually:

`effective_assistant = published_profile + approved_adaptive_overlays + memory + active_policy`

This keeps the stable baseline separate from learned behavior.

## Adaptation Scopes

- `session`: temporary adaptation for one conversation
- `user`: personal adaptation across sessions
- `workspace`: shared adaptation for one team or project space
- `profile_promotion`: learned behavior promoted into a new profile version

Scoped adaptation reflects the narrower-scope-first pattern seen in project, repository, and managed-memory products [2][3].

## Learning Signals

The system may learn from:

- explicit user feedback
- user edits and rewrites
- repeated follow-up corrections
- accepted or rejected task outputs
- tool retry and fallback patterns
- retrieval and citation usage patterns

These signals are consistent with both productized memory systems and research work on experience- and action-driven adaptation [1][4][5].

## Evolution Pipeline

1. observe usage signals
2. infer an adaptation candidate
3. evaluate the candidate
4. auto-apply or request approval based on scope and risk
5. activate the candidate as an adaptive overlay
6. monitor ongoing quality
7. promote, expire, or roll back the overlay

This pipeline intentionally inserts evaluation and promotion steps before durable mutation, following the industry shift toward governed adaptation [2][4][5].

## Guardrails

- no automatic permission escalation
- no silent mutation of published profiles
- temporary sessions should disable durable learning
- sensitive learning domains may be disabled by policy
- adaptive overlays should support expiration and revalidation

These guardrails align with temporary-chat, admin-control, and freshness patterns already visible in major assistant products [1][2][3].

## Data Impact

Recommended entities:

- `adaptation_events`
- `adaptation_candidates`
- `adaptive_overlays`
- `overlay_evaluations`
- `profile_promotions`
- `rollback_records`

## Client Impact

- users should be able to inspect what the assistant learned
- users should be able to pause, reset, or delete learned behavior
- clients should distinguish base profile behavior from learned overlay behavior

## References

[1] `docs/450-Industry-Patterns-For-Adaptive-Assistants.md`

[2] GitHub Docs, "Copilot memory."  
https://docs.github.com/en/enterprise-cloud@latest/copilot/concepts/agents/copilot-memory

[3] OpenAI, "Memory and new controls for ChatGPT."  
https://openai.com/index/memory-and-new-controls-for-chatgpt/

[4] T. Zhang et al., "MOBIMEM."  
https://arxiv.org/abs/2512.15784

[5] Dynamic evaluation framework for long-term personalized preferences.  
https://arxiv.org/abs/2504.06277
