# Agentic System Landscape Tracker

## Goal

跟踪对 `recon` 最有参考价值的 agentic system 开源项目与 SDK 进展，重点关注这些维度：

- runtime 与 orchestration 形态
- multi-agent 与 handoff 能力
- workflow durability 与 human-in-the-loop
- observability / tracing / control plane
- extensibility、tooling、UI surface
- 对 `recon` 路线的直接启发

## Scope

### Included

- `badlogic/pi-mono`
- `langchain-ai/langgraph`
- `openai/openai-agents-js`
- `microsoft/autogen`
- `crewAIInc/crewAI`
- `huggingface/smolagents`
- `microsoft/agent-framework`（作为方向性 watchlist）

### Excluded

- 闭源 agent products
- 仅做模型封装、没有 agent runtime 的轻量 SDK
- 学术 benchmark 项目

## Snapshot Method

- 快照日期：`2026-03-30`
- 只采用官方 README、官方文档、官方 release、官方仓库元数据作为引用依据
- 表中 `Signal` 列属于基于官方定位与近期活跃度的归纳，不等于项目方原话

## Why This Matters To Recon

`recon` 已经有 provider abstraction、gateway routing、request observability、skill pipeline、generic assistant platform 等基础。[R1][R2][R3]  
下一阶段的关键不是“再造一个聊天壳”，而是判断哪些能力应该成为产品主线，哪些能力应该保持为可插拔选项。

## 2026-03-30 Snapshot

### Market Snapshot

| Project | Official positioning | Lang | Stars | Latest release | Signal | Refs |
| --- | --- | --- | ---: | --- | --- | --- |
| `pi-mono` | AI agent toolkit，含 coding agent CLI、统一 LLM API、TUI / web UI、Slack bot、vLLM pods | TypeScript | 29.3k | `v0.64.0` on 2026-03-29 | open-source coding harness stack，0.x 迭代很快 | [P0][P1] |
| `LangGraph` | low-level orchestration framework for long-running, stateful agents | Python | 27.9k | `langgraph-cli==0.4.19` on 2026-03-20 | workflow / durability / LangSmith 绑定很强 | [L0][L1] |
| `OpenAI Agents JS` | lightweight framework for multi-agent workflows and voice agents | TypeScript | 2.5k | `v0.8.1` on 2026-03-25 | JS/TS 侧的新一代官方 agents SDK，tracing 与 handoffs 是核心卖点 | [O0][O1] |
| `AutoGen` | framework for creating multi-agent AI applications | Python | 56.4k | `python-v0.7.5` on 2025-09-30 | 仍活跃，但官方已明确建议新用户优先看 Microsoft Agent Framework | [A0][A1] |
| `CrewAI` | fast multi-agent automation framework，强调 Crews、Flows、AMP Suite | Python | 47.6k | `1.12.2` on 2026-03-26 | orchestration 与 enterprise control plane 叙事非常强 | [C0][C1] |
| `smolagents` | barebones library for agents that think in code | Python | 26.3k | `v1.24.0` on 2026-01-16 | 极简 code-agent 路线，MCP / sandbox / Hub 分发能力突出 | [S0][S1] |
| `Microsoft Agent Framework` | framework for building, orchestrating and deploying AI agents and multi-agent workflows with Python and .NET | Python + .NET | 8.3k | `python-1.0.0rc5` on 2026-03-20 | Microsoft 新主线，强调 graph workflows、OTel、DevUI、AutoGen migration | [M0][M1] |

### What The Market Is Converging On

#### 1. Agent runtime 正在从 “single agent + tools” 转向 “workflow / graph / multi-agent”

`LangGraph` 明确把 durable execution、memory、human-in-the-loop、deployment 放在一线能力；`OpenAI Agents JS` 把 handoffs、agents as tools、sessions、tracing 放进 core concepts；`CrewAI` 把 `Crews` 和 `Flows` 明确拆成两条产品线；`Microsoft Agent Framework` 直接把 graph-based workflows 放在 highlights 里。[L1][O1][C1][M1]

#### 2. Observability / tracing / control plane 正在从附属能力变成默认期待

`LangGraph` 的官方叙事里把 LangSmith debugging 和 deployment 明确列成核心理由；`OpenAI Agents JS` 把 tracing 列为 core concept；`CrewAI` 在 AMP / Control Plane 中直接强调 tracing & observability；`Microsoft Agent Framework` 则把 built-in OpenTelemetry integration 和 DevUI 放在 highlights 中。[L1][O1][C1][M1]

#### 3. MCP 正在主流化，但并非所有项目都接受它成为内核

`OpenAI Agents JS` 的 tools 文档入口直接覆盖 `functions, MCP, hosted tools`；`AutoGen` 在 README 里给出 `McpWorkbench` 示例；`smolagents` 明确支持从 MCP server 加载工具。相对地，`pi-coding-agent` 在其 Philosophy 中明确写了 `No MCP`，主张优先使用 CLI tools + README 风格的 skills，或由 extension 自行添加 MCP 支持。[O1][A1][S1][P2]

#### 4. “coding harness” 已经和 “general orchestration framework” 分化成两条路线

`pi-mono` 把 coding agent CLI、TUI、Web UI、Slack bot、vLLM pod management 都放进一个套件；`smolagents` 虽然强调 `CodeAgent`，但它关注的是“用代码作为 agent action”，不是本地开发工作台；`LangGraph`、`CrewAI`、`OpenAI Agents JS`、`Microsoft Agent Framework` 更偏 runtime / workflow / platform，而不是 terminal-native coding UX。[P1][P2][P3][P4][P5][S1][L1][O1][C1][M1]

#### 5. 平台整合正在加速，尤其是 Microsoft 生态

`AutoGen` README 顶部已经明确提示新用户优先查看 `Microsoft Agent Framework`；`Microsoft Agent Framework` README 同时提供从 Semantic Kernel 和 AutoGen 的 migration guides。这说明多代理研究框架正在向更统一的工程化平台收敛。[A1][M1]

## Capability Comparison

### Execution And Orchestration

| Project | Multi-agent / handoff | Durable workflow / checkpoints | Human-in-the-loop | Observability / tracing | Evidence |
| --- | --- | --- | --- | --- | --- |
| `pi-mono` | `Extension/example-based`，不是 core default | `Conversation/session persistence` 强，但不是 workflow engine | `Interactive UI + extension UI`，非统一审批框架 | `Usage / cost / session` 有，缺少独立 tracing platform 叙事 | [P2][P3][P4][P5] |
| `LangGraph` | 强，围绕 graph / subgraph / deep agents 生态展开 | 强，durable execution 是 headline feature | 强，interrupt / HITL 是 headline feature | 强，但主要经由 LangSmith | [L1] |
| `OpenAI Agents JS` | 强，handoffs 与 agents-as-tools 是 core concept | 中，sessions 明确存在，但 workflow durability 不是主叙事 | 强，官方单列 human-in-the-loop | 强，tracing 是 core concept | [O1] |
| `AutoGen` | 强，multi-agent orchestration 是 headline；AgentTool / teams 是主路线 | 中，适合 orchestration，但 README 顶层不是 durability-first 叙事 | 中到强，强调 alongside humans | 中，生态里有 Studio，但 README 顶层更强调 agents / orchestration / MCP | [A1] |
| `CrewAI` | 强，`Crews` 是主能力 | 强，`Flows` 直接面向 production architecture | 中，官方首页更强调 automation 和 control，而不是 HITL | 强，AMP / Control Plane 把 tracing 放到一线 | [C1] |
| `smolagents` | 轻量，可组合但不是重 orchestration 定位 | 轻量，主打简单与代码动作 | 非 headline capability | 轻量，没有 control plane 叙事 | [S1] |
| `Microsoft Agent Framework` | 强，multi-agent workflows + graph orchestration 是 headline | 强，workflow 中直接写 checkpointing 和 time-travel | 强，workflow highlights 直接写 human-in-the-loop | 强，built-in OpenTelemetry + DevUI | [M1] |

### Product Surface And Extensibility

| Project | Local coding harness | UI / control plane | Extensibility posture | Deployment posture | Evidence |
| --- | --- | --- | --- | --- | --- |
| `pi-mono` | 很强，`pi-coding-agent` 是核心产品面 | `TUI + web UI + Slack bot`，但不是统一 control plane | `Extensions + skills + prompt templates + themes + packages` | `pi-pods` 明确面向 vLLM / GPU pods | [P1][P2][P5][P6] |
| `LangGraph` | 否 | 主要依赖 LangSmith / Deployment 生态 | graph composition + LangChain ecosystem | 明确 production deployment | [L1] |
| `OpenAI Agents JS` | 否 | tracing UI / voice agents 文档，但不是开箱业务 UI | tools, MCP, hosted tools, guardrails, handoffs | 偏 SDK 集成，不主打 self-host infra | [O1] |
| `AutoGen` | 否 | `AutoGen Studio` | AgentChat + extensions + MCP workbench | 偏 application framework，不主打 infra ops | [A1] |
| `CrewAI` | 否 | `AMP Suite` / `Crew Control Plane` | `Crews` + `Flows` 两层抽象 | 强烈面向 enterprise deployment | [C1] |
| `smolagents` | 不是 harness，但有强 code-agent / sandbox 属性 | 无明显 control plane 主叙事 | Hub、MCP、LangChain、Space、LiteLLM 集成很开放 | 支持多种 sandbox，与 infra 耦合较轻 | [S1] |
| `Microsoft Agent Framework` | 否 | `DevUI` | Python + .NET + middleware + workflows | 明确 build / orchestrate / deploy | [M1] |

## Focused Assessment Of `pi-mono`

### Where `pi-mono` Is Strong

- 它不是单一 SDK，而是完整 agent stack：`pi-ai`、`pi-agent-core`、`pi-coding-agent`、`pi-web-ui`、`pi-tui`、`pi-mom`、`pi-pods` 同时存在。[P1]
- 对本地 coding workflow 很完整：内建读写编辑/bash、interactive mode、session tree、fork、compaction、SDK、RPC mode。[P2]
- extensibility 非常强：官方明确把 `Extensions`、`Skills`、`Prompt Templates`、`Themes`、`Pi Packages` 作为一等自定义边界。[P2]
- provider 与 self-host 路线都覆盖：`pi-ai` 统一多 provider，`pi-pods` 直接覆盖 vLLM / GPU pod 场景。[P3][P6]

### Where `pi-mono` Is Not Trying To Compete

- 官方 Philosophy 明确写了 `No MCP`、`No sub-agents`、`No plan mode`、`No permission popups`、`No built-in to-dos`、`No background bash`；虽然可以靠 extension / package 做出来，但它们不是内核承诺。[P2]
- 它有 session persistence 和 UI-level interaction，但没有像 LangGraph / MAF / CrewAI / OpenAI Agents 那样把 workflow durability、tracing、control plane 作为 headline product story。[P2][L1][O1][C1][M1]

### What `recon` Should Learn From `pi-mono`

- 本地优先 UX：terminal / desktop 侧可直接借鉴它对 session、context、skill、tool-call 可见性的处理。[P2][P5]
- 自定义边界：`extension + skill + package` 三层机制值得参考。
- 不应盲目复制其 “No MCP / No plan mode” 哲学。`recon` 的目标更接近通用 assistant platform；在这种目标下，MCP、workflow、observability 更适合作为可选但正式支持的边界，而不是完全排除。[P2][R2][R3]

## Implications For `recon`

### 1. `recon` 需要把 observability / eval 保持为产品主线

行业头部项目正在把 tracing、metrics、debugging、control plane 前置为默认能力，而不是开发后期再补。[L1][O1][C1][M1]  
这和 `recon` 现有的 `docs/170-Gateway-Observability.md`、`docs/200-Gateway-Metrics-And-Costs.md`、`docs/380-Evaluation-And-Quality.md` 是同方向，应该继续强化。[R2][R3]

### 2. `recon` 应把 “interactive workbench” 和 “workflow runtime” 分层

`pi-mono` 在 workbench / coding harness 上很强，`LangGraph` / `CrewAI` / `MAF` 在 workflow runtime 上更强。`recon` 不必二选一，但应该明确桌面端、gateway、workflow/state engine 的边界。

### 3. `recon` 的 tool boundary 不应只押注一种协议

MCP 的主流化值得跟进，但 `pi-mono` 也证明“README + CLI tools + local skills”依然很有生命力。[O1][A1][S1][P2]  
更稳妥的路线是：

- 内部统一 tool abstraction
- 外部同时适配 `local skills / HTTP tools / MCP`
- 在 UI 和审计层统一展示调用轨迹

### 4. 如果 `recon` 未来要做企业协作，control plane 不能只是运维页

`CrewAI AMP`、`LangSmith`、`OpenAI Tracing`、`MAF DevUI + OTel` 表明，企业用户期待的是“可追踪、可调试、可比较、可治理”的 agent system，而不是单一 chat 界面。[L1][O1][C1][M1]

## Maintenance Notes

- 每月刷新一次 stars、latest release、recent direction
- 如果项目官方改变路线，需要单独记录，例如 `AutoGen -> Microsoft Agent Framework`
- 如果某能力只存在于扩展或生态层，不要写成 core capability
- 引用优先顺序：
  1. 官方 README / docs
  2. 官方 release notes
  3. 官方 repo metadata

## Design Readiness Assessment

### This Document Is Necessary But Not Sufficient

单靠这篇文档，**还不能直接进入产品设计**。

它回答的是：

- 外部生态正在往哪里收敛
- `pi-mono` 与常见 agentic system 的相对位置
- `recon` 不应该错过哪些能力方向

它没有回答的是：

- `recon` 的首要目标用户是谁
- `recon` 的 v1 产品边界是什么
- 哪些能力是 `must-have`，哪些只是后续观察项
- 主要交互面应该优先围绕 desktop、CLI/TUI、还是 web
- 哪些市场信号应被采纳为产品决策，哪些只应作为 watchlist

### Output To Product Design

这篇文档对产品设计的直接输出应被限制为：

- 能力优先级方向
- 竞争与参考系
- 生态协议趋势，例如 MCP、workflow、tracing、control plane
- 对 `pi-mono` 路线的借鉴与边界提醒

真正进入产品设计的收敛结论，应由综合设计文档给出。见 `docs/430-Pi-Mono-Inspired-Product-Design-Brief.md`。

## References

- [R1] [`recon` overview doc](./330-Generic-Assistant-Platform.md), sections `Current Reusable Assets` and `Recommended Target Product Model`, accessed 2026-03-30.
- [R2] [`recon` eval doc](./380-Evaluation-And-Quality.md), whole document, accessed 2026-03-30.
- [R3] [`recon` repository README](../README.md), sections `Current status` and `Docs`, accessed 2026-03-30.

- [P0] [`badlogic/pi-mono` repo metadata](https://api.github.com/repos/badlogic/pi-mono) and [latest release](https://api.github.com/repos/badlogic/pi-mono/releases/latest), accessed 2026-03-30.
- [P1] [`badlogic/pi-mono` root README](https://github.com/badlogic/pi-mono), section `Packages`, accessed 2026-03-30.
- [P2] [`packages/coding-agent` README](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent), sections `Quick Start`, `Customization`, `Programmatic Usage`, `Philosophy`, accessed 2026-03-30.
- [P3] [`packages/ai` README](https://github.com/badlogic/pi-mono/tree/main/packages/ai), section `Supported Providers`, accessed 2026-03-30.
- [P4] [`packages/agent` README](https://github.com/badlogic/pi-mono/tree/main/packages/agent), sections `Core Concepts`, `Event Flow`, `Agent Options`, accessed 2026-03-30.
- [P5] [`packages/web-ui` README](https://github.com/badlogic/pi-mono/tree/main/packages/web-ui), sections `Features` and `Architecture`, accessed 2026-03-30.
- [P6] [`packages/pods` README](https://github.com/badlogic/pi-mono/tree/main/packages/pods), sections `What is pi?` and `Quick Start`, accessed 2026-03-30.

- [L0] [`langchain-ai/langgraph` repo metadata](https://api.github.com/repos/langchain-ai/langgraph) and [latest release](https://api.github.com/repos/langchain-ai/langgraph/releases/latest), accessed 2026-03-30.
- [L1] [`LangGraph` README](https://github.com/langchain-ai/langgraph), sections `Why use LangGraph?` and `LangGraph ecosystem`, accessed 2026-03-30.

- [O0] [`openai/openai-agents-js` repo metadata](https://api.github.com/repos/openai/openai-agents-js) and [latest release](https://api.github.com/repos/openai/openai-agents-js/releases/latest), accessed 2026-03-30.
- [O1] [`OpenAI Agents SDK (JavaScript/TypeScript)` README](https://github.com/openai/openai-agents-js), sections `Core concepts` and `Supported environments`, accessed 2026-03-30.

- [A0] [`microsoft/autogen` repo metadata](https://api.github.com/repos/microsoft/autogen) and [latest release](https://api.github.com/repos/microsoft/autogen/releases/latest), accessed 2026-03-30.
- [A1] [`AutoGen` README](https://github.com/microsoft/autogen), top-level note plus sections `MCP Server` and `Multi-Agent Orchestration`, accessed 2026-03-30.

- [C0] [`crewAIInc/crewAI` repo metadata](https://api.github.com/repos/crewAIInc/crewAI) and [latest release](https://api.github.com/repos/crewAIInc/crewAI/releases/latest), accessed 2026-03-30.
- [C1] [`CrewAI` README](https://github.com/crewAIInc/crewAI), sections `Fast and Flexible Multi-Agent Automation Framework`, `CrewAI AMP Suite`, `Crew Control Plane Key Features`, `Why CrewAI?`, accessed 2026-03-30.

- [S0] [`huggingface/smolagents` repo metadata](https://api.github.com/repos/huggingface/smolagents) and [latest release](https://api.github.com/repos/huggingface/smolagents/releases/latest), accessed 2026-03-30.
- [S1] [`smolagents` README](https://github.com/huggingface/smolagents), introductory feature bullets and quick demo section, accessed 2026-03-30.

- [M0] [`microsoft/agent-framework` repo metadata](https://api.github.com/repos/microsoft/agent-framework) and [latest release](https://api.github.com/repos/microsoft/agent-framework/releases/latest), accessed 2026-03-30.
- [M1] [`Microsoft Agent Framework` README](https://github.com/microsoft/agent-framework), sections `Documentation` and `Highlights`, accessed 2026-03-30.
