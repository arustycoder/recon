# Pi-Mono-Inspired Product Design Brief

## Goal

把 `docs/410-Agentic-System-Landscape-Tracker.md` 与 `docs/420-Rust-Port-Evaluation-For-Pi-Mono-Capabilities.md` 两篇研究文档，收敛成一份可以支撑 `recon` 进入产品设计阶段的设计入口文档。

这份文档不再重复外部生态细节或底层技术可行性，而是明确回答：

- 产品到底面向谁
- 首期产品是什么，不是什么
- 主交互面是什么
- 哪些能力必须进 v1
- 哪些约束已经确定，设计不应再反复摇摆

## Design Gate Result

### Before This Brief

只有 `410` 和 `420` 两篇文档时，**还不满足直接进入产品设计阶段**。

原因很简单：

- `410` 解决的是外部参考系与能力趋势，不是产品定义
- `420` 解决的是 Rust 迁移与架构约束，不是产品定义

它们都缺少：

- 明确目标用户
- 明确 v1 范围
- 明确主交互面
- 明确非目标
- 明确哪些结论已经定案，设计阶段不再反复讨论

### After This Brief

补上这份文档后，**可以进入产品设计阶段**，但仅限于本文定义的产品范围和优先级。

## Product Thesis

`recon` 应被定义为：

**一个面向技术用户的、本地优先、可扩展、可审计的 assistant workbench。**

它的核心不是“做一个更会聊天的窗口”，而是把下面四件事做成统一产品体验：

- tool-backed assistant execution
- session / task / approval / trace 的可见化
- multi-provider 与 profile 的可切换性
- skills / tools / plugins 的可扩展性

## Target Users

### Primary Users

- 个人开发者与 technical power users
- 小型技术团队中的核心执行者
- 需要频繁比较 provider、运行工具、追踪执行过程的 AI / platform engineers

### Secondary Users

- 需要通过桌面工作台理解 assistant 执行轨迹的项目负责人或技术管理者

### Not First-Phase Users

- 非技术办公用户
- 以大规模企业管控为第一目标的管理员
- 需要复杂多智能体图形编排器的流程设计者

## Core Jobs To Be Done

### 1. Run A Technical Assistant Session

用户要能在一个受控环境中发起技术任务，并让 assistant 使用文件、shell、检索或外部工具完成工作。

### 2. Inspect And Control Execution

用户要能看见：

- 当前用了哪个 profile / provider
- assistant 调用了哪些工具
- 哪些步骤需要审批
- 当前成本、时延、错误和状态

### 3. Resume, Fork, And Revisit Work

用户要能恢复旧会话、从历史节点分叉、重看工具结果，而不是把每次执行都视作一次性聊天。

### 4. Run Longer Tasks Without Losing Control

当工作超出单次前台对话时，用户要能切到 task 视图，看到 step、approval、retry、resume、summary。

### 5. Extend The System Safely

用户或团队要能通过 skills、prompt templates、tools、plugins 扩展能力，但扩展必须落在明确协议与审计边界内。

## Product Shape Decisions

### 1. Canonical Product Surface: Desktop Workbench

产品设计阶段应把 **desktop workbench** 视为主信息架构载体。

原因：

- tasks、approvals、trace、provider settings、skill/plugin 管理都更适合多面板工作台
- `recon` 现有文档与产品方向本来就是 workbench，不是单一 CLI 工具包
- 这样可以兼容以后做 CLI/TUI，而不把产品设计绑死在终端布局上

### 2. CLI / TUI Is First-Class, But Not The Canonical IA

CLI / TUI 仍然是第一阶段必须保留的 expert surface，用于：

- 高效执行
- dogfooding
- 本地开发与自动化接入

但它不是产品设计阶段的主布局依据。  
产品设计应先定义桌面信息架构，再导出 CLI/TUI 的对应交互。

### 3. Gateway-Owned Runtime

执行、审批、任务状态、审计、provider routing 不应只存在于 UI 内部。  
这些状态必须由 gateway / runtime 持有，这样 desktop、CLI/TUI、web/API 才能共享同一执行模型。[D4][D5]

## V1 Product Boundary

### Must-Have

- 会话视图：conversation + session tree + resume/fork
- 工具执行视图：tool calls、tool results、errors、costs、latency
- 任务视图：long-running task、steps、approval checkpoints、retry、resume
- provider/profile 切换与基础比较
- skills / prompt templates 管理
- 明确的安全与审批体验
- 本地技术工具集：至少覆盖读、写、编辑、shell、搜索类能力
- request / trace / audit 基础可见性

### Should-Have

- CLI / TUI 对等入口
- 基础插件宿主
- artifact / attachment 结果视图
- 管理与诊断面板

### Defer

- Slack / channel integrations
- pod / vLLM orchestration
- browser-first web product
- visual workflow builder
- generalized swarm / autonomous multi-agent system

## V1 Non-Goals

- 不做“无限自治 agent swarm”
- 不做“企业 control plane first”
- 不做“与 npm / TS extension 生态完全兼容”
- 不做“所有 provider 与 OAuth path 一次性覆盖”
- 不做“浏览器组件体系与 `pi-web-ui` 完全同构复刻”
- 不做“native Rust plugin ABI”

## Design Principles

### 1. Visible Execution Beats Hidden Magic

用户必须看见 assistant 在做什么，而不是只看最后答案。

### 2. Single-Agent First, Task-Ready

首期优先做好 single-agent + task runtime，不把多智能体编排当成前提。

### 3. Extensible By Protocol, Not By Shared Memory

skills、tools、plugins 的扩展必须基于协议和 schema，不基于内部对象结构或 ABI。

### 4. Safety Is A Product Feature

审批、权限、审计不是后台规则，而是前台可理解的体验组成部分。[D5]

### 5. Product Scope Must Drive Technical Scope

Rust 迁移、TUI、plugin host、web UI 都必须服务于明确的产品边界，而不是各自成为独立目标。[D2]

## Core Interaction Model

### Workspace Layer

承载：

- sessions
- tasks
- resources
- policies
- active profile/provider context

### Session Layer

承载：

- 短期前台 assistant 交互
- tool trace
- branch / fork / resume

### Task Layer

承载：

- 多步长任务
- approval wait
- retries
- summarized completion back to session

### Extension Layer

承载：

- skills
- prompt templates
- tools
- process/WASI plugins

## Primary UX Surfaces For Product Design

### 1. Session Workspace

建议作为主画面，至少包含：

- 会话消息区
- session tree / history navigator
- 当前 provider / profile / cost / context 状态
- tool trace drawer
- quick actions

### 2. Task Inspector

建议作为独立面板或二级视图，至少包含：

- task summary
- current status
- step list
- approval state
- retry / cancel / resume actions
- completion summary

### 3. Settings And Policy Surface

至少要有：

- provider settings
- profile selection
- tool permissions
- plugin / skill enablement

### 4. Operations Surface

至少要有：

- recent requests
- errors
- latency / cost
- provider health

## Product Decisions That Are Now Fixed

进入产品设计时，下面这些结论应视为已定：

1. **产品定位**：技术用户的 assistant workbench，而不是通用聊天客户端。[D1]
2. **首期执行模型**：single-agent first + task runtime，不以 swarm 为前提。[D3][D4]
3. **主信息架构**：desktop workbench 优先，CLI/TUI 为第一类辅面。
4. **扩展模型**：skills / templates 保留；plugins 走协议化边界，不走 native ABI。[D2]
5. **执行归属**：runtime / policy / audit / task state 归 gateway 或共享核心，不归单一前端。[D4][D5]
6. **安全模型**：审批与审计是产品主线，不是后加规则。[D5]
7. **市场采纳原则**：吸收 `pi-mono` 的本地工作流与扩展边界，吸收 LangGraph / MAF / CrewAI / OpenAI Agents 的 observability、task/workflow、control 面思路，但不直接复制它们的全部产品形态。[D1][D2]

## Product Decisions Still Open

这些问题仍然开放，但不会阻塞产品设计启动：

- desktop shell 最终采用什么技术壳：沿现有桌面体系继续演进，还是后续向 Tauri / Rust shell 收口
- v1 初始 provider 列表到底保留几个
- plugin distribution 是仅本地目录，还是引入轻量 registry
- artifact / attachment 的首期可视化深度做到什么程度

这些应在设计与实现并行阶段继续收敛，而不是拖住 v1 结构设计。

## Entry Criteria For Product Design

进入产品设计阶段时，应按下面的清单工作：

- 以本文的目标用户和非目标为准
- 以本文的 v1 边界为准
- 以 desktop workbench 为主信息架构
- 以 session / task / settings / ops 四大界面为主设计对象
- 以 protocol-first extensibility 为扩展前提
- 以 task / approval / observability 为不可降级能力

满足以上条件后，产品设计可以正式开始。

## Relationship To Existing Docs

- `docs/410-Agentic-System-Landscape-Tracker.md` 提供外部参考系与能力趋势
- `docs/420-Rust-Port-Evaluation-For-Pi-Mono-Capabilities.md` 提供技术约束与迁移原则
- `docs/330-Generic-Assistant-Platform.md` 提供平台目标
- `docs/350-Task-Runtime.md` 提供 task model
- `docs/370-Safety-And-Permissions.md` 提供安全与审批约束

## References

- [D1] [`docs/410-Agentic-System-Landscape-Tracker.md`](./410-Agentic-System-Landscape-Tracker.md), sections `Implications For recon` and `Design Readiness Assessment`, accessed 2026-03-30.
- [D2] [`docs/420-Rust-Port-Evaluation-For-Pi-Mono-Capabilities.md`](./420-Rust-Port-Evaluation-For-Pi-Mono-Capabilities.md), sections `Executive Summary`, `Recommended Rust Architecture`, `Extensibility Model`, `Design Readiness Assessment`, accessed 2026-03-30.
- [D3] [`docs/330-Generic-Assistant-Platform.md`](./330-Generic-Assistant-Platform.md), sections `Recommended Target Product Model` and `Recommended Architecture Direction`, accessed 2026-03-30.
- [D4] [`docs/350-Task-Runtime.md`](./350-Task-Runtime.md), whole document, accessed 2026-03-30.
- [D5] [`docs/370-Safety-And-Permissions.md`](./370-Safety-And-Permissions.md), whole document, accessed 2026-03-30.
