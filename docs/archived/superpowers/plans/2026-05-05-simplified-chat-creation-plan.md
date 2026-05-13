# Simplified Chat Creation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify chat creation flow by removing `/api/chats/init` and auto-creating Chat + AgentSession in WebSocket handler

**Architecture:** WebSocket `chat` message handler will check if chat exists, create if not, then forward to AgentSession. Frontend removes draftChat state management.

**Tech Stack:** Python/FastAPI (backend), React (frontend), Playwright (E2E)

---

## File Structure

| File | Responsibility |
|------|----------------|
| `server/main.py` | WebSocket handler, chat auto-creation logic |
| `client/App.jsx` | Remove draftChat state, simplify createChat/selectChat/handleSendMessage |
| `docs/design/functional-design.md` | Update to reflect new flow |
| `e2e/full-flow.spec.js` | Update E2E tests for new New Chat behavior |

---

## Task 1: Backend - WebSocket chat message auto-creation

**Files:**
- Modify: `server/main.py:276-294` (chat message handler)

- [ ] **Step 1: Review current chat message handler**

Current code at lines 276-294:
```python
elif msg_type == "chat":
    if not chat_id or not user_id:
        await websocket.send_json({
            "type": "error",
            "error": "Must subscribe first",
        })
        continue
    content = message["content"]
    _logger.debug(
        f"[WebSocket] Chat msg for chat_id={chat_id}, "
        f"content={content[:30]}..."
    )
    session = get_or_create_session(chat_id, user_id)
    await session.send_message(content)
```

- [ ] **Step 2: Write the failing test**

In `tests/test_main.py`, add test:
```python
def test_chat_auto_creates_chat_and_session():
    """When chat message received for non-existent chat, chat and session are auto-created."""
    # Create a temp chat_id not in database
    temp_chat_id = str(uuid4())
    user_id = "testuser"

    # Simulate WebSocket message
    # Verify chat is created in DB
    # Verify session is created in _sessions
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_main.py::test_chat_auto_creates_chat_and_session -v`
Expected: FAIL (chat doesn't exist in DB)

- [ ] **Step 4: Write minimal implementation**

Replace the chat message handler:
```python
elif msg_type == "chat":
    if not chat_id or not user_id:
        await websocket.send_json({
            "type": "error",
            "error": "Must subscribe first",
        })
        continue
    content = message["content"]
    _logger.info(f"[WS] chat message for chat_id={chat_id}, user_id={user_id}")

    # Check if chat exists, create if not
    chat = chat_store.get_chat(chat_id, user_id)
    if not chat:
        _logger.info(f"[WS] Chat {chat_id} not found, creating new...")
        agent_session = AgentSession(user_id=user_id)
        session_id = await agent_session.init()
        if not session_id:
            await websocket.send_json({"type": "error", "error": "Failed to create chat session"})
            continue
        chat = chat_store.create_chat(chat_id, user_id, None, session_id)
        _logger.info(f"[WS] Created new chat {chat_id} with session {session_id}")

    session = get_or_create_session(chat_id, user_id)
    await session.send_message(content)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_main.py::test_chat_auto_creates_chat_and_session -v`
Expected: PASS

- [ ] **Step 6: Run all backend tests**

Run: `uv run pytest tests/ -v`
Expected: All pass (no regression)

- [ ] **Step 7: Commit**

```bash
git add server/main.py tests/test_main.py
git commit -m "feat: auto-create chat and session in WebSocket chat handler"
```

---

## Task 2: Frontend - Remove draftChat state

**Files:**
- Modify: `client/App.jsx` (remove draftChat, simplify createChat/selectChat/handleSendMessage)

- [ ] **Step 1: Review current state management**

Current state in `ChatApp` component:
- `draftChat` state - to be removed
- `initDraftChat()` function - to be removed
- `isDraftChat()` function - to be removed
- `createChat()` - to be simplified
- `handleSendMessage()` - to be simplified

- [ ] **Step 2: Write the failing test**

In `client/tests/App.test.jsx` (or create if doesn't exist), add test:
```javascript
test('createChat does not add to chats list', async () => {
  const { createChat } = useApp();
  createChat();
  // chats list should not include the new chat until message is sent
  expect(screen.queryByText('New Chat')).toBeNull();
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `npm test -- --run client/tests/App.test.jsx`
Expected: FAIL (current implementation adds to list)

- [ ] **Step 4: Write minimal implementation**

Simplify `ChatApp` component:

```javascript
// Remove from state:
// const [draftChat, setDraftChat] = useState(null);

// Remove these functions:
// - initDraftChat
// - isDraftChat

// Simplify createChat:
const createChat = () => {
    const tempId = crypto.randomUUID();
    setSelectedChatId(tempId);
    setMessages([]);
    // Do NOT add to chats list
};

// Simplify selectChat:
const selectChat = (chatId) => {
    console.log("[DEBUG] selectChat:", chatId);
    selectedChatIdRef.current = chatId;
    setSelectedChatId(chatId);
    setMessages([]);
};

// Simplify handleSendMessage (remove initDraftChat call):
const handleSendMessage = async (content) => {
    if (!selectedChatId || !isConnected) return;

    const chatId = selectedChatId;
    // No more isDraftChat check - directly send
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        return;
    }

    if (!loadingRef.current) {
        loadingRef.current = true;
        setIsLoading(true);
    }

    setMessages((prev) => [
        ...prev,
        {
            id: crypto.randomUUID(),
            role: "user",
            content,
            timestamp: new Date().toISOString(),
        },
    ]);

    wsRef.current.send(JSON.stringify({
        type: "chat",
        content,
        chatId,
    }));
};
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test -- --run client/tests/App.test.jsx`
Expected: PASS

- [ ] **Step 6: Run all frontend tests**

Run: `npm test -- --run`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add client/App.jsx client/tests/App.test.jsx
git commit -m "refactor: remove draftChat state, simplify chat creation flow"
```

---

## Task 3: Update E2E tests

**Files:**
- Modify: `e2e/full-flow.spec.js`

- [ ] **Step 1: Review current E2E test expectations**

Current test expects "New Chat" to appear in sidebar immediately after clicking. New behavior:
- "New Chat" creates temp chat that does NOT appear in sidebar
- Chat appears in sidebar only after sending first message

- [ ] **Step 2: Write the failing test**

In `e2e/full-flow.spec.js`, update test:
```javascript
test('complete user flow: register -> create chat -> send message -> chat appears in list', async ({ page }) => {
  // ... register flow same ...
  
  // 2. Click New Chat (temp chat, NOT in sidebar yet)
  await page.getByRole('button', { name: 'New Chat' }).click();
  
  // 3. Chat should NOT be in sidebar yet
  const sidebarChatsBefore = await page.locator('[class*="cursor-pointer"]').count();
  expect(sidebarChatsBefore).toBe(0); // No chats in sidebar
  
  // 4. Send message
  const input = page.getByPlaceholder('Type a message...');
  await input.fill('Hello');
  await input.press('Enter');
  
  // 5. Wait for response
  await expect(page.getByText('Thinking...')).toBeVisible({ timeout: 30000 });
  
  // 6. Now chat SHOULD appear in sidebar
  const sidebarChatsAfter = await page.locator('[class*="cursor-pointer"]').count();
  expect(sidebarChatsAfter).toBe(1);
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `npx playwright test e2e/full-flow.spec.js --project=chromium`
Expected: FAIL at step 6 (chat not in list after result)

- [ ] **Step 4: Implement (no code change needed, this is just verifying test is correct)**

If test fails at step 3 (chat already in sidebar), the test expectation is correct and implementation needs fixing from Task 2.

If test fails at step 6, check if `fetchChats()` is called on `result` event in App.jsx.

- [ ] **Step 5: Run test to verify it passes**

After both Task 1 and Task 2 are complete:
Run: `npx playwright test e2e/full-flow.spec.js --project=chromium`
Expected: PASS

- [ ] **Step 6: Run all E2E tests**

Run: `npx playwright test e2e/ --project=chromium`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add e2e/full-flow.spec.js
git commit -m "test: update E2E tests for simplified chat creation flow"
```

---

## Task 4: Update functional design doc

**Files:**
- Modify: `docs/design/functional-design.md`

- [ ] **Step 1: Review current functional design**

Check sections 2.1, 2.2, 3.x for references to draft chat, initDraftChat, etc.

- [ ] **Step 2: Write the changes**

Update section 2.1 and 2.2 to reflect new flow:
- New Chat creates temp chat (not in list)
- Send message triggers auto-creation
- No more `/api/chats/init`

- [ ] **Step 3: Commit**

```bash
git add docs/design/functional-design.md
git commit -m "docs: update functional design for simplified chat creation"
```

---

## Execution Order

1. **Task 1** (Backend) - Must complete first
2. **Task 2** (Frontend) - Can proceed after Task 1
3. **Task 3** (E2E) - Run after Task 1 + Task 2 complete
4. **Task 4** (Docs) - Run last

**Do NOT skip tasks.** Each task has a specific deliverable.

---

## Verification

After all tasks:
```bash
# Backend tests
uv run pytest tests/ -v

# Frontend tests
npm test -- --run

# E2E tests
npx playwright test e2e/ --project=chromium

# Manual verification
npm run dev
# Create New Chat -> Send message -> Verify chat appears in sidebar
# Switch chats -> Verify history loads
```

---

## Plan Complete

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?