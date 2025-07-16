jest.setTimeout(20000);
const { _electron: electron } = require('playwright');

let app, page;

describe('Subtitles and Audio E2E', () => {
  beforeAll(async () => {
    // Patch WebSocket before app loads
    app = await electron.launch({
      args: ['.'],
      env: process.env,
    });
    page = await app.firstWindow();
    await page.addInitScript(() => {
      window._testWebSockets = [];
      class FakeWebSocket {
        constructor(url) {
          this.url = url;
          this.readyState = 1;
          setTimeout(() => {
            if (this.onopen) this.onopen();
          }, 10);
          window.ws = this;
          window._testWebSockets.push(this);
        }
        send() {}
        close() {}
        set onmessage(fn) {
          this._onmessage = fn;
        }
        get onmessage() {
          return this._onmessage;
        }
        addEventListener(type, handler) {
          if (type === 'message') this.onmessage = handler;
        }
        // Allow test to trigger message
        _triggerMessage(data) {
          if (this._onmessage) this._onmessage({ data });
        }
      }
      window.WebSocket = FakeWebSocket;
    });
  });
  afterAll(async () => { await app.close(); });
  it('should update subtitles and audio controls', async () => {
    await page.click('#recBtn');
    await page.waitForTimeout(1000);
    await page.click('#recBtn');
    // Wait for the app to set the onmessage handler
    await page.waitForTimeout(500);
    await page.evaluate(() => {
      console.log('Test: triggering message on all WebSockets');
      (window._testWebSockets || []).forEach(ws => {
        console.log('Test: ws.onmessage is', typeof ws._onmessage);
        ws._triggerMessage(JSON.stringify({ text: 'Hello world' }));
      });
    });
    await page.waitForSelector('.subtitles');
    const text = await page.textContent('.subtitles');
    console.log('Subtitles text:', text);
    await page.screenshot({ path: 'subtitles-fail.png' });
    expect(text).toContain('Hello world');
    // Audio controls should appear
    await page.waitForSelector('.audio-controls');
  });
}); 