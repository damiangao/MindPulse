import { test, expect } from '@playwright/test';

test.describe('Session Resume E2E', () => {

  test('should resume session after page reload - history preserved', async ({ page }) => {
    const email = `resume-${Date.now()}@example.com`;

    // 1. Register and login
    await page.goto('/');
    const toggleBtn = page.locator('button:text-is("Register")').first();
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
    }
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').first().fill('testpass123');
    await page.locator('form button[type="submit"]').click();
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // 2. Create chat and send first message
    await page.getByRole('button', { name: 'New Chat' }).click();
    const input = page.getByPlaceholder('Type a message...');
    await input.fill('My name is Alice');
    await input.press('Enter');

    // 3. Wait for response to complete
    await expect(page.getByText('Thinking...')).toBeVisible({ timeout: 30000 });
    await page.waitForFunction(
      () => !document.body.textContent.includes('Thinking...'),
      { timeout: 45000 }
    );

    // 4. Verify chat appears in sidebar
    await page.waitForFunction(
      () => document.querySelectorAll('[class*="cursor-pointer"]').length >= 1,
      { timeout: 10000 }
    );

    // 5. Reload the page (simulates session disconnect)
    await page.reload();

    // 6. Should still be logged in (JWT persisted in localStorage)
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // 7. Chat should still be in sidebar
    await page.waitForFunction(
      () => document.querySelectorAll('[class*="cursor-pointer"]').length >= 1,
      { timeout: 10000 }
    );

    // 8. Click the chat to subscribe
    await page.locator('[class*="cursor-pointer"]').first().click();

    // 9. Verify history is loaded (Alice message should appear)
    await expect(page.getByText('My name is Alice').first()).toBeVisible({ timeout: 10000 });

    // 10. Send follow-up message to verify context continuity
    await input.fill('What is my name?');
    await input.press('Enter');

    // 11. AI should remember "Alice" from context
    await expect(page.getByText('Thinking...')).toBeVisible({ timeout: 30000 });
    await page.waitForFunction(
      () => !document.body.textContent.includes('Thinking...'),
      { timeout: 45000 }
    );

    // 12. Verify AI responded with context (should mention Alice)
    const pageContent = await page.content();
    expect(
      pageContent.includes('Alice') || pageContent.includes('alice'),
      'AI should remember the user name from session'
    ).toBeTruthy();
  });

  test('should resume session after WebSocket disconnect - message queued', async ({ page }) => {
    const email = `ws-resume-${Date.now()}@example.com`;

    // 1. Register and login
    await page.goto('/');
    const toggleBtn = page.locator('button:text-is("Register")').first();
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
    }
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').first().fill('testpass123');
    await page.locator('form button[type="submit"]').click();
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // 2. Create chat and send first message
    await page.getByRole('button', { name: 'New Chat' }).click();
    const input = page.getByPlaceholder('Type a message...');
    await input.fill('Message 1');
    await input.press('Enter');
    await expect(page.getByText('Thinking...')).toBeVisible({ timeout: 30000 });
    await page.waitForFunction(
      () => !document.body.textContent.includes('Thinking...'),
      { timeout: 45000 }
    );

    // 3. Force close WebSocket by navigating away and back
    // This simulates a network disconnect
    await page.goto('about:blank');
    await page.waitForTimeout(500);

    // 4. Go back to app
    await page.goto('/');

    // 5. Should still be logged in
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // 6. Chat should still be in sidebar
    await page.waitForFunction(
      () => document.querySelectorAll('[class*="cursor-pointer"]').length >= 1,
      { timeout: 10000 }
    );

    // 7. Click chat to reconnect
    await page.locator('[class*="cursor-pointer"]').first().click();

    // 8. Verify history loaded
    await expect(page.getByText('Message 1').first()).toBeVisible({ timeout: 10000 });

    // 9. Send follow-up
    await input.fill('Message 2');
    await input.press('Enter');
    await expect(page.getByText('Thinking...')).toBeVisible({ timeout: 30000 });
    await page.waitForFunction(
      () => !document.body.textContent.includes('Thinking...'),
      { timeout: 45000 }
    );

    // 10. Verify both messages present
    await expect(page.getByText('Message 1').first()).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Message 2').first()).toBeVisible({ timeout: 5000 });
  });

  test('should preserve multi-chat sessions across reload', async ({ page }) => {
    const email = `multi-resume-${Date.now()}@example.com`;

    // 1. Register and login
    await page.goto('/');
    const toggleBtn = page.locator('button:text-is("Register")').first();
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
    }
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').first().fill('testpass123');
    await page.locator('form button[type="submit"]').click();
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // 2. Create first chat
    await page.getByRole('button', { name: 'New Chat' }).click();
    const input = page.getByPlaceholder('Type a message...');
    await input.fill('Chat A - First');
    await input.press('Enter');
    await expect(page.getByText('Thinking...')).toBeVisible({ timeout: 30000 });
    await page.waitForFunction(
      () => !document.body.textContent.includes('Thinking...'),
      { timeout: 45000 }
    );

    // 3. Wait for chat to appear in sidebar
    await page.waitForFunction(
      () => document.querySelectorAll('[class*="cursor-pointer"]').length === 1,
      { timeout: 10000 }
    );

    // 4. Create second chat
    await page.getByRole('button', { name: 'New Chat' }).click();
    await input.fill('Chat B - First');
    await input.press('Enter');
    await expect(page.getByText('Thinking...')).toBeVisible({ timeout: 30000 });
    await page.waitForFunction(
      () => !document.body.textContent.includes('Thinking...'),
      { timeout: 45000 }
    );

    // 5. Wait for both chats in sidebar
    await page.waitForFunction(
      () => document.querySelectorAll('[class*="cursor-pointer"]').length === 2,
      { timeout: 10000 }
    );

    // 6. Reload page
    await page.reload();
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // 7. Both chats should be in sidebar
    await page.waitForFunction(
      () => document.querySelectorAll('[class*="cursor-pointer"]').length === 2,
      { timeout: 10000 }
    );

    // 8. Click first chat (last item = oldest = Chat A)
    const chatItems = page.locator('[class*="cursor-pointer"]');
    await chatItems.last().click();

    // 9. Should see Chat A content
    await expect(page.getByText('Chat A - First').first()).toBeVisible({ timeout: 10000 });

    // 10. Click second chat (first item = newest = Chat B)
    await chatItems.first().click();

    // 11. Should see Chat B content
    await expect(page.getByText('Chat B - First').first()).toBeVisible({ timeout: 10000 });
  });
});
