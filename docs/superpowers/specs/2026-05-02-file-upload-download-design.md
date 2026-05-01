# File Upload/Download Design

**Date:** 2026-05-02

## Overview

Enable file upload and download in the chat application. Files are stored in the agent's workspace, and AI reads them via its own Read tool.

## Upload Flow

1. User drags file onto input area OR clicks upload button to select file
2. Frontend POSTs file to `POST /api/files/upload` with `chatId` in form data
3. Backend saves file to `{AGENT_PROJECT_ROOT}/workspace/{chat_id}/{filename}`
4. Backend returns `{ path: "workspace/{chat_id}/{filename}" }`
5. User message is sent with the file path as text content (e.g., "Read this file: workspace/xxx/report.pdf")

## Download Flow

1. AI generates file and mentions its path in the response (e.g., "I've saved the report to workspace/xxx/report.pdf")
2. Frontend detects file path patterns in assistant message (`workspace/xxx/filename`)
3. Frontend renders a download button inside the message bubble
4. Click download → `GET /api/files/download?path={encoded_path}`
5. Backend reads file from `{AGENT_PROJECT_ROOT}/{path}` and streams as attachment

## Backend Changes

### New Endpoints

**`POST /api/files/upload`**
- Multipart form upload with `file` and `chatId` fields
- Saves to `workspace/{chat_id}/{filename}`
- Returns `{ path: "workspace/{chat_id}/{filename}" }`
- Creates `workspace/{chat_id}/` directory if not exists

**`GET /api/files/download`**
- Query param: `path` (URL-encoded)
- Reads file from `{AGENT_PROJECT_ROOT}/{path}`
- Returns file as streamed attachment with `Content-Disposition`
- 404 if file not found

### File Storage

- Location: `{AGENT_PROJECT_ROOT}/workspace/{chat_id}/`
- Per-chat isolation via subdirectory
- Files are persistent (not cleaned up on chat delete — workspace cleanup is out of scope)

## Frontend Changes

### Upload UI

- Input area accepts drag-and-drop
- Upload button next to send button
- Show upload progress
- File type/size validation before upload

### Download Detection

- Parse assistant message for `workspace/[^/\s]+` patterns
- Render download icon/button in message bubble
- Click triggers file download

### Message Bubble Updates

- After assistant message with detected file paths, inject download button(s)
- Multiple files = multiple download buttons

## Data Flow

```
User drops file
    → Frontend validates (size, type)
    → POST /api/files/upload (multipart)
    → Backend saves to workspace/
    → Returns path
    → User message sent with path
    → AI reads file via Read tool
    → AI responds with file path in message
    → Frontend detects pattern, shows download button
    → User clicks → GET /api/files/download
    → File streamed to user
```

## Key Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Storage location | `{AGENT_PROJECT_ROOT}/workspace/{chat_id}/` | AI already has access to this directory |
| File isolation | Per chat_id subdirectory | Prevents cross-chat file leakage |
| Download button placement | Inside assistant message bubble | Contextually appropriate |
| File size limit | Default 10MB | Reasonable for code/doc files |
| File type validation | None (AI handles any type) | Flexible, AI can reject unsupported |

## Out of Scope

- Automatic workspace cleanup
- File listing/management UI
- Drag-drop visual feedback (beyond standard browser behavior)
