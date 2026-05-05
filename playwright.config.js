import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 60000,
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'uv run python -m server.main',
      port: 3001,
      timeout: 15000,
      reuseExistingServer: true,
    },
    {
      command: 'npm run dev:client',
      port: 5173,
      timeout: 15000,
      reuseExistingServer: true,
    },
  ],
});