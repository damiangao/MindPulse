# MindPulse 系统架构

> 本文档描述 MindPulse 聊天应用的系统架构、数据模型和通信协议。

**最后更新：** 2026-05-13

---

## 系统概览

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  ChatList   │  │  ChatWindow  │  │   App.jsx          │  │
│  │  (sidebar)  │  │  (messages)  │  │  (WS connection)   │  │
│  └─────────────┘  └──────────────┘  └────────────────────┘  │
│          │                │                    │              │
│          └────────────────┴────────────────────┘              │
│                         WebSocket / REST API                 │
└────────────────────────────┬──────────────────────────────────┘
                             │
┌────────────────────────────▼──────────────────────────────────┐
│                        Backend (FastAPI)                       │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │   REST API  │  │  WebSocket   │  │  Session Manager   │   │
│  │  /api/chats │  │   /ws        │  │  _sessions dict    │   │
│  └─────────────┘  └──────────────┘  └────────────────────┘   │
│          │                │                    │              │
│          └────────────────┴────────────────────┘              │
│                         ChatStore / DB                         │
└─────────────────────────────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │     SQLite     │
                    │   data/chats.db │
                    └─────────────────┘
```

---

## 核心概念

### 1. Chat 类型

系统有两种 Chat：

| 类型 | 说明 | 有 DB 记录 | session_id 来源 |
|------|------|:---:|------|
| **Draft Chat** | "New Chat" 按钮创建的本地临时 chat | 否 | 无 |
| **Formal Chat** | 发送第一条消息后，通过 SDK 创建 | 是 | SDK 返回的 session_id |

**Chat 表的字段：**
- `id` = 前端生成的 UUID（来自 draft chat id）
- `session_id` = SDK 返回的 session_id（与 id 不同）

### 2. Session 与 Session Manager

**后端 Session（Python）：**
- `Session` 类：管理一个 Chat 的 WebSocket 订阅者 + AI 交互
- 持有 `AgentSession`（SDK client 包装）
- `_sessions` dict：key = `(chat_id, user_id)`，value = `Session` 实例

**AgentSession（Python）：**
- 包装 `ClaudeSDKClient`
- 管理与 AI 的长连接
- 支持 interrupt（取消正在生成的响应）
- 支持断点重连（通过 session_id resume）

### 3. SDK 内置工具

MindPulse 使用 `claude-agent-sdk`，以下工具已内置：

| 工具 | 功能 |
|------|------|
| `Bash` | 执行 shell 命令 |
| `Read/Write/Edit` | 文件操作 |
| `Glob/Grep` | 搜索文件 |
| `WebSearch/WebFetch` | 网络搜索 |
| `Skill` | 调用 Claude Skills |

---

## 数据模型

### Chat（chats 表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT (PK) | 前端生成的 UUID |
| user_id | TEXT | 用户 ID（workspace 目录名） |
| session_id | TEXT | SDK 返回的 session_id |
| title | TEXT | Chat 标题 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 最后更新时间 |

### ChatMessage（messages 表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT (PK) | UUID |
| chat_id | TEXT (FK) | 关联的 chat id |
| user_id | TEXT | 用户 ID |
| role | TEXT | "user" 或 "assistant" |
| content | TEXT | 消息内容 |
| timestamp | TIMESTAMP | 创建时间 |

---

## WebSocket 消息协议

### 客户端 → 服务器

```javascript
// Subscribe
{ "type": "subscribe", "chatId": "xxx", "authorization": "Bearer xxx" }

// Chat（发送消息）
{ "type": "chat", "content": "你好", "chatId": "xxx" }

// Stop（停止生成）
{ "type": "stop", "chatId": "xxx" }
```

### 服务器 → 客户端

```javascript
// 连接成功
{ "type": "connected", "message": "..." }

// 历史消息
{ "type": "history", "messages": [...], "chatId": "xxx" }

// 用户消息（回显）
{ "type": "user_message", "content": "xxx", "chat_id": "xxx" }

// 流式文本
{ "type": "assistant_delta", "delta": "xxx", "chat_id": "xxx" }

// 流式思考
{ "type": "thinking_delta", "delta": "xxx", "chat_id": "xxx" }

// Tool 使用
{ "type": "tool_use", "tool_name": "xxx", "tool_input": {...}, "chat_id": "xxx" }

// 完成
{ "type": "result", "success": true, "cost": 0.001, "duration": 5000, "chat_id": "xxx" }

// 中断
{ "type": "interrupted", "chat_id": "xxx" }

// 错误
{ "type": "error", "error": "xxx", "chat_id": "xxx" }
```

---

## REST API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/register` | POST | 注册 |
| `/api/auth/login` | POST | 登录 |
| `/api/auth/me` | GET | 获取当前用户 |
| `/api/chats` | GET | 获取所有 chats |
| `/api/chats` | POST | 创建新 chat |
| `/api/chats/init` | POST | 初始化 draft chat |
| `/api/chats/{chat_id}` | GET | 获取单个 chat |
| `/api/chats/{chat_id}` | DELETE | 删除 chat |
| `/api/chats/{chat_id}/messages` | GET | 获取消息 |
| `/api/files/upload` | POST | 上传文件 |
| `/api/files/download` | GET | 下载文件 |

---

## 关键文件

| 文件 | 职责 |
|------|------|
| `client/App.jsx` | 主组件，WebSocket 管理，状态管理 |
| `client/components/ChatList.jsx` | 侧边栏聊天列表 |
| `client/components/ChatWindow.jsx` | 聊天消息展示和输入 |
| `server/main.py` | FastAPI 应用，REST API，WebSocket 端点 |
| `server/session.py` | Session 类，管理 AI 交互和 WebSocket 订阅 |
| `server/ai_client.py` | AgentSession 包装 SDK |
| `server/chat_store.py` | DB 操作门面 |
| `server/models.py` | 数据模型 |
| `server/auth.py` | JWT 工具 |
| `server/database/connection.py` | SQLite 连接管理 |

---

## Change Log

- 2026-05-13: 整合 current-state.md 和 functional-design.md，添加 SDK 内置工具说明