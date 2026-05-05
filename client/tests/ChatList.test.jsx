import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatList } from '../components/ChatList';

describe('ChatList', () => {
  it('renders empty state when no chats', () => {
    render(
      <ChatList
        chats={[]}
        selectedChatId={null}
        onSelectChat={() => {}}
        onNewChat={() => {}}
        onDeleteChat={() => {}}
      />
    );
    expect(screen.getByText('No chats yet')).toBeInTheDocument();
    expect(screen.getByText('Click "New Chat" to start')).toBeInTheDocument();
  });

  it('renders chat items', () => {
    const chats = [
      { id: '1', title: 'Chat A' },
      { id: '2', title: 'Chat B' },
    ];
    render(
      <ChatList
        chats={chats}
        selectedChatId="1"
        onSelectChat={() => {}}
        onNewChat={() => {}}
        onDeleteChat={() => {}}
      />
    );
    expect(screen.getByText('Chat A')).toBeInTheDocument();
    expect(screen.getByText('Chat B')).toBeInTheDocument();
  });

  it('calls onNewChat when New Chat button is clicked', () => {
    const handleNewChat = vi.fn();
    render(
      <ChatList
        chats={[]}
        selectedChatId={null}
        onSelectChat={() => {}}
        onNewChat={handleNewChat}
        onDeleteChat={() => {}}
      />
    );
    fireEvent.click(screen.getByText('New Chat'));
    expect(handleNewChat).toHaveBeenCalledOnce();
  });

  it('calls onSelectChat when chat item is clicked', () => {
    const handleSelect = vi.fn();
    const chats = [{ id: 'chat-1', title: 'Test Chat' }];
    render(
      <ChatList
        chats={chats}
        selectedChatId={null}
        onSelectChat={handleSelect}
        onNewChat={() => {}}
        onDeleteChat={() => {}}
      />
    );
    fireEvent.click(screen.getByText('Test Chat'));
    expect(handleSelect).toHaveBeenCalledWith('chat-1');
  });

  it('calls onDeleteChat when delete button is clicked', () => {
    const handleDelete = vi.fn();
    const chats = [{ id: 'chat-1', title: 'Test Chat' }];
    render(
      <ChatList
        chats={chats}
        selectedChatId={null}
        onSelectChat={() => {}}
        onNewChat={() => {}}
        onDeleteChat={handleDelete}
      />
    );
    // Delete button is visible on hover - we need to hover first
    const chatItem = screen.getByText('Test Chat').parentElement;
    fireEvent.mouseEnter(chatItem);
    const deleteBtn = chatItem.querySelector('button');
    fireEvent.click(deleteBtn);
    expect(handleDelete).toHaveBeenCalledWith('chat-1');
  });

  it('highlights selected chat', () => {
    const chats = [{ id: 'chat-1', title: 'Test Chat' }];
    const { container } = render(
      <ChatList
        chats={chats}
        selectedChatId="chat-1"
        onSelectChat={() => {}}
        onNewChat={() => {}}
        onDeleteChat={() => {}}
      />
    );
    // Check that the chat item has bg-gray-700 class (selected state)
    const chatItem = container.querySelector('[class*="bg-gray-700"]');
    expect(chatItem).toBeTruthy();
  });
});