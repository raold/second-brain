<<<<<<< HEAD
=======
const { describeIfNotCI } = require('./skip-in-ci');
jest.setTimeout(20000);
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
const { _electron: electron } = require('playwright');

let app, page;

<<<<<<< HEAD
describe('Electron Voice LLM App', () => {
  beforeAll(async () => {
    app = await electron.launch({ args: ['.'] });
=======
describeIfNotCI('Electron Voice LLM App', () => {
  beforeAll(async () => {
    app = await electron.launch({ 
      args: ['.', '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
      env: process.env,
    });
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
    page = await app.firstWindow();
  });
  afterAll(async () => {
    await app.close();
  });
  it('should render main UI and toggle theme', async () => {
    await page.waitForSelector('h1');
    const title = await page.textContent('h1');
    expect(title).toContain('Voice LLM Electron Demo');
    await page.click('#themeToggle');
    await page.click('#themeToggle');
  });
  it('should open settings panel', async () => {
    await page.click('#settingsBtn');
    await page.waitForSelector('#settingsPanel', { state: 'visible' });
    await page.click('#closeSettings');
  });
}); 