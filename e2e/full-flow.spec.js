import { test, expect } from '@playwright/test';

test.describe('Full User Flow E2E', () => {
  test('complete user flow: register -> create chat -> send message -> upload file -> switch chats', async ({ page }) => {
    const email = `e2e-${Date.now()}@example.com`;
    const password = 'testpass123';

    // 1. Register
    await page.goto('/');
    // Switch to register mode if showing login
    const toggleBtn = page.locator('button:text-is("Register")').first();
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
    }
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').first().fill(password);
    // Submit using the form button (Register mode)
    await page.locator('form button[type="submit"]').click();

    // Wait for main app (New Chat button visible)
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // 2. Create new chat (temp chat, NOT in sidebar yet)
    await page.getByRole('button', { name: 'New Chat' }).click();

    // Input should be visible
    const input = page.getByPlaceholder('Type a message...');
    await expect(input).toBeVisible();

    // 3. Chat should NOT be in sidebar yet (temp chat only)
    const sidebarChatsBefore = await page.locator('[class*="cursor-pointer"]').count();
    expect(sidebarChatsBefore).toBe(0); // No chats in sidebar

    // 4. Send "你好"
    await input.fill('你好');
    await input.press('Enter');

    // 5. Wait for response
    await expect(page.getByText('Thinking...')).toBeVisible({ timeout: 30000 });
    await expect(page.getByText('你好').first()).toBeVisible({ timeout: 30000 });

    // 6. Now chat SHOULD appear in sidebar (after backend auto-creates on first message)
    // Wait for fetchChats() to complete and React to re-render
    await page.waitForFunction(
      () => document.querySelectorAll('[class*="cursor-pointer"]').length === 1,
      { timeout: 10000 }
    );
    const sidebarChatsAfter = await page.locator('[class*="cursor-pointer"]').count();
    expect(sidebarChatsAfter).toBe(1);

    // 7. File upload - click upload button
    const uploadBtn = page.locator('button[title="Upload file"]');
    await uploadBtn.click();

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test-e2e.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('Hello from E2E test'),
    });

    // Wait for file upload confirmation
    await expect(page.getByText(/test-e2e\.txt|File uploaded/i)).toBeVisible({ timeout: 10000 });

    // 8. Create another chat (temp chat, NOT in sidebar yet)
    await page.getByRole('button', { name: 'New Chat' }).click();

    // Chat should NOT be in sidebar yet
    const sidebarChatsBeforeSecond = await page.locator('[class*="cursor-pointer"]').count();
    expect(sidebarChatsBeforeSecond).toBe(1); // Still only the first chat

    // 9. Switch back to first chat (oldest chat = last item in newest-first list)
    const chatItems = page.locator('[class*="cursor-pointer"]');
    await chatItems.last().click();

    // Should see "你好" in history
    await expect(page.getByText('你好').first()).toBeVisible({ timeout: 5000 });

    // 8. Send follow-up
    const input2 = page.getByPlaceholder('Type a message...');
    await input2.fill('继续');
    await input2.press('Enter');

    await expect(page.getByText('Thinking...')).toBeVisible({ timeout: 30000 });
    await expect(page.getByText('● Connected')).toBeVisible({ timeout: 5000 });
  });

  test('auth flow: register -> login -> logout -> login again', async ({ page }) => {
    await page.goto('/');

    const email = `auth-${Date.now()}@example.com`;

    // Register
    // Switch to register mode if showing login
    const toggleBtn = page.locator('button:text-is("Register")').first();
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
    }
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').first().fill('testpass123');
    await page.locator('form button[type="submit"]').click();

    // Should show main app
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // Logout
    await page.getByRole('button', { name: /logout/i }).click();

    // Should show auth form
    await expect(page.locator('input[type="email"]')).toBeVisible({ timeout: 5000 });

    // Login with existing account
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').first().fill('testpass123');
    await page.locator('form button[type="submit"]').click();

    // Should be logged back in
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });
  });

  test('chat switching: create 2 chats, switch between them, verify history', async ({ page }) => {
    const email = `switch-${Date.now()}@example.com`;

    await page.goto('/');
    // Switch to register mode if showing login
    const toggleBtn = page.locator('button:text-is("Register")').first();
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
    }
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').first().fill('testpass123');
    await page.locator('form button[type="submit"]').click();
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // Create first chat (temp chat, NOT in sidebar yet)
    await page.getByRole('button', { name: 'New Chat' }).click();
    const input1 = page.getByPlaceholder('Type a message...');
    await input1.fill('Chat A message');
    await input1.press('Enter');
    await expect(page.getByText('Thinking...')).toBeVisible({ timeout: 30000 });
    await expect(page.getByText('Chat A message').first()).toBeVisible({ timeout: 30000 });

    // After first message, Chat A should appear in sidebar (wait for fetchChats)
    await page.waitForFunction(
      () => document.querySelectorAll('[class*="cursor-pointer"]').length === 1,
      { timeout: 10000 }
    );
    const chatCountAfterA = await page.locator('[class*="cursor-pointer"]').count();
    expect(chatCountAfterA).toBe(1);

    // Create second chat (temp chat, NOT in sidebar yet)
    await page.getByRole('button', { name: 'New Chat' }).click();
    const input2 = page.getByPlaceholder('Type a message...');
    await input2.fill('Chat B message');
    await input2.press('Enter');
    await expect(page.getByText('Thinking...')).toBeVisible({ timeout: 30000 });
    await expect(page.getByText('Chat B message').first()).toBeVisible({ timeout: 30000 });

    // After second message, both chats should be in sidebar (wait for fetchChats)
    await page.waitForFunction(
      () => document.querySelectorAll('[class*="cursor-pointer"]').length === 2,
      { timeout: 10000 }
    );
    const chatCountAfterB = await page.locator('[class*="cursor-pointer"]').count();
    expect(chatCountAfterB).toBe(2);

    // Switch to Chat A (oldest chat = last item in newest-first list)
    const chatItems = page.locator('[class*="cursor-pointer"]');
    await chatItems.last().click();

    // Should see Chat A message in history
    await expect(page.getByText('Chat A message').first()).toBeVisible({ timeout: 5000 });
  });

  test('multi-round message ordering: verify messages appear in correct order after multiple rounds', async ({ page }) => {
    const email = `multi-${Date.now()}@example.com`;

    await page.goto('/');
    // Switch to register mode if showing login
    const toggleBtn = page.locator('button:text-is("Register")').first();
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
    }
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').first().fill('testpass123');
    await page.locator('form button[type="submit"]').click();
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // Round 1: Create chat and send first message
    await page.getByRole('button', { name: 'New Chat' }).click();
    const input1 = page.getByPlaceholder('Type a message...');
    await input1.fill('First round message');
    await input1.press('Enter');
    await expect(page.getByText('First round message').first()).toBeVisible({ timeout: 30000 });
    await expect(page.getByText('Thinking...')).toBeVisible({ timeout: 30000 });

    // Wait for response to complete
    await page.waitForFunction(
      () => !document.body.textContent.includes('Thinking...') || document.querySelector('[class*="cursor-pointer"]'),
      { timeout: 30000 }
    );

    // Round 2: Send follow-up message
    await input1.fill('Second round message');
    await input1.press('Enter');
    await expect(page.getByText('Second round message').first()).toBeVisible({ timeout: 30000 });
    await expect(page.getByText('Thinking...')).toBeVisible({ timeout: 30000 });

    // Wait for response to complete
    await page.waitForFunction(
      () => !document.body.textContent.includes('Thinking...') || document.querySelector('[class*="cursor-pointer"]'),
      { timeout: 30000 }
    );

    // Verify both messages appear in correct order in the DOM
    const pageText = await page.content();
    const firstMessageIdx = pageText.indexOf('First round message');
    const secondMessageIdx = pageText.indexOf('Second round message');
    expect(firstMessageIdx).toBeLessThan(secondMessageIdx);
    expect(firstMessageIdx).not.toBe(-1);
    expect(secondMessageIdx).not.toBe(-1);

    // Verify sidebar shows the chat
    await page.waitForFunction(
      () => document.querySelectorAll('[class*="cursor-pointer"]').length >= 1,
      { timeout: 10000 }
    );
    const chatCount = await page.locator('[class*="cursor-pointer"]').count();
    expect(chatCount).toBe(1);

    // Verify chat title in sidebar (should be auto-generated from first message)
    const chatTitle = await page.locator('[class*="cursor-pointer"]').first().textContent();
    expect(chatTitle).toContain('First round');
  });
});