// Skip E2E tests in CI environment where Electron can't launch properly
const skipInCI = process.env.CI === 'true';

module.exports = {
  describeIfNotCI: skipInCI ? describe.skip : describe,
  skipInCI
}; 