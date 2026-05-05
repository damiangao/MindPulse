import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';

// Mock WebSocket
let mockWsInstance = null;
const mockWsConstructor = vi.fn(() => {
  mockWsInstance = {
    readyState: WebSocket.OPEN,
    send: vi.fn(),
    close: vi.fn(),
    onopen: null,
    onmessage: null,
    onclose: null,
    onerror: null,
  };
  return mockWsInstance;
});
global.WebSocket = mockWsConstructor;

// Mock crypto.randomUUID
const mockRandomUUID = 'test-uuid-1234';
crypto.randomUUID = vi.fn(() => mockRandomUUID);

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockWsInstance = null;
    mockFetch.mockReset();
    // Default: successful auth then return empty chats
    mockFetch.mockImplementation((url) => {
      if (url.includes('/api/auth/me')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ id: '1', email: 'test@example.com' }),
        });
      }
      if (url.includes('/api/chats')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([]),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
    // Setup localStorage mock
    Object.defineProperty(global, 'localStorage', {
      value: {
        getItem: vi.fn().mockReturnValue('mock-token'),
        setItem: vi.fn(),
        removeItem: vi.fn(),
      },
      writable: true,
    });
  });

  it('createChat does not add to chats list', async () => {
    render(<App />);

    // Wait for ChatApp to render (auth passes and fetchChats completes)
    await waitFor(() => {
      expect(screen.queryByText('Login')).not.toBeInTheDocument();
      expect(screen.getByText('New Chat')).toBeInTheDocument();
    });

    // Count fetch calls before clicking New Chat
    const chatsFetchCountBefore = mockFetch.mock.calls.filter(([url]) => url.includes('/api/chats')).length;

    // Click New Chat
    const newChatBtn = screen.getByText('New Chat');
    fireEvent.click(newChatBtn);

    // Wait a bit for any async operations
    await new Promise((r) => setTimeout(r, 50));

    // Verify NO additional chats API calls were made
    // (createChat no longer calls /api/chats/init or adds to chats list)
    const chatsFetchCountAfter = mockFetch.mock.calls.filter(([url]) => url.includes('/api/chats')).length;
    expect(chatsFetchCountAfter).toBe(chatsFetchCountBefore);

    // Also verify that /api/chats/init was NEVER called
    const initCalls = mockFetch.mock.calls.filter(([url]) => url.includes('/api/chats/init'));
    expect(initCalls).toHaveLength(0);
  });

  it('createChat generates a temp UUID without calling any chat API', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.queryByText('Login')).not.toBeInTheDocument();
    });

    // Clear mock to track only the createChat call
    mockFetch.mockClear();
    crypto.randomUUID.mockClear();

    // Click New Chat
    const newChatBtn = screen.getByText('New Chat');
    fireEvent.click(newChatBtn);

    // Verify crypto.randomUUID was called (creates temp chat ID)
    expect(crypto.randomUUID).toHaveBeenCalled();

    // Verify NO fetch calls were made (no API call for temp chat)
    expect(mockFetch).not.toHaveBeenCalled();
  });
});
