const { _electron: electron } = require('playwright');

let app, page;

describe('Subtitles and Audio E2E', () => {
  beforeAll(async () => {
    app = await electron.launch({ args: ['.'] });
    page = await app.firstWindow();
    // Mock /transcribe and /ws/generate
    await page.route('**/transcribe', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ transcript: 'Hello world.' })
    }));
    await page.route('**/ws/generate', route => {
      route.fulfill({
        status: 101,
        headers: { 'Upgrade': 'websocket' },
        body: ''
      });
    });
  });
  afterAll(async () => { await app.close(); });
  it('should update subtitles and audio controls', async () => {
    await page.click('#recBtn');
    // Simulate stop after 1s
    await page.waitForTimeout(1000);
    await page.click('#recBtn');
    await page.waitForSelector('.subtitles');
    const text = await page.textContent('.subtitles');
    expect(text).toContain('Hello world');
    // Audio controls should appear
    await page.waitForSelector('.audio-controls');
  });
}); 