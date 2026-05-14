import React, { useState, useRef, useEffect, useMemo, useCallback } from "react";

function ToolUseBlock({ message }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const getToolSummary = () => {
    const input = message.toolInput || {};
    switch (message.toolName) {
      case "Read":
        return input.file_path;
      case "Write":
      case "Edit":
        return input.file_path;
      case "Bash":
        return (
          input.command?.slice(0, 60) +
          (input.command?.length > 60 ? "..." : "")
        );
      case "Grep":
        return `"${input.pattern}" in ${input.path || "."}`;
      case "Glob":
        return input.pattern;
      case "WebSearch":
        return input.query;
      case "WebFetch":
        return input.url;
      default:
        return JSON.stringify(input).slice(0, 50);
    }
  };

  return (
    <div className="my-2 border border-gray-200 bg-gray-50 rounded">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-2 flex items-center justify-between text-left hover:bg-gray-100"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-gray-600 uppercase">
            {message.toolName}
          </span>
          <span className="text-xs text-gray-500 truncate max-w-md">
            {getToolSummary()}
          </span>
        </div>
        <span className="text-xs text-gray-400">
          {isExpanded ? "▼" : "▶"}
        </span>
      </button>
      {isExpanded && (
        <div className="p-2 border-t border-gray-200">
          <pre className="text-xs bg-white p-2 rounded overflow-x-auto">
            {JSON.stringify(message.toolInput, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

function ThinkingBlock({ thinking }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const { trimmedThinking, displayText } = useMemo(() => {
    const trimmed = thinking.trimEnd();
    const lines = trimmed.split("\n");
    const shouldCollapse = lines.length > 2 && !isExpanded;
    return {
      trimmedThinking: trimmed,
      displayText: shouldCollapse ? lines.slice(-2).join("\n") : trimmed,
    };
  }, [thinking, isExpanded]);

  if (!thinking) return null;

  return (
    <div className="max-w-[80%] ml-0">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1.5 text-gray-400 hover:text-gray-600 transition-colors"
      >
        <span className="text-[10px] font-medium uppercase tracking-wider">
          Thinking
        </span>
        <span className="text-[10px]">
          {isExpanded ? "▼" : "▶"}
        </span>
      </button>
      {isExpanded ? (
        <div className="mt-1 text-[11px] text-gray-500 whitespace-pre-wrap break-words font-mono leading-relaxed">
          {trimmedThinking}
        </div>
      ) : (
        <div className="mt-1 text-[11px] text-gray-400 whitespace-pre-wrap break-words font-mono leading-relaxed">
          {displayText}
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-100 text-gray-900"
        }`}
      >
        <p className="whitespace-pre-wrap break-words">{message.content.replace(/^\n+/, '')}</p>
      </div>
    </div>
  );
}

export function ChatWindow({
  chatId,
  messages,
  isConnected,
  isLoading,
  onSendMessage,
  onStopResponse,
  token,
  insertedPath,
  onInsertPathChange,
}) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const prevMessageCountRef = useRef(0);

  // Reset scroll tracking when switching chats
  useEffect(() => {
    prevMessageCountRef.current = messages.length;
  }, [chatId]);

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    const hasNewMessages = messages.length > prevMessageCountRef.current;
    if (!hasNewMessages) return;
    prevMessageCountRef.current = messages.length;

    const isNearBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight < 100;
    if (isNearBottom) {
      messagesEndRef.current?.scrollIntoView({ behavior: "auto" });
    }
  }, [messages.length]);

  const handleFileUploaded = useCallback((path, filename) => {
    onSendMessage(`File uploaded: ${path}`);
  }, [onSendMessage]);

  // Handle path insertion from file browser
  useEffect(() => {
    if (insertedPath) {
      setInput(insertedPath);
      onInsertPathChange(null);
    }
  }, [insertedPath, onInsertPathChange]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || !chatId || !isConnected) return;
    onSendMessage(input.trim());
    setInput("");
  };

  if (!chatId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center text-gray-500">
          <p className="text-lg">Welcome to Simple Chat</p>
          <p className="text-sm mt-2">
            Select a chat or create a new one to get started
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-white">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <h2 className="font-semibold text-gray-800">Chat</h2>
        <div className="flex items-center gap-2">
          {isConnected ? (
            <span className="text-xs text-green-600">● Connected</span>
          ) : (
            <span className="text-xs text-red-600">○ Disconnected</span>
          )}
        </div>
      </div>

      {/* Messages */}
      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-400 mt-8">
            <p>Start a conversation</p>
          </div>
        ) : (
          <>
            {messages.map((msg) =>
              msg.role === "tool_use" ? (
                <ToolUseBlock key={msg.id} message={msg} />
              ) : msg.role === "assistant" && !msg.content?.trim() && !msg.thinking?.trim() ? null : (
                <div key={msg.id} className="space-y-1">
                  {msg.role !== "user" && msg.thinking && (
                    <ThinkingBlock thinking={msg.thinking} />
                  )}
                  {msg.content?.trim() && <MessageBubble message={msg} />}
                </div>
              )
            )}
            {isLoading && (
              <div className="flex items-center gap-2 text-gray-500">
                <span className="animate-pulse">●</span>
                <span className="text-sm">Thinking...</span>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-200">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isConnected ? "Type a message..." : "Connecting..."}
            disabled={!isConnected}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
          />
          {isLoading ? (
            <button
              type="button"
              onClick={onStopResponse}
              title="Stop generating"
              className="px-3 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors flex items-center justify-center"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
                <rect x="1" y="1" width="12" height="12" rx="1.5" />
              </svg>
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim() || !isConnected}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Send
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
