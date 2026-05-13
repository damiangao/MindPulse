# MindPulse 改进需求文档

## 一、SDK 功能使用分析

> ⚠️ **评估原则**：配置了但未调用的 SDK 功能 = 可改进项

### 已配置但未充分使用的 SDK 功能

| SDK 功能 | 配置 | 现状 | 改进点 |
|---------|------|------|--------|
| `Bash` | ✅ 已配置 | 未验证是否可用 | 可能需要开启 |
| `Skill` | ✅ 已配置 | 未暴露给用户 | 前端无技能调用入口 |
| `max_turns=100` | ✅ 已配置 | 未使用 | 无多轮对话支持 |
| `thinking` | ✅ 已配置 | 后端已接收 | 前端未展示 thinking 过程 |
| `include_partial_messages` | ✅ 已配置 | 未确认 | 可能影响流式体验 |
| `setting_sources=["project"]` | ✅ 已配置 | 未确认 | CLAUDE.md 加载可能失效 |
| `resume=session_id` | ✅ 已配置 | **未实现** | 无法恢复历史会话 |

---

### 差距 1: Session 恢复（resume）

**当前**: `session_id` 只用于追踪，未用于恢复会话。

**问题**:
- 用户刷新页面或断线后，无法继续历史对话
- 每次都是新 session，AI 丢失上下文

**方案**:
```python
# ai_client.py 的 _build_options 已支持 resume
# 只需在前端 reconnect 时传入 session_id
```

---

### 差距 2: 多轮对话支持

**当前**: `max_turns=100` 已配置，但每次 `send_message` 是独立调用。

**问题**:
- SDK 的 turn 是指 user-assistant 配对
- 当前实现每次都重置消息历史，未累积

**方案**:
- 维护 `self._messages` 列表
- 每次 `send_message` 时附带历史消息
- SDK 会自动处理多轮逻辑

---

### 差距 3: Thinking 展示

**当前**: 后端接收 `thinking_delta` 并广播，但前端未渲染。

**问题**:
- AI 的思考过程用户看不到
- 体验不完整

**方案**:
- 前端 `ChatWindow` 渲染 `thinking_delta`
- 类似 `tool_use` 的展示块

---

### 差距 4: 技能系统未暴露

**当前**: `Skill` 工具已配置，但用户无法调用。

**问题**:
- Skills 是 Claude 内置技能生态
- 用户不知道可以用 `/skill` 或类似方式调用

**方案**:
- 前端添加技能选择器
- 或提示用户可使用技能命令

---

### 差距 5: 项目级 Context（CLAUDE.md）

**当前**: `setting_sources=["project"]` 已配置。

**问题**:
- 不确定 CLAUDE.md 是否被正确加载
- 用户可能写了项目规则但未生效

**方案**:
- 验证 CLAUDE.md 是否被 SDK 读取
- 如未生效，修复路径或配置

---

## 二、Mini-Agent 对比（真实差距）

| 功能 | Mini-Agent | MindPulse | 说明 |
|------|-----------|----------|------|
| **跨会话记忆** | ✅ Session Note | ❌ | SDK 无此功能，需自己实现 |
| **上下文摘要** | ✅ token_limit | ❌ | SDK 无，需自己实现 |
| **重试机制** | ✅ RetryWrapper | ❌ | 需自己实现 |
| **MCP Server** | ✅ mcp_loader | ❌ | SDK 不支持外部 MCP |
| **ACP 协议** | ✅ acp/server | ❌ | 需自己实现 |
| **日志系统** | ✅ AgentLogger | ⚠️ | 只有基础 logging |

---

## 三、真实改进需求

### P0 - 已配置但未生效

1. **Session 恢复** - reconnect 时恢复会话
2. **Thinking 展示** - 前端渲染思考过程
3. **CLAUDE.md 加载验证** - 确认 project setting 生效

### P1 - 核心体验缺失

4. **跨会话记忆** - Session Note Tool
5. **上下文摘要** - Token 超限时压缩
6. **多轮消息累积** - 累积历史消息

### P2 - 稳定性增强

7. **重试机制** - 指数退避重试
8. **日志增强** - 参考 AgentLogger

### P3 - 扩展能力

9. **技能系统暴露** - 前端支持调用
10. **MCP Server** - 外部工具集成
11. **ACP 协议** - 编辑器集成

---

## 四、推荐优先级

```
Phase 0: 验证 & 修复（已配置但有问题）
├── 1. 验证 CLAUDE.md 加载
├── 2. 修复 Thinking 前端展示
└── 3. 实现 Session 恢复

Phase 1: 核心体验
├── 4. Session Note 持久化
├── 5. 上下文摘要
└── 6. 多轮消息累积

Phase 2: 稳定性
├── 7. 重试机制
└── 8. 日志增强

Phase 3: 扩展
├── 9. 技能暴露
├── 10. MCP
└── 11. ACP
```

---

## 五、快速修复项

### 1. Thinking 展示（前端）

```jsx
// ChatWindow.jsx
// 已有 thinking_delta 广播，前端只需渲染
{type === "thinking_delta" && (
  <ThinkingBlock delta={message.delta} />
)}
```

### 2. Session 恢复（前后端）

```python
# 前端 reconnect 时传入 session_id
# 后端 AgentSession 识别 session_id 并 resume
```

### 3. 验证 CLAUDE.md 加载

```python
# 在 ai_client.py 添加日志确认
_logger.info(f"Project root: {project_root}, CLAUDE.md exists: {Path(project_root, 'CLAUDE.md').exists()}")
```