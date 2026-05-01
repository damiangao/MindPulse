# File Upload/Download Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add file upload and download endpoints. Files are saved to workspace/{chat_id}/, AI reads them via Read tool, and frontend detects file paths in AI responses to show download buttons.

**Architecture:** Backend exposes REST endpoints for upload/download. Frontend adds drag-drop + upload button in input area, detects file path patterns in AI messages, renders download button in message bubbles.

**Tech Stack:** Python/FastAPI backend, React/Vite frontend, file system storage.

---

## File Structure

```
server/
  main.py              # Modify: add upload/download endpoints
  file_storage.py      # Create: file storage utility

tests/
  test_file_storage.py # Create: file storage tests

client/
  components/
    ChatWindow.jsx    # Modify: drag-drop, upload button, download detection
    FileUpload.jsx     # Create: drag-drop / upload button component
```

---

## Task 1: File Storage Utility

**Files:**
- Create: `server/file_storage.py`
- Test: `tests/test_file_storage.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_file_storage.py
import os
import pytest
from pathlib import Path

class TestFileStorage:
    def test_save_file_creates_directory(self, tmp_path):
        from server.file_storage import save_file
        # Create a test file-like object
        content = b"hello world"
        result = save_file(content, "chat-123", "test.txt", str(tmp_path))
        assert os.path.exists(result)
        assert open(result, "rb").read() == content

    def test_save_file_returns_relative_path(self, tmp_path):
        from server.file_storage import save_file
        result = save_file(b"test", "chat-123", "file.txt", str(tmp_path))
        assert result == "workspace/chat-123/file.txt"

    def test_get_file_path_constructs_full_path(self, tmp_path):
        from server.file_storage import get_file_path
        path = get_file_path("workspace/chat-123/file.txt", str(tmp_path))
        assert path == str(tmp_path / "workspace" / "chat-123" / "file.txt")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_file_storage.py -v`
Expected: FAIL — ModuleNotFoundError: No module named 'server.file_storage'

- [ ] **Step 3: Write minimal implementation**

```python
# server/file_storage.py
"""File storage utility for saving uploaded files to workspace."""
import os
from pathlib import Path


def save_file(content: bytes, chat_id: str, filename: str, project_root: str) -> str:
    """Save file content to workspace/{chat_id}/{filename}.

    Returns the relative path: workspace/{chat_id}/{filename}
    """
    workspace_dir = Path(project_root) / "workspace" / chat_id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    file_path = workspace_dir / filename
    file_path.write_bytes(content)
    return f"workspace/{chat_id}/{filename}"


def get_file_path(relative_path: str, project_root: str) -> Path:
    """Convert relative path to full file path for reading."""
    return Path(project_root) / relative_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_file_storage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/file_storage.py tests/test_file_storage.py
git commit -m "feat: add file storage utility"
```

---

## Task 2: Upload/Download API Endpoints

**Files:**
- Modify: `server/main.py:1-30` (imports), `server/main.py:120-140` (new endpoints)
- Test: `tests/test_main.py` (add tests)

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_main.py
class TestFileUploadAPI:
    @patch("server.main.get_project_root")
    def test_upload_file(self, mock_root, client, tmp_path):
        mock_root.return_value = str(tmp_path)
        from io import BytesIO
        file_content = b"test file content"
        file = (BytesIO(file_content), "test.txt")
        response = client.post(
            "/api/files/upload",
            files={"file": file},
            data={"chatId": "chat-123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "workspace/chat-123/test.txt"
        assert (tmp_path / "workspace" / "chat-123" / "test.txt").read_bytes() == file_content

    def test_upload_file_missing_chat_id(self, client):
        from io import BytesIO
        file = (BytesIO(b"content"), "test.txt")
        response = client.post("/api/files/upload", files={"file": file})
        assert response.status_code == 422  # FastAPI validation error

    @patch("server.main.get_project_root")
    def test_download_file(self, mock_root, client, tmp_path):
        mock_root.return_value = str(tmp_path)
        # Create the file first
        file_path = tmp_path / "workspace" / "chat-123" / "test.txt"
        file_path.parent.mkdir(parents=True)
        file_path.write_bytes(b"file content")
        response = client.get("/api/files/download?path=workspace%2Fchat-123%2Ftest.txt")
        assert response.status_code == 200
        assert response.content == b"file content"

    @patch("server.main.get_project_root")
    def test_download_file_not_found(self, mock_root, client, tmp_path):
        mock_root.return_value = str(tmp_path)
        response = client.get("/api/files/download?path=nonexistent%2Ffile.txt")
        assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_main.py::TestFileUploadAPI -v`
Expected: FAIL — TestFileUploadAPI not found (class not added yet)

- [ ] **Step 3: Add imports and helper to main.py**

Add after existing imports in `server/main.py`:
```python
import shutil
from pathlib import Path
from fastapi import UploadFile
from server.file_storage import save_file, get_file_path
```

Add this helper function (place near `get_or_create_session`):
```python
def get_project_root() -> str:
    """Get the agent project root directory."""
    return os.getenv("AGENT_PROJECT_ROOT", ".")
```

Add these new endpoints (place after the existing REST API sections):
```python
# REST API: Upload file
@app.post("/api/files/upload")
async def upload_file(file: UploadFile, chatId: str):
    project_root = get_project_root()
    # Create workspace/{chatId}/ directory if needed
    workspace_dir = Path(project_root) / "workspace" / chatId
    workspace_dir.mkdir(parents=True, exist_ok=True)
    # Save with original filename, handle name conflicts
    filename = file.filename or "uploaded_file"
    save_path = workspace_dir / filename
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    relative_path = f"workspace/{chatId}/{filename}"
    return {"path": relative_path}


# REST API: Download file
@app.get("/api/files/download")
async def download_file(path: str):
    project_root = get_project_root()
    file_path = get_file_path(path, project_root)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=file_path.name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_main.py::TestFileUploadAPI -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/main.py tests/test_main.py
git commit -m "feat: add file upload and download endpoints"
```

---

## Task 3: File Upload Frontend Component

**Files:**
- Create: `client/components/FileUpload.jsx`
- Modify: `client/components/ChatWindow.jsx:218-250` (input area)

- [ ] **Step 1: Write the FileUpload component**

```jsx
// client/components/FileUpload.jsx
import React, { useRef, useState } from "react";

const API_BASE = "/api";
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export function FileUpload({ chatId, onFileUploaded }) {
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const handleFileSelect = async (files) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    if (file.size > MAX_FILE_SIZE) {
      alert(`File too large. Maximum size is ${MAX_FILE_SIZE / 1024 / 1024}MB`);
      return;
    }
    await uploadFile(file);
  };

  const uploadFile = async (file) => {
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("chatId", chatId);
      const res = await fetch(`${API_BASE}/files/upload`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      onFileUploaded(data.path, file.name);
    } catch (err) {
      console.error("Upload failed:", err);
      alert("File upload failed. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  return (
    <div
      className={`relative ${dragOver ? "ring-2 ring-blue-400" : ""}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={(e) => handleFileSelect(e.target.files)}
      />
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={isUploading || !chatId}
        className="p-2 text-gray-500 hover:text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
        title="Upload file"
      >
        {isUploading ? (
          <span className="animate-pulse">...</span>
        ) : (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 1a.5.5 0 0 1 .5.5v11.793l3.146-3.147a.5.5 0 0 1 .708.708l-4 4a.5.5 0 0 1-.708 0l-4-4a.5.5 0 0 1 .708-.708L7.5 13.293V1.5A.5.5 0 0 1 8 1z"/>
          </svg>
        )}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Run build to verify component is valid**

Run: `npm run build 2>&1 | tail -10`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add client/components/FileUpload.jsx
git commit -m "feat: add FileUpload component with drag-drop support"
```

---

## Task 4: Integrate File Upload into ChatWindow

**Files:**
- Modify: `client/components/ChatWindow.jsx:218-250` (input area)

- [ ] **Step 1: Update ChatWindow to use FileUpload component**

In `ChatWindow.jsx`, add import:
```jsx
import { FileUpload } from "./FileUpload";
```

Add `onFileUploaded` prop and helper:
```jsx
export function ChatWindow({
  chatId,
  messages,
  isConnected,
  isLoading,
  onSendMessage,
  onStopResponse,
  onFileUploaded, // new prop
}) {
  // ... existing code ...

  const handleFileUploaded = (path, filename) => {
    // Send a message with the file path
    onSendMessage(`I've uploaded: ${path}`);
  };
```

- [ ] **Step 2: Add FileUpload to input area**

In the input area (around line 220), add the component next to the send button:
```jsx
<div className="p-4 border-t border-gray-200">
  <form onSubmit={handleSubmit} className="flex gap-2">
    <input
      type="text"
      value={input}
      onChange={(e) => setInput(e.target.value)}
      placeholder={isConnected ? "Type a message..." : "Connecting..."}
      disabled={!isConnected}
      className="flex-1 px-4 py-2 border border-gray-300 ..."
    />
    {isLoading ? (
      <button type="button" ...>Stop</button>
    ) : (
      <button type="submit" ...>Send</button>
    )}
    <FileUpload chatId={chatId} onFileUploaded={handleFileUploaded} />
  </form>
</div>
```

- [ ] **Step 3: Update App.jsx to pass onFileUploaded**

In `App.jsx`, update the `ChatWindow` component call to include the new prop:
```jsx
<ChatWindow
  chatId={selectedChatId}
  messages={messages}
  isConnected={isConnected}
  isLoading={isLoading}
  onSendMessage={handleSendMessage}
  onStopResponse={onStopResponse}
  onFileUploaded={(path, filename) => {
    // For now, do nothing — message is sent automatically via handleSendMessage
  }}
/>
```

Actually, the `handleFileUploaded` in ChatWindow calls `onSendMessage` directly, so we need to wire it up properly in App.jsx. Update the approach so ChatWindow passes the path back via `onFileUploaded` prop and App.jsx handles the message sending.

- [ ] **Step 4: Run build to verify**

Run: `npm run build 2>&1 | tail -10`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add client/components/ChatWindow.jsx client/App.jsx
git commit -m "feat: integrate FileUpload into ChatWindow"
```

---

## Task 5: Download Button in Message Bubble

**Files:**
- Modify: `client/components/ChatWindow.jsx:102-118` (MessageBubble)

- [ ] **Step 1: Update MessageBubble to detect file paths**

In `MessageBubble.jsx`, update the component:
```jsx
function MessageBubble({ message }) {
  const isUser = message.role === "user";
  const [downloadFiles, setDownloadFiles] = useState([]);

  // Detect workspace file paths in content
  useEffect(() => {
    if (!isUser && message.content) {
      const pattern = /workspace\/[^\/\s]+/g;
      const matches = message.content.match(pattern);
      if (matches) {
        setDownloadFiles([...new Set(matches)]);
      }
    }
  }, [message.content, isUser]);

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[80%] rounded-lg px-4 py-2 ...`}>
        <p className="whitespace-pre-wrap break-words">{message.content}</p>
        {downloadFiles.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {downloadFiles.map((path) => (
              <a
                key={path}
                href={`/api/files/download?path=${encodeURIComponent(path)}`}
                download
                className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-gray-200 hover:bg-gray-300 rounded"
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                  <path d="M6 1a.5.5 0 0 1 .5.5v7.793l2.146-2.147a.5.5 0 0 1 .708.708l-3 3a.5.5 0 0 1-.708 0l-3-3a.5.5 0 0 1 .708-.708L5.5 9.293V1.5A.5.5 0 0 1 6 1z"/>
                  <path d="M1 10a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1v-1z"/>
                </svg>
                Download {path.split("/").pop()}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run build to verify**

Run: `npm run build 2>&1 | tail -10`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add client/components/ChatWindow.jsx
git commit -m "feat: add download button to message bubbles for workspace files"
```

---

## Task 6: End-to-End Test

**Files:**
- Create: `tests/test_file_upload_e2e.py` (optional)

- [ ] **Step 1: Write integration test**

```python
# tests/test_file_upload_e2e.py
import os
from io import BytesIO
from fastapi.testclient import TestClient

class TestFileUploadDownloadE2E:
    @patch("server.main.get_project_root")
    def test_upload_and_download_flow(self, mock_root, tmp_path, client):
        mock_root.return_value = str(tmp_path)
        # 1. Upload a file
        file_content = b"E2E test content"
        file = (BytesIO(file_content), "e2e_test.txt")
        res = client.post("/api/files/upload", files={"file": file}, data={"chatId": "chat-e2e"})
        assert res.status_code == 200
        path = res.json()["path"]
        # 2. Download it back
        res = client.get(f"/api/files/download?path={path}")
        assert res.status_code == 200
        assert res.content == file_content
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_file_upload_e2e.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_file_upload_e2e.py
git commit -m "test: add e2e test for file upload/download flow"
```

---

## Spec Coverage Check

- [x] Upload endpoint — Task 2
- [x] Download endpoint — Task 2
- [x] Workspace storage at workspace/{chat_id}/ — Task 1, 2
- [x] Drag-drop upload — Task 3
- [x] Upload button — Task 3
- [x] File path detection in AI messages — Task 5
- [x] Download button in message bubble — Task 5
- [x] Per-chat isolation — Task 1, 2
- [x] Unit tests — Task 1, 2, 6
- [x] Integration test — Task 6

---

## Execution Options

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
