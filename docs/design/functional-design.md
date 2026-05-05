# claude-chat 功能设计文档

> 从当前实现还原的功能设计（to-be）。描述系统应该做什么。

**最后更新：** 2026-05-05

---

## 功能概述

claude-chat 是一个 AI 助手聊天应用，支持：
- 用户认证
- 多会话管理
- 实时 AI 对话（流式输出）
- 思考过程展示
- 工具调用展示
- 文件上传

---

## 用户角色与认证

### 1.1 注册

**流程：**
1. 用户输入 email + password
2. 前端发送 `POST /api/auth/register`
3. 后端创建用户，返回 JWT token
4. 前端保存 token 到 localStorage，自动登录

**约束：**
- email 格式验证
- password 最少 6 字符

### 1.2 登录

**流程：**
1. 用户输入 email + password
2. 前端发送 `POST /api/auth/login`
3. 后端验证，返回 JWT token
4. 前端保存 token，自动进入应用

### 1.3 登出

**流程：**
1. 用户点击 logout
2. 前端清除 localStorage 的 token
3. 关闭 WebSocket 连接
4. 回到登录页面

### 1.4 Token 验证

**流程：**
1. 页面加载时，检查 localStorage 是否有 token
2. 发送 `GET /api/auth/me` 验证
3. 有效则进入应用，无效则显示登录页

---

## 聊天会话管理

### 2.1 创建新聊天（New Chat）

**触发：** 用户点击侧边栏的 "New Chat" 按钮

**流程：**
1. 前端创建一个临时 chat（仅内存）
   - 生成 UUID 作为 chat id
   - title = "New Chat"
2. 切换到该 chat（清空消息区域）
3. 用户可以输入消息
4. **如果不发消息就切换走，temp chat 直接丢弃**

**注意：** 前端不把这个 temp chat 加入 sidebar 列表，后端也没有记录。只有发送消息后，才会创建正式的 chat。

### 2.2 发送消息

**触发：** 用户在输入框输入文字，按 Enter 或点击 Send

**流程（New Chat 首次发送）：**
1. 前端发送 WebSocket `chat` 消息
   - chatId = 前端生成的临时 UUID
   - content = 用户输入
2. 后端收到消息，检查 chat 是否存在
3. 如果不存在：
   - 创建 AgentSession（调用 SDK init()）
   - 创建 chat 记录（id=前端UUID, session_id=SDK session_id）
   - 关联 AgentSession 到 Session
4. 后端转发消息给 AgentSession
5. 流式返回 AI 输出
6. 完成后，前端更新 chat 列表（title 可能被更新）

**流程（已有 Chat）：**
1. 前端发送 WebSocket `chat` 消息
   - chatId = 已有的 chat id
2. 后端：
   - 查找/创建 Session（关联到该 chat）
   - 转发消息给 AgentSession
3. 流式返回 AI 输出

### 2.3 查看聊天列表

**触发：** 用户登录后，侧边栏显示聊天列表

**流程：**
1. 前端调用 `GET /api/chats`
2. 后端返回该用户的所有 chat（按 updated_at DESC）
3. 前端渲染列表

**展示：** 按最新更新时间排序，最新的在最上面。

### 2.4 切换聊天

**触发：** 用户点击侧边栏的某个 chat

**流程：**
1. 前端 `selectChat(chatId)`
   - 清空当前消息
   - 设置 selectedChatId
2. 前端发送 WebSocket `subscribe` 消息
3. 后端：
   - 查找/创建 Session
   - 调用 `session.subscribe(websocket)`
   - 查询历史消息，发送 `history`
4. 前端收到 `history`，显示消息

### 2.5 删除聊天

**触发：** 用户点击 chat 旁边的删除按钮

**流程：**
1. 前端调用 `DELETE /api/chats/{chat_id}`
2. 后端：
   - 删除 messages 表记录
   - 删除 chats 表记录
   - 关闭 Session
3. 前端更新 chat 列表
4. 如果删除的是当前 chat，切换到空白状态

---

## 实时消息功能

### 3.1 WebSocket 连接

**时机：** 用户登录后，前端建立 WebSocket 连接

**流程：**
1. 前端 `connectWebSocket()`
2. 后端接受连接，发送 `{"type": "connected"}`
3. 前端保持连接，用于所有实时通信

### 3.2 消息类型

| 方向 | type | 说明 |
|------|------|------|
| C→S | subscribe | 订阅某个 chat |
| C→S | chat | 发送消息 |
| C→S | stop | 停止 AI 生成 |
| S→C | connected | 连接成功 |
| S→C | history | 历史消息 |
| S→C | user_message | 用户消息回显 |
| S→C | assistant_delta | AI 流式输出 |
| S→C | thinking_delta | AI 思考输出 |
| S→C | tool_use | AI 调用工具 |
| S→C | result | AI 完成 |
| S→C | interrupted | AI 被中断 |
| S→C | error | 错误 |

### 3.3 消息过滤

**规则：** 前端只处理当前 chat 的消息

```javascript
// handleWSMessage
const msgChatId = message.chatId || message.chat_id;
if (msgChatId && msgChatId !== selectedChatIdRef.current) {
  return;  // 忽略其他 chat 的消息
}
```

**作用：** 防止切换 chat 时，旧 chat 的消息污染新 chat。

---

## AI 对话功能

### 4.1 流式输出

**流程：**
1. 用户发送消息
2. AI 开始生成响应
3. 后端逐块返回 `assistant_delta`
4. 前端实时更新消息内容
5. AI 完成时，返回 `result`

### 4.2 思考过程

**流程：**
1. AI 生成思考时，后端返回 `thinking_delta`
2. 前端显示 ThinkingBlock
3. 用户可以展开/折叠查看完整思考

### 4.3 工具调用

**流程：**
1. AI 调用工具时，后端返回 `tool_use`
2. 前端显示 ToolUseBlock（可展开）
3. 工具结果作为后续消息的一部分

### 4.4 中断响应

**触发：** 用户点击停止按钮

**流程：**
1. 前端发送 `{"type": "stop"}`
2. 后端调用 `session.stop_response()`
3. Session 取消当前任务，发送 `interrupted`
4. 前端标记消息为非流式

### 4.5 自动标题

**规则：** 首个用户消息的前 50 字符作为 chat 标题

```python
# chat_store.py:71-73
if chat.title == "New Chat" and role == "user":
    title = content[:50] + ("..." if len(content) > 50 else "")
    chat_repo.update_title(chat_id, title)
```

---

## 文件功能

### 5.1 上传文件

**触发：** 用户点击上传按钮，选择文件

**流程：**
1. 前端发送 `POST /api/files/upload`
   - multipart/form-data
   - file + chatId
2. 后端保存到 `{AGENT_PROJECT_ROOT}/{user_id}/{chat_id}/{filename}`
3. 前端显示上传成功

### 5.2 文件下载

**触发：** AI 消息中包含 workspace 文件路径

**流程：**
1. AI 返回消息，包含 `workspace/{user_id}/...` 路径
2. 前端解析路径，显示下载链接
3. 用户点击链接，访问 `/api/files/download?path=xxx`
4. 后端验证路径权限，返回文件

---

## 数据隔离

### 6.1 用户隔离

**规则：** 每个用户只能访问自己的数据

**实现：**
- JWT token 包含 user_id
- 所有 DB 查询都按 user_id 过滤
- 文件存储在 `{user_id}/` 目录下

### 6.2 Workspace 隔离

**规则：** AI 的工作目录按用户分隔

**实现：**
- `AgentSession` 的 cwd = `{AGENT_PROJECT_ROOT}/{user_id}/`
- 不同用户的 AI 看不到彼此的文件

---

## 错误处理

### 7.1 网络错误

- WebSocket 断开时，自动重连（3秒延迟）
- 重连后重新 subscribe 当前 chat

### 7.2 AI 错误

- AI 返回错误时，后端发送 `{"type": "error", "error": "..."}`
- 前端显示错误信息

### 7.3 API 错误

- 注册/登录失败显示错误提示
- 其他 API 错误跳转到登录页

---

## 关键流程图

### 创建并完成一个对话

```
用户登录
    ↓
点击 "New Chat"
    ↓
输入消息 "你好"
    ↓
前端调用 /api/chats/init（创建 formal chat）
    ↓
前端发送 WebSocket chat 消息
    ↓
后端 → AI SDK → 流式响应
    ↓
后端 → assistant_delta / thinking_delta / tool_use
    ↓
前端实时显示
    ↓
后端 → result
    ↓
fetchChats() 更新列表
```

### 切换并查看历史

```
点击 sidebar 中的某个 chat
    ↓
selectChat(chatId)
    ↓
发送 subscribe 消息
    ↓
后端返回 history 消息
    ↓
前端 setMessages(history)
    ↓
显示历史消息
```

---

## Change Log

- 2026-05-05: 初始版本，从当前实现还原功能设计