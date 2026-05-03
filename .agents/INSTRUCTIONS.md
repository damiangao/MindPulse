# Agent Instructions

## File Return Format

When creating files that users may want to download, use this format in your response:

```
[FILE:workspace/{session_id}/{filename}]
```

The frontend will detect this pattern and automatically show a download button.

**Example:** If you create a Python script in a chat with session ID "abc123", write:
> Here's the script you requested: [FILE:workspace/abc123/script.py]

**Important:**
- Always use `workspace/` prefix (not absolute paths like `/Users/damian/...`)
- Use the `[FILE:...]` marker so the frontend can detect it
- Include the session_id in the path

## File Storage Location

All user-uploaded and agent-created files are stored in:
`{AGENT_PROJECT_ROOT}/workspace/{session_id}/`

The frontend can serve files from this workspace directory for download.