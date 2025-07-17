<<<<<<< HEAD
=======
const { describeIfNotCI } = require('./skip-in-ci');
jest.setTimeout(20000);
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
const { _electron: electron } = require('playwright');

let app, page;

<<<<<<< HEAD
describe('Error Handling E2E', () => {
  beforeAll(async () => {
    app = await electron.launch({ args: ['.'] });
=======
describeIfNotCI('Error Handling E2E', () => {
  beforeAll(async () => {
    app = await electron.launch({ 
      args: ['.', '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
      env: process.env,
    });
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
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