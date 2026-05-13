# 简化 Chat 创建流程设计

**状态：** Draft
**日期：** 2026-05-05
**问题：** 当前 draft chat → init → formal chat 流程复杂，导致前端状态不一致，bug 难修。

---

## 目标

简化 Chat 创建流程：
- 移除 `/api/chats/init` 接口
- 前端无需管理 draft chat 状态
- 后端在首次收到消息时自动创建 Chat + AgentSession

---

## 方案概述

### 当前流程（3 步）

```
1. createChat()        → 前端创建 draft chat
2. initDraftChat()     → POST /api/chats/init（创建 formal chat）
3. ws chat 消息        → 发送消息
```

### 简化后流程（1 步）

```
1. ws chat 消息        → 后端判断 chat 是否存在
                          → 不存在则创建 Chat + AgentSession
                          → 然后转发消息
```

---

## 详细设计

### 1. WebSocket `chat` 消息处理

**修改位置：** `server/main.py` - `websocket_endpoint`

**日志埋点：**
```python
elif msg_type == "chat":
    if not chat_id or not user_id:
        # error
    # 检查 chat 是否存在
    _logger.info(f"[WS] chat message for chat_id={chat_id}, user_id={user_id}")
    chat = chat_store.get_chat(chat_id, user_id)
    if not chat:
        _logger.info(f"[WS] Chat {chat_id} not found, creating new...")
        agent_session = AgentSession(user_id=user_id)
        session_id = await agent_session.init()
        chat = chat_store.create_chat(chat_id, user_id, None, session_id)
        _logger.info(f"[WS] Created new chat {chat_id} with session {session_id}")
    # 已有 Session 则直接使用
    session = get_or_create_session(chat_id, user_id)
    await session.send_message(content)
```

**关键日志点：**
- 收到 chat 消息时（INFO）
- Chat 不存在，创建时（INFO）
- Chat 已存在，直接使用时（DEBUG）
- Session 发送/接收消息（DEBUG）

### 2. Chat 创建时机

| 时机 | 当前 | 简化后 |
|------|------|--------|
| New Chat 按钮 | 前端创建 draft | 前端创建（仅 UI） |
| 发送消息 | 调用 /api/chats/init | WebSocket 内自动创建 |

### 3. 前端修改

**移除：**
- `initDraftChat()` 函数
- `draftChat` 状态
- 调用 `/api/chats/init` 的逻辑

**保留：**
- `createChat()` — 创建本地临时 chat（用于 UI）
- chats 列表管理

**关键变更：**
- 发送消息时，不再调用 `/api/chats/init`
- 直接发送 WebSocket `chat` 消息
- 后端会在第一次发消息时自动创建 chat + session

### 4. 后端修改

**修改文件：**
- `server/main.py` — WebSocket handler 增加 chat 创建逻辑

**新增逻辑：**
```python
# 检查 chat 是否存在
chat = chat_store.get_chat(chat_id, user_id)
if not chat:
    # 创建 AgentSession 和 Chat
    agent_session = AgentSession(user_id=user_id)
    session_id = await agent_session.init()
    chat = chat_store.create_chat(chat_id, user_id, None, session_id)
```

### 5. API 接口变化

**移除：**
- `POST /api/chats/init` — 不再需要
- `POST /api/chats` — 删除（前端不再调用）

**保留：**
- `GET /api/chats` — 获取聊天列表
- `DELETE /api/chats/{chat_id}` — 删除聊天

---

## 前端状态变化

### 简化前

```javascript
// App.jsx
const [draftChat, setDraftChat] = useState(null);  // 需要管理
const [selectedChatId, setSelectedChatId] = useState(null);

// createChat - 创建 draft
const createChat = () => {
    setDraftChat({ id: tempId, title: "New Chat", ... });
    setSelectedChatId(tempId);
    setMessages([]);
};

// initDraftChat - 调用 API 创建 formal chat
const initDraftChat = async (chatId) => {
    const res = await fetch('/api/chats/init', { ... });
    // 更新 chats 列表
    setChats(prev => [formalChat, ...prev]);
    // 切换到 formal chat
    setSelectedChatId(data.id);
    setDraftChat(null);
};

// handleSendMessage - 判断是 draft 还是 formal
if (isDraftChat(selectedChatId)) {
    await initDraftChat(selectedChatId);
}
ws.send({ type: "chat", content, chatId: newId });
```

### 简化后

```javascript
// App.jsx
// 不需要 draftChat 状态
const [selectedChatId, setSelectedChatId] = useState(null);

// createChat - 仅创建本地 UI 状态，不加入列表
const createChat = () => {
    const tempId = crypto.randomUUID();
    setSelectedChatId(tempId);
    setMessages([]);
};

// handleSendMessage - 直接发消息，后端自动创建 chat
const handleSendMessage = async (content) => {
    const chatId = selectedChatId;
    ws.send({ type: "chat", content, chatId });
};

// selectChat - 如果切换走，不需要任何操作
// （temp chat 因为不在列表，用户无法再切回来看到它）
const selectChat = (chatId) => {
    selectedChatIdRef.current = chatId;
    setSelectedChatId(chatId);
    setMessages([]);
};
```

**关键变化：**
- 不需要 `draftChat` 状态
- 不需要 `initDraftChat()`
- 不需要 `isDraftChat()` 判断
- createChat 不加入 chats 列表（用户感知不到 temp chat 存在）
- 切换走时不需要清理 temp chat（因为不在列表，不会再被选中）

---

## 测试验证

### 流程 1：New Chat → 发送消息

```
1. 用户点击 "New Chat"
   → 前端创建 temp chat（仅内存，不加入列表）
   → 切换到该 chat（messages = []）

2. 用户输入消息并发送
   → 前端发送 ws { type: "chat", chatId: tempId, content }
   → 后端发现 chat 不存在，创建 Chat + AgentSession
   → 后端转发消息给 AgentSession
   → 流式响应
   → 后端返回 result
   → 前端收到 result → fetchChats() 更新列表
   → chat 现在出现在 sidebar
```

**Chat 进入列表的时机：**
- 用户发送消息后，后端返回 `result` 时
- 前端 `handleWSMessage` 处理 `result` 时调用 `fetchChats()`
- 此时从后端获取完整列表，包含新创建的 chat

### 流程 2：New Chat → 切换走（未发消息）

```
1. 用户点击 "New Chat"
   → 前端创建 temp chat，切换到该 chat

2. 用户还没发消息就点击了其他 chat
   → selectChat(otherChatId)
   → temp chat（messages=[]）被丢弃
   → sidebar 不显示这个 temp chat

3. 用户再次点击 "New Chat"
   → 正常创建新的 temp chat
```

### 流程 3：切换 Chat → 查看历史

```
1. 用户点击 sidebar 中的某个 chat
   → selectChat(chatId)
   → 前端发送 ws { type: "subscribe", chatId }
   → 后端返回 history
   → 前端显示消息
```

---

## 前端代码变更清单

**删除：**
- `draftChat` 状态（App.jsx）
- `initDraftChat()` 函数
- `isDraftChat()` 函数
- 调用 `/api/chats/init` 的代码

**简化：**
- `createChat()` — 不加入 chats 列表
- `selectChat()` — 不需要清理 draft 状态
- `handleSendMessage()` — 不需要判断 draft/formal

---

## 待确认问题

1. [x] 前端 `createChat` 是否需要在 chats 列表中？
   - **决策：否**。temp chat 仅内存中，不加入 sidebar 列表。

2. [x] 如果用户创建了 New Chat，但从未发消息，chat 是否保留？
   - **决策：删除**。用户切换走时，如果还没发过消息，temp chat 丢弃。
   - 由于 temp chat 不在列表，用户无法再切回来。

3. [x] `POST /api/chats` 是否还有保留价值？
   - **决策：无用，删除**。

4. [x] 边界情况处理
   - New Chat → 直接上传文件：**不处理**（用户不会这么做）
   - 切换走未发消息，再切回来：**不可能**，因为 temp chat 不在列表
   - 发送消息后断网：**不处理**（极端异常）

---

## Change Log

- 2026-05-05: 初始版本，简化 Chat 创建流程设计
- 2026-05-05: 更新决策：temp chat 不加入列表，未发消息则删除；移除回滚计划；增加前端代码变更清单