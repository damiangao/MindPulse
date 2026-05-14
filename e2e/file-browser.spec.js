import { test, expect } from '@playwright/test';
import { writeFileSync, unlinkSync, mkdirSync } from 'fs';
import { join } from 'path';

// Helper to create a temp file
function createTempFile(name, content) {
  const path = join('/tmp', name);
  writeFileSync(path, content);
  return path;
}

test.describe('File Browser E2E', () => {

  test('should switch between chat and file tabs', async ({ page }) => {
    const email = `fb-tabs-${Date.now()}@example.com`;

    // Register and login
    await page.goto('/');
    const toggleBtn = page.locator('button:text-is("Register")').first();
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
    }
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').first().fill('testpass123');
    await page.locator('form button[type="submit"]').click();
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // Default should show chat tab
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible();

    // Click files tab
    await page.locator('button[title="Files"]').click();
    await expect(page.getByText('Files', { exact: true })).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Drop files here or click to upload')).toBeVisible();

    // Click chat tab
    await page.locator('button[title="Chats"]').click();
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible();
  });

  test('should upload file and see it in file tree', async ({ page }) => {
    const email = `fb-upload-${Date.now()}@example.com`;

    // Register and login
    await page.goto('/');
    const toggleBtn = page.locator('button:text-is("Register")').first();
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
    }
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').first().fill('testpass123');
    await page.locator('form button[type="submit"]').click();
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // Go to files tab
    await page.locator('button[title="Files"]').click();
    await expect(page.getByText('Files', { exact: true })).toBeVisible({ timeout: 5000 });

    // Click upload area to trigger file input
    const uploadArea = page.locator('text=Drop files here or click to upload');
    await uploadArea.click();

    // Create and upload a temp file
    const tempFilePath = createTempFile('test-upload.txt', 'Hello from e2e test');
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(tempFilePath);

    // Wait for upload to complete
    await page.waitForTimeout(1000);

    // Verify file appears in the tree (should show "test-upload.txt")
    await expect(page.getByText('test-upload.txt')).toBeVisible({ timeout: 5000 });

    // Clean up
    unlinkSync(tempFilePath);
  });

  test('should upload file, right-click, and add path to chat input', async ({ page }) => {
    const email = `fb-add-to-chat-${Date.now()}@example.com`;

    // Register and login
    await page.goto('/');
    const toggleBtn = page.locator('button:text-is("Register")').first();
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
    }
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').first().fill('testpass123');
    await page.locator('form button[type="submit"]').click();
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // Create a chat first so we have a chat selected
    await page.getByRole('button', { name: 'New Chat' }).click();
    const input = page.getByPlaceholder('Type a message...');

    // Go to files tab
    await page.locator('button[title="Files"]').click();
    await expect(page.getByText('Files', { exact: true })).toBeVisible({ timeout: 5000 });

    // Upload a file first
    const uploadArea = page.locator('text=Drop files here or click to upload');
    await uploadArea.click();
    const tempFilePath = createTempFile('test-right-click.txt', 'Content for right-click test');
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(tempFilePath);
    await page.waitForTimeout(1000);

    // Verify file appears
    await expect(page.getByText('test-right-click.txt')).toBeVisible({ timeout: 5000 });

    // Right-click on the file to open context menu
    const fileItem = page.locator('text=test-right-click.txt').first();
    await fileItem.click({ button: 'right' });

    // Context menu should appear with "Add to chat" option
    await expect(page.getByText('Add to chat')).toBeVisible({ timeout: 3000 });

    // Click "Add to chat"
    await page.getByRole('button', { name: 'Add to chat' }).click();

    // Should switch to chat tab
    await expect(page.locator('button[title="Chats"]')).toBeVisible({ timeout: 3000 });

    // Wait for React to update the input with the file path
    await page.waitForTimeout(500);

    // The input should contain a file path - use fresh locator after tab switch
    const inputAfterSwitch = page.getByPlaceholder('Type a message...');
    const inputValue = await inputAfterSwitch.inputValue();
    expect(inputValue.length > 0).toBeTruthy();
    expect(inputValue.includes('test-right-click') || inputValue.includes('/')).toBeTruthy();

    // Clean up
    unlinkSync(tempFilePath);
  });

  test('should upload file, right-click, and delete it', async ({ page }) => {
    const email = `fb-delete-${Date.now()}@example.com`;

    // Register and login
    await page.goto('/');
    const toggleBtn = page.locator('button:text-is("Register")').first();
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
    }
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').first().fill('testpass123');
    await page.locator('form button[type="submit"]').click();
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // Go to files tab
    await page.locator('button[title="Files"]').click();
    await expect(page.getByText('Files', { exact: true })).toBeVisible({ timeout: 5000 });

    // Upload a file
    const uploadArea = page.locator('text=Drop files here or click to upload');
    await uploadArea.click();
    const tempFilePath = createTempFile('test-delete.txt', 'File to delete');
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(tempFilePath);
    await page.waitForTimeout(1000);

    // Verify file appears
    await expect(page.getByText('test-delete.txt')).toBeVisible({ timeout: 5000 });

    // Right-click on the file
    const fileItem = page.locator('text=test-delete.txt').first();
    await fileItem.click({ button: 'right' });

    // Click Delete (with confirmation)
    page.on('dialog', dialog => dialog.accept());
    await page.getByRole('button', { name: 'Delete' }).click();

    // Wait for refresh
    await page.waitForTimeout(500);

    // File should be gone from the tree
    await expect(page.locator('text=test-delete.txt')).not.toBeVisible();

    // Clean up
    unlinkSync(tempFilePath);
  });

  test('should refresh file list and see uploaded file', async ({ page }) => {
    const email = `fb-refresh-${Date.now()}@example.com`;

    // Register and login
    await page.goto('/');
    const toggleBtn = page.locator('button:text-is("Register")').first();
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
    }
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').first().fill('testpass123');
    await page.locator('form button[type="submit"]').click();
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // Go to files tab
    await page.locator('button[title="Files"]').click();
    await expect(page.getByText('Files', { exact: true })).toBeVisible({ timeout: 5000 });

    // Upload a file
    const uploadArea = page.locator('text=Drop files here or click to upload');
    await uploadArea.click();
    const tempFilePath = createTempFile('test-refresh.txt', 'Refresh test content');
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(tempFilePath);
    await page.waitForTimeout(1000);

    // Verify file appears
    await expect(page.getByText('test-refresh.txt')).toBeVisible({ timeout: 5000 });

    // Click refresh button
    await page.locator('button[title="Refresh"]').click();
    await page.waitForTimeout(500);

    // File should still be there after refresh
    await expect(page.getByText('test-refresh.txt')).toBeVisible();

    // Clean up
    unlinkSync(tempFilePath);
  });

  test('should download file via context menu', async ({ page }) => {
    const email = `fb-download-${Date.now()}@example.com`;

    // Register and login
    await page.goto('/');
    const toggleBtn = page.locator('button:text-is("Register")').first();
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
    }
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').first().fill('testpass123');
    await page.locator('form button[type="submit"]').click();
    await expect(page.getByRole('button', { name: 'New Chat' })).toBeVisible({ timeout: 15000 });

    // Go to files tab
    await page.locator('button[title="Files"]').click();
    await expect(page.getByText('Files', { exact: true })).toBeVisible({ timeout: 5000 });

    // Upload a file
    const uploadArea = page.locator('text=Drop files here or click to upload');
    await uploadArea.click();
    const tempFilePath = createTempFile('test-download.txt', 'Download test content');
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(tempFilePath);
    await page.waitForTimeout(1000);

    // Verify file appears
    await expect(page.getByText('test-download.txt')).toBeVisible({ timeout: 5000 });

    // Set up download promise before right-click
    const downloadPromise = page.waitForEvent('download', { timeout: 10000 });

    // Right-click on the file
    const fileItem = page.locator('text=test-download.txt').first();
    await fileItem.click({ button: 'right' });

    // Click Download
    await page.getByRole('button', { name: 'Download' }).click();

    // Wait for download to start
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe('test-download.txt');

    // Clean up
    unlinkSync(tempFilePath);
  });
});