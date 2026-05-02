import { useState, useEffect, useCallback, useRef } from "react";
import { ChatList } from "./components/ChatList";
import { ChatWindow } from "./components/ChatWindow";

const API_BASE = "/api";
const WS_URL = `ws://${window.location.host}/ws`;

export default function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [chats, setChats] = useState([]);
  const [selectedChatId, setSelectedChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [draftChat, setDraftChat] = useState(null);
  const [loginError, setLoginError] = useState("");

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const fetchedRef = useRef(false);
  const selectedChatIdRef = useRef(null);
  const loadingRef = useRef(false);

  // Check for existing token on mount
  useEffect(() => {
    const savedToken = localStorage.getItem("auth_token");
    if (savedToken) {
      validateToken(savedToken);
    } else {
      setAuthLoading(false);
    }
  }, []);

  const validateToken = async (t) => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      if (res.ok) {
        const userData = await res.json();
        setToken(t);
        setUser(userData);
        localStorage.setItem("auth_token", t);
      } else {
        localStorage.removeItem("auth_token");
      }
    } catch (e) {
      localStorage.removeItem("auth_token");
    }
    setAuthLoading(false);
  };

  const login = async (email, password) => {
    setLoginError("");
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (res.ok) {
        setToken(data.token);
        setUser(data.user);
        localStorage.setItem("auth_token", data.token);
      } else {
        setLoginError(data.detail || "Login failed");
      }
    } catch (e) {
      setLoginError("Network error");
    }
  };

  const register = async (email, password) => {
    setLoginError("");
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (res.ok) {
        setToken(data.token);
        setUser(data.user);
        localStorage.setItem("auth_token", data.token);
      } else {
        setLoginError(data.detail || "Registration failed");
      }
    } catch (e) {
      setLoginError("Network error");
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("auth_token");
    if (wsRef.current) {
      wsRef.current.close();
    }
  };

  const fetchChats = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/chats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setChats(data);
    } catch (error) {
      console.error("Failed to fetch chats:", error);
    }
  }, [token]);

  // Fetch chats when logged in
  useEffect(() => {
    if (user && token && !fetchedRef.current) {
      fetchedRef.current = true;
      fetchChats();
    }
  }, [user, token, fetchChats]);

  // Auth check passed - render main app
  if (!authLoading && user) {
    return <ChatApp user={user} token={token} logout={logout} chats={chats} setChats={setChats} fetchChats={fetchChats} />;
  }

  // Loading
  if (authLoading) {
    return <div className="flex h-screen items-center justify-center">Loading...</div>;
  }

  // Not logged in - show auth form
  return <AuthForm onLogin={login} onRegister={register} error={loginError} />;
}

function AuthForm({ onLogin, onRegister, error }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isLogin) {
      onLogin(email, password);
    } else {
      onRegister(email, password);
    }
  };

  return (
    <div className="flex h-screen items-center justify-center bg-gray-100">
      <div className="w-80 rounded bg-white p-6 shadow">
        <h1 className="mb-4 text-2xl font-bold">{isLogin ? "Login" : "Register"}</h1>
        {error && <p className="mb-4 text-red-500">{error}</p>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded border p-2"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded border p-2"
              required
              minLength={6}
            />
          </div>
          <button type="submit" className="w-full rounded bg-blue-500 p-2 text-white">
            {isLogin ? "Login" : "Register"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm">
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <button
            type="button"
            onClick={() => {
              setIsLogin(!isLogin);
              setEmail("");
              setPassword("");
            }}
            className="text-blue-500"
          >
            {isLogin ? "Register" : "Login"}
          </button>
        </p>
      </div>
    </div>
  );
}

function ChatApp({ user, token, logout, chats, setChats, fetchChats }) {
  const [selectedChatId, setSelectedChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [draftChat, setDraftChat] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const fetchedRef = useRef(false);
  const selectedChatIdRef = useRef(null);
  const loadingRef = useRef(false);

  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket connected");
      setIsConnected(true);
      const currentChatId = selectedChatIdRef.current;
      if (currentChatId) {
        ws.send(JSON.stringify({
          type: "subscribe",
          chatId: currentChatId,
          authorization: `Bearer ${token}`,
        }));
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
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }, [token]);

  const handleWSMessage = useCallback((message) => {
    const msgChatId = message.chatId || message.chat_id;
    if (msgChatId && msgChatId !== selectedChatIdRef.current) {
      return;
    }

    switch (message.type) {
      case "connected":
        break;

      case "history":
        setMessages(message.messages || []);
        break;

      case "user_message":
        break;

      case "assistant_message":
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
          const revIdx = prev.slice().reverse().findIndex((m) => m.role === "assistant" && m.isStreaming);
          if (revIdx >= 0) {
            const idx = prev.length - 1 - revIdx;
            const next = [...prev];
            next[idx] = { ...next[idx], content: next[idx].content + message.delta };
            return next;
          }
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
        break;

      case "thinking_delta":
        setMessages((prev) => {
          const revIdx = prev.slice().reverse().findIndex((m) => m.role === "assistant" && m.isStreaming);
          if (revIdx >= 0) {
            const idx = prev.length - 1 - revIdx;
            const next = [...prev];
            next[idx] = { ...next[idx], thinking: (next[idx].thinking || "") + message.delta };
            return next;
          }
          return [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: "",
              thinking: message.delta,
              isStreaming: true,
              timestamp: new Date().toISOString(),
            },
          ];
        });
        break;

      case "tool_use":
        setMessages((prev) => {
          const assistantIdx = prev.findLastIndex((m) => m.role === "assistant" && m.isStreaming);
          const insertIdx = assistantIdx >= 0 ? assistantIdx + 1 : prev.length;
          const next = [...prev];
          next.splice(insertIdx, 0, {
            id: crypto.randomUUID(),
            role: "tool_use",
            content: "",
            timestamp: new Date().toISOString(),
            toolName: message.tool_name,
            toolInput: message.tool_input,
          });
          return next;
        });
        break;

      case "interrupted":
        setMessages((prev) => {
          const revIdx = prev.slice().reverse().findIndex((m) => m.role === "assistant" && m.isStreaming);
          if (revIdx >= 0) {
            const idx = prev.length - 1 - revIdx;
            const next = [...prev];
            next[idx] = { ...next[idx], isStreaming: false, thinking: "" };
            return next;
          }
          return prev;
        });
        loadingRef.current = false;
        setIsLoading(false);
        break;

      case "result":
        setMessages((prev) => {
          const revIdx = prev.slice().reverse().findIndex((m) => m.role === "assistant" && m.isStreaming);
          if (revIdx >= 0) {
            const idx = prev.length - 1 - revIdx;
            const next = [...prev];
            next[idx] = { ...next[idx], isStreaming: false };
            return next;
          }
          return prev;
        });
        loadingRef.current = false;
        setIsLoading(false);
        fetchChats();
        break;

      case "error":
        console.error("Server error:", message.error);
        loadingRef.current = false;
        setIsLoading(false);
        break;
    }
  }, [fetchChats]);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connectWebSocket]);

  // Re-subscribe when chat changes
  useEffect(() => {
    selectedChatIdRef.current = selectedChatId;
    if (selectedChatId && wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "subscribe",
        chatId: selectedChatId,
        authorization: `Bearer ${token}`,
      }));
    }
  }, [selectedChatId, token]);

  const createChat = () => {
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
    loadingRef.current = false;
    setIsLoading(false);
  };

  const initDraftChat = async (chatId) => {
    if (!chatId) return chatId;
    try {
      const res = await fetch(`${API_BASE}/chats/init`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ tempId: chatId }),
      });
      const data = await res.json();
      if (data.id) {
        const draftTitle = draftChat?.title || "New Chat";
        const formalChat = {
          id: data.id,
          title: draftTitle,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        setChats((prev) => [formalChat, ...prev]);
        setDraftChat(null);
        selectedChatIdRef.current = data.id;
        setSelectedChatId((current) => (current === chatId ? data.id : current));
        return data.id;
      }
    } catch (error) {
      console.error("Failed to init chat:", error);
    }
    return chatId;
  };

  const deleteChat = async (chatId) => {
    try {
      await fetch(`${API_BASE}/chats/${chatId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      setChats((prev) => prev.filter((c) => c.id !== chatId));
      if (selectedChatId === chatId) {
        setSelectedChatId(null);
        setMessages([]);
      }
    } catch (error) {
      console.error("Failed to delete chat:", error);
    }
  };

  const selectChat = (chatId) => {
    setDraftChat(null);
    selectedChatIdRef.current = chatId;
    setSelectedChatId(chatId);
    setMessages([]);
    loadingRef.current = false;
    setIsLoading(false);
  };

  const isDraftChat = (chatId) => !chats.some((c) => c.id === chatId);

  const handleSendMessage = async (content) => {
    if (!selectedChatId || !isConnected) return;

    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      },
    ]);

    if (!loadingRef.current) {
      loadingRef.current = true;
      setIsLoading(true);
    }

    let chatId = selectedChatId;
    if (isDraftChat(selectedChatId)) {
      chatId = await initDraftChat(selectedChatId);
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "chat",
        content,
        chatId,
      }));
    }
  };

  const sidebarSelectedId = draftChat ? null : selectedChatId;

  return (
    <div className="flex h-screen">
      <div className="w-64 shrink-0">
        <div className="flex items-center justify-between p-4 border-b">
          <span className="font-medium truncate">{user.email}</span>
          <button onClick={logout} className="text-sm text-gray-500 hover:text-gray-700">Logout</button>
        </div>
        <ChatList
          chats={chats}
          selectedChatId={sidebarSelectedId}
          onSelectChat={selectChat}
          onNewChat={createChat}
          onDeleteChat={deleteChat}
        />
      </div>
      <ChatWindow
        chatId={selectedChatId}
        messages={messages}
        isConnected={isConnected}
        isLoading={isLoading}
        onSendMessage={handleSendMessage}
        onStopResponse={() => {
          if (wsRef.current?.readyState === WebSocket.OPEN && selectedChatId) {
            wsRef.current.send(JSON.stringify({ type: "stop", chatId: selectedChatId }));
          }
        }}
      />
    </div>
  );
}