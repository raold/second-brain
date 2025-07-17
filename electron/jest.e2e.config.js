module.exports = {
  testEnvironment: 'node',
  roots: ['<rootDir>'],
  testMatch: ['**/e2e/**/*.spec.js'],
  testTimeout: 30000,
  setupFilesAfterEnv: ['./jest.setup.js'],
}; 