import { useState, useEffect, useCallback, useRef } from "react";
import { ChatList } from "./components/ChatList";
import { ChatWindow } from "./components/ChatWindow";

const API_BASE = "/api";
const WS_URL = `ws://${window.location.host}/ws`;

export default function App() {
  const [chats, setChats] = useState([]);
  const [selectedChatId, setSelectedChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  // Draft chat: current unsaved chat, not shown in sidebar
  const [draftChat, setDraftChat] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const fetchedRef = useRef(false);
  const selectedChatIdRef = useRef(null);

  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket connected");
      setIsConnected(true);
      // Re-subscribe to current chat if any
      const currentChatId = selectedChatIdRef.current;
      if (currentChatId) {
        ws.send(JSON.stringify({ type: "subscribe", chatId: currentChatId }));
      }
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        handleWSMessage(message);
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
      }
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected");
      setIsConnected(false);
      wsRef.current = null;
      // Auto-reconnect
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }, []);

  const handleWSMessage = useCallback((message) => {
    // Only handle messages for the currently selected chat
    const msgChatId = message.chatId || message.chat_id;
    if (msgChatId && msgChatId !== selectedChatIdRef.current) {
      return;
    }

    switch (message.type) {
      case "connected":
        console.log("Connected to server");
        break;

      case "history":
        setMessages(message.messages || []);
        break;

      case "user_message":
        // User message already added locally
        break;

      case "assistant_message":
        // Legacy complete message (fallback)
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: message.content,
            timestamp: new Date().toISOString(),
          },
        ]);
        setIsLoading(false);
        break;

      case "assistant_delta":
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === "assistant" && last.isStreaming) {
            // Append to existing streaming message
            return [
              ...prev.slice(0, -1),
              {
                ...last,
                content: last.content + message.delta,
              },
            ];
          }
          // Create new streaming message
          return [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: message.delta,
              thinking: "",
              isStreaming: true,
              timestamp: new Date().toISOString(),
            },
          ];
        });
        setIsLoading(false);
        break;

      case "thinking_delta":
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === "assistant" && last.isStreaming) {
            return [
              ...prev.slice(0, -1),
              {
                ...last,
                thinking: (last.thinking || "") + message.delta,
              },
            ];
          }
          return prev;
        });
        break;

      case "tool_use":
        setMessages((prev) => [
          ...prev,
          {
            id: message.toolId,
            role: "tool_use",
            content: "",
            timestamp: new Date().toISOString(),
            toolName: message.tool_name,
            toolInput: message.tool_input,
          },
        ]);
        break;

      case "result":
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === "assistant" && last.isStreaming) {
            return [
              ...prev.slice(0, -1),
              { ...last, isStreaming: false },
            ];
          }
          return prev;
        });
        setIsLoading(false);
        // Refresh chat list to get updated titles
        fetchChats();
        break;

      case "error":
        console.error("Server error:", message.error);
        setIsLoading(false);
        break;
    }
  }, []);

  // Initialize WebSocket
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connectWebSocket]);

  // Fetch all chats
  const fetchChats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/chats`);
      const data = await res.json();
      setChats(data);
    } catch (error) {
      console.error("Failed to fetch chats:", error);
    }
  }, []);

  // Create new chat - instant, no backend call, not shown in sidebar
  const createChat = () => {
    // Discard current draft if exists
    setDraftChat(null);
    const tempId = crypto.randomUUID();
    const now = new Date().toISOString();
    setDraftChat({
      id: tempId,
      title: "New Chat",
      createdAt: now,
      updatedAt: now,
    });
    setSelectedChatId(tempId);
    setMessages([]);
    setIsLoading(false);
  };


  // Initialize draft chat with backend session
  const initDraftChat = async (chatId) => {
    if (!chatId) return chatId;
    try {
      const res = await fetch(`${API_BASE}/chats/init`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tempId: chatId }),
      });
      const data = await res.json();
      if (data.id) {
        // Move draft to formal chats
        const draftTitle = draftChat?.title || "New Chat";
        const formalChat = {
          id: data.id,
          title: draftTitle,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        setChats((prev) => [formalChat, ...prev]);
        setDraftChat(null);
        // Update selectedChatId so ChatWindow renders correctly
        setSelectedChatId((current) => {
          if (current === chatId) {
            selectedChatIdRef.current = data.id;
            return data.id;
          }
          return current;
        });
        return data.id;
      }
    } catch (error) {
      console.error("Failed to init chat:", error);
    }
    return chatId;
  };

  // Delete chat
  const deleteChat = async (chatId) => {
    try {
      await fetch(`${API_BASE}/chats/${chatId}`, { method: "DELETE" });
      setChats((prev) => prev.filter((c) => c.id !== chatId));
      if (selectedChatId === chatId) {
        setSelectedChatId(null);
        setMessages([]);
      }
    } catch (error) {
      console.error("Failed to delete chat:", error);
    }
  };

  // Keep ref in sync with selectedChatId
  useEffect(() => {
    selectedChatIdRef.current = selectedChatId;
    if (selectedChatId && wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "subscribe", chatId: selectedChatId }));
    }
  }, [selectedChatId]);

  // Select a chat - discard draft if switching away
  const selectChat = (chatId) => {
    setDraftChat(null);
    selectedChatIdRef.current = chatId;
    setSelectedChatId(chatId);
    setMessages([]);
    setIsLoading(false);
  };

  // Check if a chatId is a draft (not in formal chats list)
  const isDraftChat = (chatId) => {
    return !chats.some((c) => c.id === chatId);
  };

  // Send a message
  const handleSendMessage = async (content) => {
    if (!selectedChatId || !isConnected) return;

    // Add message optimistically
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      },
    ]);

    setIsLoading(true);

    // If in draft mode, initialize it first
    let chatId = selectedChatId;
    if (isDraftChat(selectedChatId)) {
      chatId = await initDraftChat(selectedChatId);
    }

    // Send via WebSocket
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "chat",
          content,
          chatId,
        })
      );
    }
  };

  // Initial fetch - only once
  useEffect(() => {
    if (!fetchedRef.current) {
      fetchedRef.current = true;
      fetchChats();
    }
  }, [fetchChats]);

  // Determine which chat ID to show as selected in sidebar
  // Draft chat is not in sidebar, so sidebar shows none selected when in draft
  const sidebarSelectedId = draftChat ? null : selectedChatId;

  return (
    <div className="flex h-screen">
      {/* Sidebar - only shows formal chats */}
      <div className="w-64 shrink-0">
        <ChatList
          chats={chats}
          selectedChatId={sidebarSelectedId}
          onSelectChat={selectChat}
          onNewChat={createChat}
          onDeleteChat={deleteChat}
        />
      </div>

      {/* Main chat area */}
      <ChatWindow
        chatId={selectedChatId}
        messages={messages}
        isConnected={isConnected}
        isLoading={isLoading}
        onSendMessage={handleSendMessage}
      />
    </div>
  );
}
