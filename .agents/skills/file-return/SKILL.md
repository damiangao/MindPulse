# File Return Skill

**Purpose:** Guide the agent to return files in a format that the frontend can detect and offer for download.

## When to Use

When the agent creates a file that the user might want to download (code files, reports, generated content, etc.), it should inform the user using a specific format that the frontend can parse.

## How to Return File Information

When saving a file, include the path in your response using this format:

```
[FILE:workspace/{chat_id}/{filename}]
```

The frontend will detect this pattern and automatically display a download button for the file.

## Example

**Instead of:**
> I've saved the report to `/Users/damian/workspace/claude-chat/workspace/abc123/report.pdf`

**Use:**
> I've saved the report to [FILE:workspace/{chat_id}/report.pdf]

Replace `{chat_id}` with the current chat session ID (visible in the conversation context).

## Important Rules

1. **Always use `workspace/` prefix** - Files must be in the workspace directory for the frontend to serve them for download
2. **Include the `[FILE:...]` marker** - This is how the frontend detects downloadable files
3. **Use relative paths** - Never use absolute paths like `/Users/damian/...`
4. **The file path must be URL-safe** - Use only letters, numbers, hyphens, underscores, and slashes

## File Location

Files are stored in: `{AGENT_PROJECT_ROOT}/workspace/{chat_id}/`

The frontend download endpoint is: `GET /api/files/download?path={encoded_path}`

## Example Responses

**Generating a Python file:**
> Here's the Python script you requested:
> ```python
> # content here
> ```
> [FILE:workspace/{chat_id}/script.py]

**Creating a report:**
> The report has been generated and saved to [FILE:workspace/{chat_id}/report.pdf]

**Multiple files:**
> I've created two files for you:
> - [FILE:workspace/{chat_id}/data.csv]
> - [FILE:workspace/{chat_id}/summary.txt]