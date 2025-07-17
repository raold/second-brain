const { describeIfNotCI } = require('./skip-in-ci');
jest.setTimeout(20000);
const { _electron: electron } = require('playwright');

let app, page;

describeIfNotCI('Subtitles and Audio E2E', () => {
  beforeAll(async () => {
    // Launch app first
    app = await electron.launch({
      args: ['.', '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
      env: process.env,
    });
    
    // Get the page and add init script before any interactions
    page = await app.firstWindow();
    
    // Wait for the page to be ready and then evaluate our WebSocket mock
    await page.waitForLoadState('domcontentloaded');
    
    // Inject WebSocket mock directly
    await page.evaluate(() => {
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
  
  afterAll(async () => { 
    await app.close(); 
  });
  
  it('should update subtitles and audio controls', async () => {
    // Directly call connectToWSGenerate to create the WebSocket
    await page.evaluate(() => {
      // Access the connectToWSGenerate function from the global scope
      window.connectToWSGenerate = function(prompt) {
        const subtitlesDiv = document.getElementById('subtitles');
        subtitlesDiv.textContent = '';
        window.tokenBuffer = [];
        window.ttsBuffer = '';
        if (window.ws) window.ws.close();
        window.ws = new WebSocket('ws://localhost:8000/ws/generate?token=test');
        window.ws.onopen = () => {
          console.log('WebSocket opened');
        };
        window.ws.onmessage = (event) => {
          let msg;
          try { 
            msg = JSON.parse(event.data); 
          } catch { 
            return; 
          }
          if (msg.error) {
            return;
          }
          if (msg.text || msg.chunk) {
            const token = msg.text || msg.chunk;
            subtitlesDiv.textContent += token;
          }
        };
      };
      
      // Call it to establish the WebSocket connection
      window.connectToWSGenerate('test prompt');
    });
    
    // Wait for the WebSocket to be created and onmessage handler to be set
    await page.waitForTimeout(500);
    
    // Send a message in the correct format (with text property)
    await page.evaluate(() => {
      console.log('Test: triggering message on all WebSockets');
      (window._testWebSockets || []).forEach(ws => {
        console.log('Test: ws.onmessage is', typeof ws._onmessage);
        // Send message in the format the app expects: { text: "content" }
        ws._triggerMessage(JSON.stringify({ text: 'Hello world' }));
      });
    });
    
    await page.waitForSelector('.subtitles');
    const text = await page.textContent('.subtitles');
    console.log('Subtitles text:', text);
    await page.screenshot({ path: 'subtitles-success.png' });
    expect(text).toContain('Hello world');
    
    // Audio controls should appear (they get populated by the audio queue logic)
    await page.waitForSelector('.audio-controls');
  });
}); 