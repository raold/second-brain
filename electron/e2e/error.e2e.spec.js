const { _electron: electron } = require('playwright');

let app, page;

describe('Error Handling E2E', () => {
  beforeAll(async () => {
    app = await electron.launch({ args: ['.'] });
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