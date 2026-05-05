import { test, expect } from '@playwright/test';

test.describe('Debug New Chat Select Effect', () => {
  test('check selectChat when clicking new chat button', async ({ page }) => {
    const email = `new-chat-${Date.now()}@example.com`;

    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('selectChat') || text.includes('DEBUG')) {
        console.log(`[${msg.type()}] ${text}`);
      }
    });

    await page.goto('/');
    const toggleBtn = page.locator('button:text-is("Register")').first();
    if (await toggleBtn.isVisible()) await toggleBtn.click();
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').first().fill('testpass123');
    await page.locator('form button[type="submit"]').click();
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // Create first chat with 你好
    await page.getByRole('button', { name: 'New Chat' }).click();
    await page.getByPlaceholder('Type a message...').fill('你好');
    await page.getByPlaceholder('Type a message...').press('Enter');
    await expect(page.getByText('Thinking...')).toBeVisible({ timeout: 30000 });
    await expect(page.getByText('● Connected')).toBeVisible({ timeout: 30000 });
    console.log('=== First chat done ===');

    let body = await page.locator('body').innerText();
    console.log('你好 visible:', body.includes('你好'));

    // File upload
    const uploadBtn = page.locator('button[title="Upload file"]');
    await uploadBtn.click();
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('Hello'),
    });
    await expect(page.getByText(/test\.txt|File uploaded/i)).toBeVisible({ timeout: 10000 });
    console.log('=== File uploaded ===');

    body = await page.locator('body').innerText();
    console.log('After upload - 你好 visible:', body.includes('你好'));

    // Click "New Chat" button
    console.log('=== Clicking New Chat button ===');
    await page.getByRole('button', { name: 'New Chat' }).click();
    await page.waitForTimeout(1000);

    body = await page.locator('body').innerText();
    console.log('After New Chat click - 你好 visible:', body.includes('你好'));

    // Now type in the new chat
    await page.getByPlaceholder('Type a message...').fill('Second');
    await page.getByPlaceholder('Type a message...').press('Enter');
    await expect(page.getByText('Thinking...')).toBeVisible({ timeout: 30000 });
    await expect(page.getByText('● Connected')).toBeVisible({ timeout: 30000 });
    console.log('=== Second chat done ===');

    // Switch to first chat
    const items = page.locator('[class*="cursor-pointer"]');
    console.log('Total chats:', await items.count());
    await items.last().click();
    await page.waitForTimeout(3000);

    body = await page.locator('body').innerText();
    console.log('After switch - 你好 visible:', body.includes('你好'));
    console.log('After switch - empty state:', body.includes('Start a conversation'));
  });
});