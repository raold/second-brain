const NodeEnvironment = require('jest-environment-jsdom').default;
class CustomEnv extends NodeEnvironment {
  async setup() {
    await super.setup();
    if (this.global.window && this.global.window.location) {
      this.global.window.location.href = 'http://localhost/';
    }
  }
}
module.exports = CustomEnv; 