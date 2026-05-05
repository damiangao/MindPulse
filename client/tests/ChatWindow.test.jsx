import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatWindow } from '../components/ChatWindow';

describe('ChatWindow', () => {
  const defaultProps = {
    chatId: 'test-chat-1',
    messages: [],
    isConnected: true,
    isLoading: false,
    onSendMessage: vi.fn(),
    onStopResponse: vi.fn(),
    token: 'test-token',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows empty state when no chatId', () => {
    render(<ChatWindow {...defaultProps} chatId={null} messages={[]} />);
    expect(screen.getByText('Welcome to Simple Chat')).toBeInTheDocument();
    expect(screen.getByText('Select a chat or create a new one to get started')).toBeInTheDocument();
  });

  it('shows input field when chatId is provided', () => {
    render(<ChatWindow {...defaultProps} />);
    const input = screen.getByPlaceholderText('Type a message...');
    expect(input).toBeInTheDocument();
    expect(input).not.toBeDisabled();
  });

  it('shows connecting placeholder when not connected', () => {
    render(<ChatWindow {...defaultProps} isConnected={false} />);
    const input = screen.getByPlaceholderText('Connecting...');
    expect(input).toBeInTheDocument();
    expect(input).toBeDisabled();
  });

  it('calls onSendMessage when form is submitted', () => {
    const handleSend = vi.fn();
    render(<ChatWindow {...defaultProps} onSendMessage={handleSend} />);
    const input = screen.getByPlaceholderText('Type a message...');
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.submit(input.closest('form'));
    expect(handleSend).toHaveBeenCalledWith('Hello');
    expect(input.value).toBe('');
  });

  it('does not submit empty message', () => {
    const handleSend = vi.fn();
    render(<ChatWindow {...defaultProps} onSendMessage={handleSend} />);
    const input = screen.getByPlaceholderText('Type a message...');
    const form = input.closest('form');
    fireEvent.submit(form);
    expect(handleSend).not.toHaveBeenCalled();
  });

  it('renders user message bubble', () => {
    const messages = [
      {
        id: '1',
        role: 'user',
        content: 'Hello assistant',
        timestamp: '2024-01-01T00:00:00Z',
      },
    ];
    render(<ChatWindow {...defaultProps} messages={messages} />);
    expect(screen.getByText('Hello assistant')).toBeInTheDocument();
  });

  it('renders assistant message bubble', () => {
    const messages = [
      {
        id: '2',
        role: 'assistant',
        content: 'Hello user!',
        timestamp: '2024-01-01T00:00:00Z',
      },
    ];
    render(<ChatWindow {...defaultProps} messages={messages} />);
    expect(screen.getByText('Hello user!')).toBeInTheDocument();
  });

  it('renders thinking block when message has thinking', () => {
    const messages = [
      {
        id: '3',
        role: 'assistant',
        content: '',
        thinking: 'Let me think about this...',
        isStreaming: true,
        timestamp: '2024-01-01T00:00:00Z',
      },
    ];
    render(<ChatWindow {...defaultProps} messages={messages} />);
    expect(screen.getByText('Let me think about this...')).toBeInTheDocument();
  });

  it('renders tool_use block', () => {
    const messages = [
      {
        id: '4',
        role: 'tool_use',
        toolName: 'Bash',
        toolInput: { command: 'ls -la' },
        timestamp: '2024-01-01T00:00:00Z',
      },
    ];
    render(<ChatWindow {...defaultProps} messages={messages} />);
    expect(screen.getByText('Bash')).toBeInTheDocument();
  });

  it('shows loading indicator when isLoading and messages exist', () => {
    const messages = [{ id: '1', role: 'assistant', content: 'test', timestamp: '2024-01-01T00:00:00Z' }];
    render(<ChatWindow {...defaultProps} isLoading={true} messages={messages} />);
    expect(screen.getByText('Thinking...')).toBeInTheDocument();
  });

  it('shows connected status when chat is active', () => {
    render(<ChatWindow {...defaultProps} isConnected={true} />);
    expect(screen.getByText('● Connected')).toBeInTheDocument();
  });

  it('shows disconnected status when not connected', () => {
    render(<ChatWindow {...defaultProps} isConnected={false} />);
    expect(screen.getByText('○ Disconnected')).toBeInTheDocument();
  });

  it('shows send button when not loading and has input', () => {
    render(<ChatWindow {...defaultProps} isLoading={false} />);
    const input = screen.getByPlaceholderText('Type a message...');
    fireEvent.change(input, { target: { value: 'test' } });
    const sendButton = screen.getByRole('button', { name: /send/i });
    expect(sendButton).not.toBeDisabled();
  });

  it('trims leading newlines from message content', () => {
    const messages = [
      {
        id: '5',
        role: 'assistant',
        content: '\n\nHello trimmed',
        timestamp: '2024-01-01T00:00:00Z',
      },
    ];
    render(<ChatWindow {...defaultProps} messages={messages} />);
    // The content should NOT start with newlines
    const bubble = screen.getByText('Hello trimmed');
    expect(bubble.textContent).toBe('Hello trimmed');
  });
});