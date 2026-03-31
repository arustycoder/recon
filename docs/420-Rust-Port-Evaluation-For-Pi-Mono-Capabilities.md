# Rust Port Evaluation For Pi-Mono Capability Parity

## Goal

评估如何在 `recon` 体系内，用 Rust 重建 `pi-mono` 的主要能力，并在以下前提下保持可落地：

- 保留大部分用户可见特性
- 保持较好的扩展性
- 避免把系统锁死在脆弱的 ABI 或单一脚本运行时
- 为后续桌面、网关、协作与可观测能力留出演进空间

## Scope

### Included

- `pi-ai` 类统一 provider / model / tool-calling 层
- `pi-agent-core` 类 stateful agent runtime
- `pi-coding-agent` 类 CLI / session / compaction / RPC 能力
- `pi-tui` 类终端交互层
- `pi-web-ui` 类 API / artifact / attachment 支撑面
- `pi-mom` 类 Slack bot 集成
- `pi-pods` 类 vLLM / pod management 能力
- `Extensions / Skills / Prompt Templates / Packages` 的可替代设计

### Excluded

- 与 TypeScript extension API 的二进制或源码级兼容
- 与 npm 安装模型的 1:1 兼容
- 所有 OAuth provider 在首期完整复刻
- 在第一阶段同时完成 CLI、TUI、web UI、desktop UI 的完全同等成熟度

## Baseline: What “Keep Most Features” Means

如果要说“保持大部分特性”，至少要保住下面这些能力：

1. 多 provider、统一 tool-calling LLM API。[P1][P3]
2. Stateful agent loop、事件流、tool execution、streaming。[P4]
3. Interactive coding CLI：内建文件与 shell 工具、session、fork、tree、compaction、SDK、RPC。[P2]
4. 明确的可扩展面：skills、prompt templates、extensions、package distribution。[P2][P5]
5. 基本可用的 TUI 交互层，而不是只有裸命令行。[P6]
6. 可选的协作入口，例如 Slack bot 和远端模型运维入口。[P1][P7]

## Executive Summary

### Short Answer

可以做，而且核心部分适合 Rust。  
如果目标是“保住 75% 到 85% 的核心能力，同时提升 runtime 稳定性、并发性和部署一致性”，Rust 是合理路线。  
如果目标是“逐字逐句复制 `pi-mono` 的 TypeScript extension 体验、热加载方式、web component 形态和 npm package 生态”，Rust 路线的成本会显著上升，不建议这么定义目。

### Main Judgement

- **高可行**：provider layer、agent runtime、session storage、RPC、CLI、gateway/service、Slack/pod orchestration。
- **中可行**：TUI parity、artifact pipeline、tool schema system、settings/operations surface。
- **中高风险**：动态扩展系统、hot reload、browser-side component parity、subscription OAuth parity、终端高级特性完全复刻。

### Recommended Porting Principle

不要做“TypeScript 架构的 Rust 翻译版”。  
应该做“Rust 核心 + 协议优先扩展 + 声明式 UI 集成”的新实现。

## Feasibility By Pi-Mono Package

| Pi capability | Suggested Rust target | Parity expectation | Risk | Why |
| --- | --- | --- | --- | --- |
| `pi-ai` | `recon-llm` | 高 | 中 | HTTP + streaming + typed schema 在 Rust 很适合，但 provider OAuth 生态不如 JS 齐全。[P3][K1][K2][K6][K7] |
| `pi-agent-core` | `recon-agent-runtime` | 高 | 低 | Rust 很适合做 state machine、event stream、tool loop、cancellation。[P4][K1][K6] |
| `pi-coding-agent` | `recon-cli` + `recon-session` + `recon-rpc` | 高 | 中 | CLI、session、JSONL、fork/tree/compaction 都可重建；复杂点在 UX 打磨和 provider auth。[P2][K1][K6] |
| `pi-tui` | `recon-tui` | 中 | 中高 | Ratatui + Crossterm 足以覆盖主体交互，但高级终端特性要额外补工程。[P6][K4][K5] |
| `pi-web-ui` | `recon-api` + thin web client | 中 | 中高 | Rust 很适合服务端与 protocol，不适合优先重做浏览器组件体系。[P5][K3][K9] |
| `pi-mom` | `recon-slack` | 中高 | 中 | 事件同步、上下文与工具调用可迁；主要风险在 Slack 适配与运维细节。[P7][K1][K3] |
| `pi-pods` | `recon-pods` | 中高 | 中 | Rust 适合 SSH/orchestration/CLI，但模型预设、平台适配、诊断脚本要靠长期维护。[P8][K1][K2] |
| `Extensions` | `recon-plugin-host` | 中 | 高 | 不能照搬 TS runtime；必须改成 process/WASI/plugin protocol。[P5][K8] |
| `Skills` / `Templates` | `recon-skills` | 高 | 低 | Markdown / manifest / prompt-time loading 天然适合语言无关实现。[P2] |
| `Pi Packages` | `recon package registry` | 中 | 中高 | 分发可以做，但不建议与 npm compatibility 绑定。[P2] |

## What Rust Is Especially Good At

### 1. Runtime Core

`Tokio` 明确定位为 event-driven、non-blocking I/O platform，提供 scheduler、reactor、async sockets，非常适合承接 provider streaming、tool execution、session flush、background orchestration。[K1]

这意味着下面这些核心能力用 Rust 重写是顺势而为：

- provider streaming
- cancellation / abort
- parallel tool execution
- request timeout / retry / backpressure
- gateway concurrency
- long-lived agent sessions

### 2. HTTP And Gateway Layer

`Reqwest` 提供 async / blocking client、JSON、multipart、proxy、HTTPS、cookie store；`axum` 提供 request routing、extractors、predictable errors，以及基于 `tower` 的 middleware 生态。[K2][K3]

因此 Rust 版本可以自然承接：

- OpenAI / Anthropic / Google / compatible HTTP adapters
- SSE / websocket / streaming response fan-out
- management APIs
- RPC over HTTP / WebSocket
- admin and observability endpoints

### 3. Typed Protocols And Tool Schemas

`Serde` 是 Rust 侧事实标准序列化框架；`Schemars` 可以从 Rust types 生成 JSON Schema，并显式强调与 Serde attribute 的兼容性。[K6][K7]

这对替代 `pi-ai` 里 TypeBox + JSON schema 的工具定义非常关键。  
推荐把工具、事件、session entry、plugin protocol 都建模成：

- Rust struct / enum
- `serde::{Serialize, Deserialize}`
- `schemars::JsonSchema`

这样可以同时得到：

- 本地类型安全
- 外部协议稳定性
- 自动文档与校验输入
- 未来多语言插件的 schema contract

## Where Pure Rust Porting Becomes Expensive

### 1. Dynamic Extension System

`pi-coding-agent` 的一大优势是 TypeScript extensions：可热加载、可注册工具、命令、快捷键、事件处理器和 UI 组件。[P5]  
这套体验依赖 Node / TS / JIT loading，本质上不适合直接映射到原生 Rust 插件 ABI。

这里的核心结论是：

- **不要做 native Rust 动态库插件 ABI 作为主要扩展方案**
- **不要把 `ratatui` widget trait 暴露给插件**
- **不要把内部内存结构当扩展契约**

否则扩展性会很快退化成版本锁死。

### 2. TUI Advanced Parity

`pi-tui` 明确支持 differential rendering、synchronized output、bracketed paste、autocomplete、overlay、IME cursor positioning、Kitty/iTerm image protocols 等高级终端能力。[P6]  
`Ratatui` 和 `Crossterm` 能很好覆盖基本 TUI，但不会自动给出这些“成熟终端产品”级别能力。[K4][K5]

因此应该把目标拆开：

- **Phase 1 必须保住**：input editor、message list、status line、select list、overlay、keybindings、streaming updates
- **Phase 2 再补**：images、IME refinement、advanced rendering optimizations、terminal-specific polish

### 3. Web UI Full Parity

`pi-web-ui` 不只是 chat 面板，还包含附件提取、artifact、IndexedDB-backed app storage、sandboxed artifact execution、custom runtime providers 等。[P9]  
如果要求“用纯 Rust 同时复刻浏览器组件体系”，整体投入会大幅增加。

因此更合理的判断是：

- Rust 非常适合做 `web API + session protocol + artifact backend`
- 浏览器 UI 不应成为首期纯 Rust 约束
- 如果确实需要 desktop shell，可把 Rust 核心置于 `Tauri` 后端，由 web UI 与之交互；Tauri 自身就是 Rust backend + web frontend 的架构。[K9]

## Recommended Rust Architecture

### Workspace Layout

建议按 workspace 切成下面这些 crate：

- `recon-protocol`
  - 所有公共协议：messages、events、tool calls、session entries、plugin RPC types
- `recon-llm`
  - provider adapters、model registry、streaming normalizer、cost/tokens accounting
- `recon-agent-runtime`
  - state machine、tool loop、hooks、interrupt、compaction hooks
- `recon-session`
  - JSONL session tree、fork、resume、branch navigation、compaction snapshots
- `recon-tools`
  - built-in tools：read / write / edit / bash / grep / find / ls
- `recon-cli`
  - print / json / rpc / interactive entrypoints
- `recon-tui`
  - TUI rendering、keybinding、message queue、widgets、status/footer
- `recon-plugin-host`
  - plugin loading、permission boundary、protocol bridge
- `recon-api`
  - HTTP / WS / admin / artifact APIs
- `recon-slack`
  - Slack integration
- `recon-pods`
  - remote pod / vLLM management

### Key Boundary Rule

把 `recon-protocol` 当成“系统真正的 public API”。  
CLI、TUI、gateway、plugins、web client 都依赖它，而不是互相依赖具体实现细节。

## Extensibility Model

为了保持较好的扩展性，建议把扩展面拆成四层。

### 1. Prompt-Time Extensions

保留 `Skills` 与 `Prompt Templates` 的思路：

- Markdown 文件
- manifest/frontmatter
- 可版本化的 metadata
- 目录发现 + 配置启用

这层不需要语言绑定，最稳。

### 2. Callable Tools

所有工具定义都通过 JSON Schema 暴露：

- 参数 schema：Rust type -> `schemars`
- 返回 schema：Rust type -> `schemars`
- 运行协议：JSON-RPC over stdio / socket / host call

这样做能同时支持：

- 内置 Rust 工具
- 外部进程工具
- 远程 HTTP 工具
- MCP adapter

### 3. Runtime Plugins

推荐双轨：

- **默认轨**：外部进程插件，使用 JSON-RPC over stdio
- **增强轨**：WASI component 插件，使用 `Wasmtime`

`Wasmtime` 明确支持 WebAssembly 与 WASI，并已支持 `wasm32-wasip2` 组件运行。[K8]  
这使它适合用来承接：

- 安全边界更清晰的插件
- 多语言 guest implementation
- 未来的 policy / transform / tool plugins

### 4. UI Contributions

不要让插件直接操作 TUI widget tree。  
应定义一个声明式 UI 协议，例如：

- notice
- confirm
- input form
- select list
- status item
- footer item
- overlay panel
- structured artifact view

插件向 host 发送声明式 UI request，真正渲染由 host 负责。  
这样才不会把 UI 实现细节变成扩展兼容负担。

## Recommended Feature Mapping

| Pi feature area | Rust port recommendation |
| --- | --- |
| Tool calling | Rust core 一等支持，类型模型统一放进 `recon-protocol` |
| Sessions / tree / fork | 保留 JSONL tree 语义，兼容导出与 replay |
| Compaction | 保留 hook 机制，但 compact prompt 做成 profile/policy 可替换 |
| Skills | 保留 Markdown skill 机制 |
| Prompt templates | 保留 |
| Extensions | 改成 process plugins + optional WASI，不复刻 TS runtime |
| Themes | TUI themes 可保留；web themes 不应阻塞核心迁移 |
| RPC mode | 必须保留，作为 GUI/web/automation 的核心协议 |
| SDK | 首期只暴露 Rust SDK；其他语言通过 RPC/HTTP 访问 |
| Web UI | 首期保协议与 API，不强求纯 Rust web component parity |
| Slack bot | 二期实现 |
| Pods / vLLM management | 三期实现 |

## Recommended Delivery Phases

### Phase 1: Rust Core First

目标：

- `recon-protocol`
- `recon-llm`
- `recon-agent-runtime`
- `recon-session`
- `recon-tools`
- `recon-cli` 的 print/json/rpc mode

完成标准：

- 可运行单 agent tool loop
- 可保存 / 恢复 / fork session
- 可通过 RPC 驱动
- 可统一处理 OpenAI-compatible 与至少一个原生 provider

### Phase 2: Interactive Product Layer

目标：

- `recon-tui`
- skills / prompt templates
- 基础 plugin host
- settings / auth / model registry UI

完成标准：

- coding harness 可日常使用
- 基础 keybindings、queued messages、tool output、session tree 可用
- 插件可注册工具与简单 UI request

### Phase 3: Ecosystem And Operations

目标：

- `recon-api`
- web client or Tauri shell
- Slack integration
- pod / vLLM operations
- WASI plugin path

完成标准：

- 可把 Rust 核心暴露给 web / desktop / automation
- artifact / attachment / admin APIs 成型
- 外部插件模型稳定

## Risks And Mitigations

### Risk 1: Over-rotating on “all-Rust”

如果强行要求 web UI、desktop UI、plugin runtime、provider auth、artifact sandbox 全部在 phase 1 用 Rust 纯重写，项目很容易陷入长时间平台工程，而不是用户价值。

**Mitigation**

- 把“Rust 核心”与“纯 Rust 全栈”分开
- 先保核心 runtime、session、CLI/TUI、protocol

### Risk 2: Native Plugin ABI Fragility

Rust 自身并不提供稳定的 native plugin ABI，直接暴露 trait object / dynamic lib 很脆。

**Mitigation**

- 主插件协议走 JSON-RPC over stdio
- 可选插件沙箱走 WASI / Wasmtime

### Risk 3: Provider Parity Overreach

`pi-ai` 的 provider 覆盖很广，还包括多种 OAuth / subscription path。[P3]  
Rust 侧如果一开始就追求完全同表，交付会变慢。

**Mitigation**

- 首期只做高价值 provider
- auth 与 transport 分层
- 允许某些 provider 通过兼容 API 或 helper process 接入

### Risk 4: TUI Product Polish Underestimation

真正好用的 agent TUI，不只是能显示文本。  
它需要流式更新、消息队列、树形 session、overlay、编辑器、工具输出折叠、终端兼容性。

**Mitigation**

- Phase 1 只求功能完整
- Phase 2 再做高阶终端体验
- 明确“产品 polish”是独立预算，不把它当附带任务

## Final Recommendation

### Recommendation

建议做 Rust 迁移，但要按以下定义推进：

- **迁移目标**：`pi-mono` 的核心能力与系统形态，而不是 TS 实现细节
- **核心策略**：Rust core + protocol-first extensibility
- **扩展策略**：skills / templates 保留；extensions 改为 process plugin + optional WASI
- **UI 策略**：TUI 优先，web UI 走协议与后端先行，不要求首期纯 Rust component parity

### Decision

如果 `recon` 想做的是：

- 更稳的 runtime
- 更强的并发和运维一致性
- 更清晰的插件边界
- 更长期的 desktop / gateway / agent platform 演进

那么 Rust 是合理主线。

如果 `recon` 想做的是：

- 立即复刻 `pi-mono` 的 TypeScript 扩展体验
- 立即兼容 npm package 生态
- 立即把 web UI 做到同等成熟

那么不应把“纯 Rust 重写”作为近期目标。

## Relationship To Existing Docs

- 补充 `docs/330-Generic-Assistant-Platform.md`
- 补充 `docs/350-Task-Runtime.md`
- 补充 `docs/370-Safety-And-Permissions.md`
- 补充 `docs/410-Agentic-System-Landscape-Tracker.md`

## Design Readiness Assessment

### This Document Is Necessary But Not Sufficient

单靠这篇文档，**也还不能直接进入产品设计**。

它回答的是：

- Rust 迁移是否可行
- 哪些能力适合首期落入 Rust 核心
- 哪些地方需要协议优先而不是实现优先
- 哪些技术约束会影响扩展性与阶段划分

它没有回答的是：

- 应该为哪类用户设计首期产品
- 首期产品到底要不要同时承担 desktop、CLI/TUI、web 三种主要界面
- 哪些技术能力必须在 v1 暴露给用户，哪些可以只保留在架构层
- 迁移路线和产品范围如何绑定，而不是彼此漂移

### Output To Product Design

这篇文档对产品设计的直接输出应被限制为：

- 技术约束
- 扩展模型约束
- UI 和插件边界约束
- 阶段化交付建议

真正的产品定义、MVP 范围、目标用户、核心旅程和非目标，应该由综合设计文档承接。见 `docs/430-Pi-Mono-Inspired-Product-Design-Brief.md`。

## References

- [P1] [`badlogic/pi-mono` root README](https://github.com/badlogic/pi-mono), section `Packages`, accessed 2026-03-30.
- [P2] [`packages/coding-agent` README](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent), sections `Quick Start`, `Sessions`, `Customization`, `Programmatic Usage`, `Philosophy`, accessed 2026-03-30.
- [P3] [`packages/ai` README](https://github.com/badlogic/pi-mono/tree/main/packages/ai), sections `Supported Providers`, `Tools`, `Cross-Provider Handoffs`, accessed 2026-03-30.
- [P4] [`packages/agent` README](https://github.com/badlogic/pi-mono/tree/main/packages/agent), sections `Core Concepts`, `Event Flow`, `Agent Options`, accessed 2026-03-30.
- [P5] [`packages/coding-agent/docs/extensions.md`](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/extensions.md), sections `Extensions`, `Key capabilities`, `Writing an Extension`, accessed 2026-03-30.
- [P6] [`packages/tui` README](https://github.com/badlogic/pi-mono/tree/main/packages/tui), sections `Features`, `TUI`, `Overlays`, `Focusable Interface (IME Support)`, accessed 2026-03-30.
- [P7] [`packages/mom` README](https://github.com/badlogic/pi-mono/tree/main/packages/mom), sections `Features`, `How Mom Works`, `Tools`, accessed 2026-03-30.
- [P8] [`packages/pods` README](https://github.com/badlogic/pi-mono/tree/main/packages/pods), sections `What is pi?`, `Commands`, `Predefined Model Configurations`, accessed 2026-03-30.
- [P9] [`packages/web-ui` README](https://github.com/badlogic/pi-mono/tree/main/packages/web-ui), sections `Features`, `Architecture`, `Components`, accessed 2026-03-30.

- [K1] [`Tokio` README](https://github.com/tokio-rs/tokio), sections `Overview` and `Example`, accessed 2026-03-30.
- [K2] [`Reqwest` README](https://github.com/seanmonstar/reqwest), introductory feature list and example, accessed 2026-03-30.
- [K3] [`axum` README](https://github.com/tokio-rs/axum/tree/main/axum), sections `High level features`, `Usage example`, `Safety`, accessed 2026-03-30.
- [K4] [`Ratatui` README](https://github.com/ratatui/ratatui), introduction and `Documentation` section, accessed 2026-03-30.
- [K5] [`Crossterm` README](https://github.com/crossterm-rs/crossterm), sections `Features` and `Getting Started`, accessed 2026-03-30.
- [K6] [`Serde` README](https://github.com/serde-rs/serde), introduction and `Serde in action`, accessed 2026-03-30.
- [K7] [`Schemars` README](https://github.com/GREsau/schemars), introduction, `Basic Usage`, and `Serde Compatibility`, accessed 2026-03-30.
- [K8] [`Wasmtime` README](https://github.com/bytecodealliance/wasmtime), sections `Example` and `Features`, accessed 2026-03-30.
- [K9] [`Tauri` README](https://github.com/tauri-apps/tauri), sections `Introduction` and `Features`, accessed 2026-03-30.
