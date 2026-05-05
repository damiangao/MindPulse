# claude-chat 项目设计文档

> 当前系统现状（as-is），不是目标设计（to-be）。用于理解系统如何工作，为后续修复bug和优化提供基础。

**最后更新：** 2026-05-05

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  ChatList   │  │  ChatWindow  │  │   App.jsx          │  │
│  │  (sidebar)  │  │  (messages)  │  │  (WS connection)   │  │
│  └─────────────┘  └──────────────┘  └────────────────────┘  │
│          │                │                    │              │
│          └────────────────┴────────────────────┘              │
│                         WebSocket / REST API                   │
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
                    │     SQLite      │
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
| **Formal Chat** | 发送第一条消息后，通过 `/api/chats/init` 创建 | 是 | SDK 返回的 session_id |

**Chat 表的字段：**
- `id` = 前端生成的 UUID（来自 draft chat id）
- `session_id` = SDK 返回的 session_id（与 id 不同）

**Draft Chat 的特征：**
- ID 是本地生成的 `crypto.randomUUID()`
- 没有对应的后端 Session
- 前端维护，切换时会清空

**Formal Chat 的特征：**
- ID 是前端传来的 UUID（不是 SDK session_id）
- session_id 字段存储 SDK 的 session_id
- 有对应的后端 `AgentSession`
- 有 DB 记录（chats 表 + messages 表）

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

### 3. WebSocket 连接

**连接生命周期：**
1. 前端连接 `/ws`
2. 后端发送 `{"type": "connected"}`
3. 前端发送 subscribe 消息
4. 后端创建/获取 Session，发送 history
5. 保持连接，用于 chat / stop 消息

**关键：单个 WebSocket 连接**
- 前端只建立一个 WebSocket 连接
- 切换 Chat 时，发送新的 subscribe 消息
- 不关闭连接，不重新连接

---

## 数据模型

### Chat（chats 表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT (PK) | 前端生成的 UUID（来自 draft chat id） |
| user_id | TEXT | 用户 ID（workspace 目录名） |
| session_id | TEXT | SDK 返回的 session_id（与 id 不同） |
| title | TEXT | Chat 标题 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 最后更新时间 |

**注意：** `id` 和 `session_id` 是不同的值。前端用 `id` 作为 chatId 来 subscribe 后端 Session；Session 内部用 `session_id` 来 resume SDK 连接。

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

## 前端架构

### App.jsx 状态管理

```javascript
// 主要状态
user, token              // 认证状态
chats, setChats          // Chat 列表（formal chats）
selectedChatId           // 当前选中的 Chat ID
messages                 // 当前 Chat 的消息列表
draftChat                // 当前的 Draft Chat（如果有）

// Refs（避免闭包问题）
selectedChatIdRef         // 当前 selectedChatId 的引用
loadingRef               // 防止重复发送
connectingRef            // 防止重复连接
```

### Draft Chat 模式

```
1. 用户点击 "New Chat"
   └── createChat() 被调用
   └── 创建 draftChat: { id: tempId, title: "New Chat", ... }
   └── setSelectedChatId(tempId)
   └── setMessages([])

2. 用户发送消息
   └── handleSendMessage(selectedChatId)
   └── isDraftChat(selectedChatId) → true
   └── 调用 /api/chats/init 创建 formal chat
   └── 获取 formal chat id
   └── 发送 WebSocket chat 消息

3. 收到 result
   └── fetchChats() 更新聊天列表
   └── draftChat 被清空
```

### Chat 切换流程（selectChat）

```javascript
function selectChat(chatId) {
  setDraftChat(null);                    // 清空 draft
  selectedChatIdRef.current = chatId;    // 更新 ref
  setSelectedChatId(chatId);             // 更新 state
  setMessages([]);                       // 清空当前消息
  loadingRef.current = false;
  setIsLoading(false);
}
```

然后 useEffect 检测到 selectedChatId 变化，发送 subscribe 消息。

### handleWSMessage 消息处理

```javascript
function handleWSMessage(message) {
  const msgChatId = message.chatId || message.chat_id;
  // 过滤：忽略不属于当前 chat 的消息
  if (msgChatId && msgChatId !== selectedChatIdRef.current) {
    return;
  }

  switch (message.type) {
    case "history":
      // 加载历史消息
      // 注意：isDraftChat 时跳过（draft 没有历史）
      setMessages(message.messages || []);
      break;
    case "user_message":
      break;
    case "assistant_delta":
      // 流式文本更新
      break;
    // ... 其他消息类型
  }
}
```

---

## 后端架构

### REST API 端点

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

### WebSocket 消息协议

**客户端 → 服务器：**

```javascript
// Subscribe
{ "type": "subscribe", "chatId": "xxx", "authorization": "Bearer xxx" }

// Chat（发送消息）
{ "type": "chat", "content": "你好", "chatId": "xxx" }

// Stop（停止生成）
{ "type": "stop", "chatId": "xxx" }
```

**服务器 → 客户端：**

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

### Session 管理

```python
# main.py
_sessions: dict[tuple[str, str], Session] = {}

def get_or_create_session(chat_id: str, user_id: str) -> Session:
    key = (chat_id, user_id)
    if key not in _sessions:
        _sessions[key] = Session(chat_id, user_id)
    return _sessions[key]
```

### Chat 初始化流程（_create_sdk_chat）

```python
async def _create_sdk_chat(chat_id: str, user_id: str, title: str | None = None):
    # 1. 创建 AgentSession
    agent_session = AgentSession(user_id=user_id)

    # 2. 调用 init() 获取 SDK session_id
    session_id = await agent_session.init()

    # 3. 存储到 DB
    chat = chat_store.create_chat(chat_id, user_id, title, session_id)

    return chat.to_dict()
```

---

## 当前已知问题

### 1. Chat Switching Bug（待验证）

**现象：** 切换到已有 Chat 时，历史消息没有显示。

**可能原因：**
- `selectChat` 清空了 `messages`，然后等待 `history` 消息
- 但 `history` 消息可能被 `selectedChatIdRef` 的旧值过滤掉
- `selectedChatIdRef.current` 在 `selectChat` 中被更新，但 `handleWSMessage` 的闭包可能有问题

**关键代码位置：**
- `App.jsx:261-265` — handleWSMessage 过滤逻辑
- `App.jsx:522-530` — selectChat 函数
- `App.jsx:431-437` — WebSocket 连接 useEffect
- `App.jsx:439-451` — 订阅 useEffect

### 2. E2E 测试不稳定

**现象：** playwright 测试有时通过，有时失败。

**可能原因：**
- React StrictMode 重复调用 useEffect
- WebSocket 连接时序问题
- `connectingRef` 逻辑不够完善

### 3. Console.log 残留

`App.jsx` 中有多处 `[DEBUG]` 日志，影响生产可观察性。

---

## 关键文件清单

| 文件 | 职责 |
|------|------|
| `client/App.jsx` | 主组件，WebSocket 管理，状态管理 |
| `client/components/ChatList.jsx` | 侧边栏聊天列表 |
| `client/components/ChatWindow.jsx` | 聊天消息展示和输入 |
| `client/components/FileUpload.jsx` | 文件上传 |
| `server/main.py` | FastAPI 应用，REST API，WebSocket 端点 |
| `server/session.py` | Session 类，管理 AI 交互和 WebSocket 订阅 |
| `server/ai_client.py` | AgentSession 包装 SDK |
| `server/chat_store.py` | DB 操作门面 |
| `server/models.py` | 数据模型 |
| `server/auth.py` | JWT 工具 |
| `server/auth_routes.py` | 认证 API |
| `server/database/connection.py` | SQLite 连接管理 |
| `server/database/repositories/chat.py` | Chat DB 操作 |
| `server/database/repositories/message.py` | Message DB 操作 |

---

## Change Log

- 2026-05-05: 初始版本，记录当前系统架构和已知问题