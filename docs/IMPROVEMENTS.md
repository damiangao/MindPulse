# MindPulse 改进需求文档

## 一、已实现功能确认

| 功能 | 状态 | 说明 |
|------|------|------|
| Thinking 展示 | ✅ 已实现 | `ThinkingBlock` 组件完整，可折叠/展开 |
| `thinking_delta` 广播 | ✅ 已实现 | 后端 `session.py` 正确处理 |
| 文件工具 | ✅ 已实现 | SDK 内置 Read/Write/Edit/Glob/Grep |
| Bash 工具 | ✅ 已实现 | SDK 内置 |
| Web 搜索 | ✅ 已实现 | SDK 内置 WebSearch/WebFetch |
| **Session 恢复** | ✅ 已验证 | E2E 测试通过，reload 后 history 保留，AI 能记住上下文 |

---

#### 1.5 E2E Testing Skill/Agent 已创建

**问题**: LLM 输出是非确定性的，如何正确测试 AI 功能？

**现状**: E2E 测试正确地测试**技术持久化**（消息存储、历史加载）而不是 AI 内容。

**方案**: 创建 MindPulse 专用 E2E testing skill 和 agent：

- `.claude/agents/mindpulse-e2e-runner.md` - 专用测试 agent
- `.claude/skills/e2e-testing/SKILL.md` - 测试 skill
- 区分 Type A (确定性) 和 Type B (概率性) 测试
- Type A: 必须 100% 通过；Type B: 使用 pass@k 指标

**运行测试**:
```bash
npx playwright test e2e/session-resume.spec.js
# 3 passed (46.9s)
```

---

---

## 二、真实改进需求

### P0 - 重要功能

#### 1. CLAUDE.md 加载验证

**问题**: `setting_sources=["project"]` 已配置，不确定是否生效。

**方案**: 添加日志验证 CLAUDE.md 是否被 SDK 读取。

---

#### 2. 跨会话记忆（Session Note）

**问题**: AI 无法跨会话记忆关键信息。不同 session 之间无共享知识。

**现状**: 每次都是新 session，AI 只记得当前会话内的事。

**方案**: 参考 Mini-Agent，实现持久化 Session Note Tool。

---

#### 3. 上下文摘要

**问题**: 长对话无 Token 控制，可能溢出。

**现状**: SDK 有 `max_turns=100`，但无主动摘要。

**方案**: 实现 Token 预算监控，超限时自动摘要。

---

### P1 - 稳定性

#### 4. 重试机制

**问题**: API 失败直接报错，无重试。

**方案**: 参考 Mini-Agent 的 RetryWrapper，实现指数退避。

---

#### 5. 日志增强

**问题**: 只有基础 logging。

**方案**: 参考 Mini-Agent AgentLogger，实现完整请求/响应日志。

---

### P2 - 扩展能力

#### 6. 技能暴露

**问题**: `Skill` 工具已配置，用户无法调用。

**方案**: 前端添加技能选择器或命令提示。

---

#### 7. MCP / ACP

**问题**: 无外部工具和编辑器集成。

**方案**: 研究 SDK 是否支持 MCP；参考 Mini-Agent 实现 ACP。

---

## 三、推荐优先级

```
Phase 0: 验证
├── 1. CLAUDE.md 加载验证

Phase 1: 核心体验
├── 2. 跨会话记忆 (Session Note)
└── 3. 上下文摘要

Phase 2: 稳定性
├── 4. 重试机制
└── 5. 日志增强

Phase 3: 扩展
├── 6. 技能暴露
└── 7. MCP / ACP
```

---

## 四、下一步

**CLAUDE.md 加载验证** 是最简单的下一步：

- 添加几行日志确认 SDK 是否读取了 CLAUDE.md
- 验证 project setting 是否生效