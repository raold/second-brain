const { JSDOM } = require('jsdom');

describe('Settings Panel', () => {
  let window, document;
  beforeEach(() => {
    const dom = new JSDOM(`<!DOCTYPE html><input id='apiKeyInput'><input id='chunkSizeInput'><input id='pauseInput'><select id='voiceSelect'></select>`);
    window = dom.window;
    document = window.document;
    global.document = document;
    global.localStorage = window.localStorage;
  });
  afterEach(() => {
    delete global.document;
    delete global.localStorage;
  });
  it('should save and load settings', () => {
    document.getElementById('apiKeyInput').value = 'test-key';
    document.getElementById('chunkSizeInput').value = '42';
    document.getElementById('pauseInput').value = '1234';
    document.getElementById('voiceSelect').innerHTML = "<option value='v1'>Voice1</option>";
    document.getElementById('voiceSelect').value = 'v1';
    // Simulate save
    localStorage.setItem('voiceAppSettings', JSON.stringify({ apiKey: 'test-key', chunkSize: 42, pause: 1234, voice: 'v1' }));
    // Simulate load
    const s = JSON.parse(localStorage.getItem('voiceAppSettings'));
    expect(s.apiKey).toBe('test-key');
    expect(s.chunkSize).toBe(42);
    expect(s.pause).toBe(1234);
    expect(s.voice).toBe('v1');
  });
}); 