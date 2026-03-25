# UI Component Glossary

## Goal

为 Recon Desktop 当前主界面提供一套统一的技术术语标识，便于后续在设计、开发、测试、文档和沟通中引用同一组页面部件名称。

## Scope

本说明覆盖当前桌面主窗口中的核心可见部件，不覆盖内部线程对象、服务对象、数据库对象等非 UI 组件。

## Main Window Structure

- `MainWindow`
  - 主窗口容器，基于 `QMainWindow`
- `MenuBar`
  - 顶部菜单栏，包含 `文件` 和 `工具`
- `Central Widget`
  - 主内容区根容器
- `Horizontal Splitter`
  - 水平分割器，基于 `QSplitter`
  - 用于划分左侧导航区和右侧工作区

## Left Panel

- `Project / Session Navigation Tree`
  - 项目与会话导航树，基于 `QTreeWidget`
- `Primary Actions Row`
  - 主操作按钮行，包含 `新建项目`、`新建对话`
- `Scenario Library`
  - 场景库，基于 `QTreeWidget`
- `Scenario Category Node`
  - 场景分类节点，例如“供汽与热力”
- `Scenario Item`
  - 场景条目，例如“蒸汽不足”“能效诊断”

## Right Panel

- `Project Context Header`
  - 右侧工作区顶部的项目上下文信息区
- `Project Info Label`
  - 当前项目标签
- `Session Info Label`
  - 当前对话标签
- `Project Metadata Label`
  - 项目元信息标签

## Message Area

- `Message Stack`
  - 消息区栈容器，基于 `QStackedWidget`
- `Empty State View`
  - 未选中会话时显示的空状态视图
- `Message List`
  - 消息列表，基于 `QListWidget`
- `Message Item`
  - 单条消息项，基于 `QListWidgetItem`
- `Message Bubble` / `Message Card`
  - 单条消息的气泡卡片，基于 `QFrame`
- `User Message Card`
  - 用户消息卡片
- `Assistant Message Card`
  - 系统消息卡片
- `Pending Message State`
  - 等待态消息，例如 `输入中`

## Message Content Blocks

- `Rich Text Block`
  - 文本和基础富文本内容块
- `Markdown Table Block`
  - Markdown 表格渲染块
- `Link Card`
  - 链接卡片
- `Attachment Card`
  - 附件卡片

## Composer Area

- `Attachment Trigger Button`
  - 输入框左侧 `+` 按钮，用于选择文件
- `Attachment Chip Row`
  - 输入区上方的附件标签行
- `Attachment Chip`
  - 单个附件标签
- `Clear Attachments Action`
  - 清空附件按钮
- `Chat Composer`
  - 聊天输入器，基于自定义 `ChatInput(QTextEdit)`
- `Primary Action Button`
  - 输入区右侧主操作按钮
- `Send Action`
  - 发送态，向上箭头图标
- `Stop Generation Action`
  - 停止等待态，铜钱样图标

## Auxiliary UI

- `Status Bar`
  - 底部状态栏，用于显示运行状态、provider 信息等
- `Context Menu`
  - 项目树上下文菜单

## Dialogs And Tool Panels

- `Project Dialog`
  - 项目编辑弹窗
- `Settings Dialog`
  - 模型设置弹窗
- `Request Log Dialog`
  - 请求日志弹窗
- `Gateway Provider Dialog`
  - Gateway Provider 运维弹窗

## Implementation Notes

- 当前主界面的主要实现位于 `src/recon/ui.py`
- 本术语表优先反映当前实际实现，而不是抽象产品概念
- 如果未来界面结构变化明显，应更新本文件而不是在其他文档中复制一份新的术语表
