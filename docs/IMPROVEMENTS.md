# MindPulse 改进需求文档

## 一、已实现功能确认

| 功能 | 状态 | 说明 |
|------|------|------|
| Thinking 展示 | ✅ 已实现 | `ThinkingBlock` 组件完整，可折叠/展开 |
| `thinking_delta` 广播 | ✅ 已实现 | 后端 `session.py` 正确处理 |
| 文件工具 | ✅ 已实现 | SDK 内置 Read/Write/Edit/Glob/Grep |
| Bash 工具 | ✅ 已配置 | SDK 内置，需验证 |
| Web 搜索 | ✅ 已配置 | SDK 内置 WebSearch/WebFetch |

---

## 二、真实改进需求

### P0 - 核心缺失

#### 1. Session 恢复（resume）

**问题**: `session_id` 只用于追踪，刷新页面或断线后无法恢复会话。

**现状**: 每次 connect 都是新 session，AI 丢失上下文。

**方案**: 前端 reconnect 时传入 `session_id`，后端识别并 resume。

---

#### 2. 多轮消息累积

**问题**: `max_turns=100` 已配置，但每次 `send_message` 是独立调用，历史消息未累积。

**现状**: SDK 会话内只保留当前 turn 的消息。

**方案**: 在 `AgentSession` 层维护 `self._messages` 列表，每次发送时附带完整历史。

---

### P1 - 重要功能

#### 3. CLAUDE.md 加载验证

**问题**: `setting_sources=["project"]` 已配置，不确定是否生效。

**方案**: 添加日志验证 CLAUDE.md 是否被 SDK 读取。

---

#### 4. 跨会话记忆（Session Note）

**问题**: AI 无法跨会话记忆关键信息。

**方案**: 参考 Mini-Agent，实现持久化 Session Note Tool。

---

#### 5. 上下文摘要

**问题**: 长对话无 Token 控制，可能溢出。

**方案**: 实现 Token 预算监控，超限时自动摘要。

---

### P2 - 稳定性

#### 6. 重试机制

**问题**: API 失败直接报错，无重试。

**方案**: 参考 Mini-Agent 的 RetryWrapper，实现指数退避。

---

#### 7. 日志增强

**问题**: 只有基础 logging。

**方案**: 参考 Mini-Agent AgentLogger，实现完整请求/响应日志。

---

### P3 - 扩展能力

#### 8. 技能暴露

**问题**: `Skill` 工具已配置，用户无法调用。

**方案**: 前端添加技能选择器或命令提示。

---

#### 9. MCP / ACP

**问题**: 无外部工具和编辑器集成。

**方案**: 研究 SDK 是否支持 MCP；参考 Mini-Agent 实现 ACP。

---

## 三、推荐优先级

```
Phase 0: 核心体验
├── 1. Session 恢复
└── 2. 多轮消息累积

Phase 1: 验证 & 重要功能
├── 3. CLAUDE.md 加载验证
├── 4. 跨会话记忆
└── 5. 上下文摘要

Phase 2: 稳定性
├── 6. 重试机制
└── 7. 日志增强

Phase 3: 扩展
├── 8. 技能暴露
└── 9. MCP / ACP
```

---

## 四、下一跳

**Session 恢复** 是最重要的改进：

- 用户体验直接受益（刷新不断线）
- 技术方案清晰（前端传 session_id，后端 resume）
- 可验证（断线重连后查日志）