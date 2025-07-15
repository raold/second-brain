// playwright.config.js
const { _electron: electron } = require('playwright');

module.exports = {
  testDir: './e2e',
  timeout: 30000,
  use: {
    headless: true,
    launchOptions: {
      args: ['.']
    }
  },
  projects: [
    {
      name: 'electron',
      use: {
        ...electron,
      },
    },
  ],
}; 