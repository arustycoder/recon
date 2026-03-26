# Industry Patterns For Adaptive Assistants

## Goal

Capture the industry patterns that have already emerged around adaptive assistants so product design can follow validated directions instead of inventing unstable behavior from scratch.

The patterns below are synthesized from official product documentation and published research, primarily [1][2][3][4][5][6][7][8][9][10][11].

## Observed Convergence

Across major assistant products, the industry is converging on the following patterns:

- explicit base configuration plus implicit learning from usage [1][3][5][7]
- scoped adaptation before global adaptation [7][8][9]
- strong user and admin controls around learned state [1][4][6][7]
- temporary or incognito modes that disable persistence [4][7]
- sensitive-topic exclusions for some learned behavior [6]
- learned state stored outside model weights [1][5][7][8]
- evaluation and review before durable promotion [8][10][11]

## Stable Product Patterns

### 1. Base Profile Plus Learned State

Products increasingly combine:

- explicit instructions, styles, or project rules
- learned preferences from history or behavior

The learned layer complements the base profile instead of replacing it.

Source examples: [1][3][5][7]

### 2. Scope Before Scale

Adaptation usually starts in the narrowest useful scope:

- user
- project
- repository
- workspace

Global cross-scope learning is treated as higher risk.

Source examples: [7][8][9]

### 3. Control Surfaces Are Mandatory

Adaptive products now commonly expose:

- memory or preference inspection
- delete or forget actions
- temporary or incognito sessions
- admin disablement for managed environments

Source examples: [1][4][6][7]

### 4. Learned State Needs Freshness Rules

Adaptive coding and work assistants increasingly attach retention or revalidation rules to learned state. Durable behavior should not live forever without evidence that it is still correct.

Source examples: [8]

### 5. Automatic Extraction Is Safer Than Silent Promotion

Industry products are more comfortable with:

- auto-detected memory candidates
- auto-generated project rules
- repo-specific inferred guidance

than with silent global profile mutation.

Source examples: [8][9]

### 6. Evaluation Is Becoming Part Of The Loop

Once behavior evolves over time, teams need:

- regression checks
- promotion criteria
- rollback
- traceability

without that, adaptive behavior drifts.

Source examples: [10][11]

## Anti-Patterns To Avoid

- one global memory bucket for all contexts
- hidden behavior drift with no inspectable diff
- mixing memory, permissions, and profile mutation into one mechanism
- durable learning with no expiration or revalidation
- automatic promotion of risky behavior without evaluation

## Product Implications For Recon

`recon` should follow the same shape:

- published base profiles
- scoped adaptive overlays
- explicit control over what is learned
- temporary no-learning mode
- promotion and rollback for durable behavior changes
- evaluation before broad rollout

## References

[1] OpenAI, "Memory and new controls for ChatGPT."  
https://openai.com/index/memory-and-new-controls-for-chatgpt/

[2] OpenAI Help Center, "ChatGPT release notes."  
https://help.openai.com/en/articles/6825453-chatgpt-release-notes

[3] Google, "Gemini personalization."  
https://blog.google/products-and-platforms/products/gemini/gemini-personalization/

[4] Google, "Temporary chats and privacy controls for Gemini."  
https://blog.google/products-and-platforms/products/gemini/temporary-chats-privacy-controls/

[5] Microsoft, "Introducing Copilot Memory."  
https://techcommunity.microsoft.com/blog/microsoft365copilotblog/introducing-copilot-memory-a-more-productive-and-personalized-ai-for-the-way-you/4432059

[6] Microsoft Support, "Microsoft Copilot privacy controls."  
https://support.microsoft.com/en-us/topic/microsoft-copilot-privacy-controls-8e479f27-6eb6-48c5-8d6a-c134062e2be6

[7] Anthropic, "Memory for Claude."  
https://claude.com/blog/memory

[8] GitHub Docs, "Copilot memory."  
https://docs.github.com/en/enterprise-cloud@latest/copilot/concepts/agents/copilot-memory

[9] GitHub Docs, "Add repository custom instructions for GitHub Copilot."  
https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions

[10] T. Zhang et al., "MOBIMEM."  
https://arxiv.org/abs/2512.15784

[11] Dynamic evaluation framework for long-term personalized preferences.  
https://arxiv.org/abs/2504.06277
