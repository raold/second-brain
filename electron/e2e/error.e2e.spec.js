const { describeIfNotCI } = require('./skip-in-ci');
jest.setTimeout(20000);
const { _electron: electron } = require('playwright');

let app, page;

describeIfNotCI('Error Handling E2E', () => {
  beforeAll(async () => {
    app = await electron.launch({ 
      args: ['.', '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
      env: process.env,
    });
    page = await app.firstWindow();
    await page.route('**/transcribe', route => route.fulfill({ status: 500, body: 'fail' }));
  });
  afterAll(async () => { await app.close(); });
  it('should show error on transcription failure', async () => {
    await page.click('#recBtn');
    await page.waitForTimeout(1000);
    await page.click('#recBtn');
    await page.waitForSelector('.status');
    const status = await page.textContent('.status');
    expect(status).toContain('error');
  });
}); 