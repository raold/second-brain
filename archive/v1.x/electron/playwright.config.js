// playwright.config.js
const { _electron: electron } = require('playwright');

module.exports = {
  testDir: './e2e',
  timeout: 30000,
  use: {
    headless: true,
    launchOptions: {
<<<<<<< HEAD
      args: ['.']
=======
      args: ['.', '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
      env: process.env,
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
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