---
name: build-info-card
description: Create single-page editorial information cards, architecture cards, and summary posters from design docs, notes, diagrams, or structured discussion. Use when Codex needs to compress dense content into a visually organized HTML card with strong hierarchy, concise copy, numbered modules, stack or compare layouts, and optional citations.
---

# Build Info Card

## Overview

Turn structured content into a one-page card that can be scanned quickly.

Default to a single self-contained HTML file with inline CSS unless the user asks for another format.

Read [references/layout-patterns.md](references/layout-patterns.md) when choosing the card structure. Read [references/content-compression.md](references/content-compression.md) when reducing source material into title, thesis, and modules. Reuse [assets/editorial-card-template.html](assets/editorial-card-template.html) when it is faster than starting from scratch.

## Workflow

### 1. Define the source and output

- Identify the canonical source: doc set, notes, diagram, or conversation summary.
- Identify the target artifact: HTML card, markdown mockup, or visual copy block.
- If no path is given, place the output in the current workspace `docs/` directory when one exists.

### 2. Reduce the content before designing

- Extract one clear headline.
- Extract one core judgement or thesis.
- Extract 4-9 supporting modules.
- Extract one closing conclusion or usage note.
- Keep each module short enough to scan in a few seconds.
- Do not mirror the source document structure mechanically; compress it into the few ideas that matter.

### 3. Choose the layout that matches the content

- Use `stack` when the subject is layered architecture, system boundaries, or top-down explanation.
- Use `grid` when the subject is a set of parallel insights, principles, or capability blocks.
- Use `compare` when the subject is options, tradeoffs, or before/after states.
- Use `timeline` when the subject is sequence, evolution, or roadmap.
- Use `field-guide` when the subject is a concise guide with numbered observations.

### 4. Build the visual hierarchy

- Use a large headline area that establishes the topic in one glance.
- Use one accent color and one neutral paper-like background unless the user supplies a stronger visual system.
- Use expressive serif typography for major headlines and a clean sans-serif for supporting copy.
- Use borders, rules, bands, or blocks to separate modules instead of heavy decorative effects.
- Favor intentional editorial composition over generic dashboard styling.
- If the user supplies a reference image, borrow the compositional logic, not the literal wording.

### 5. Build the deliverable

- Default to one self-contained HTML file with inline CSS.
- Keep assets optional. Do not depend on external CDNs unless the user asks.
- Make the first viewport useful on desktop and readable on mobile.
- Keep the card printable when possible.
- When the card is derived from cited design docs or research notes, preserve a compact reference area instead of dropping source context.

### 6. Review before handing off

- Check that the scan order is obvious.
- Check that the thesis is visible without reading the whole card.
- Check that modules are balanced and not overcrowded.
- Check that the card still reads correctly without the surrounding conversation.
- Remove any redundant labels, repeated wording, or low-value copy.

## Writing Rules

- Prefer compressed declarative sentences over long paragraphs.
- Prefer one idea per block.
- Prefer naming over explaining when the audience can infer the rest.
- Use numbered modules only when the sequence or catalog structure helps scanning.
- Keep the card thesis-driven. Every block should support the central judgement.

## Output Patterns

### Stack Card

- Best for system architecture and layered products.
- Put the stack on one side and the interpretive notes on the other.
- Use the foundation or governance layer as a visual anchor.

### Interpretation Card

- Best for summarizing a tutorial, paper, or framework.
- Use a large title, one thesis block, and a grid of numbered findings.

### Compare Card

- Best for alternatives, migration choices, or before/after analysis.
- Keep the comparison axis explicit and symmetrical.

### Timeline Card

- Best for progress, history, or roadmap material.
- Keep the time or phase labels visually stronger than the descriptive text.

## Notes

- If the request is primarily about content structure, solve the structure first and the styling second.
- If the request is primarily about presentation, keep the copy extremely short.
- If the card is about architecture, prefer stack or layered composition over process diagrams.
