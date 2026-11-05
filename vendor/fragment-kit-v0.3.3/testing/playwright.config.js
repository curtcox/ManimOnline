import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
const external = process.env.FRAGMENT_KIT_BASE_URL;
const browsers = (process.env.BROWSERS ?? 'chromium,firefox,webkit').split(',');
const projects = browsers.map(browserName => ({ name: browserName, use: { browserName } }));
if (process.env.MOBILE !== 'false') {
  if (browsers.includes('chromium')) projects.push({ name: 'Pixel 7', use: { ...devices['Pixel 7'] } });
  if (browsers.includes('webkit')) projects.push({ name: 'iPhone 14', use: { ...devices['iPhone 14'] } });
}
export default defineConfig({
  testDir: './contract', fullyParallel: true, workers: process.env.CI ? 2 : 3,
  timeout: 30000, expect: { timeout: 10000 }, retries: process.env.CI ? 1 : 0,
  outputDir: path.resolve('test-results'), reporter: [['list']], projects,
  use: { baseURL: external ?? 'http://127.0.0.1:8000/demo/', serviceWorkers: 'block', trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  ...(external ? {} : { webServer: { command: 'node tools/serve.mjs', cwd: path.resolve(new URL('../', import.meta.url).pathname), url: 'http://127.0.0.1:8000/demo/', reuseExistingServer: !process.env.CI } }),
});
