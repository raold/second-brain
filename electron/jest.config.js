module.exports = {
<<<<<<< HEAD
  testEnvironment: 'jsdom',
  roots: ['<rootDir>'],
  moduleFileExtensions: ['js', 'json'],
  testMatch: ['**/__tests__/**/*.js', '**/?(*.)+(spec|test).js'],
  transform: {},
=======
  testEnvironment: require.resolve('./jest.env.js'),
  testEnvironmentOptions: {
    url: 'http://localhost/',
  },
  roots: ['<rootDir>'],
  testMatch: [
    '**/__tests__/**/*.test.js',
    // Skip E2E tests in CI environment
    ...(process.env.CI !== 'true' ? ['**/e2e/**/*.spec.js'] : []),
  ],
  collectCoverageFrom: [
    '*.js',
    '!jest.*.js',
    '!coverage/**',
    '!node_modules/**',
    '!e2e/**',
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  setupFiles: ['./jest.localstorage.js'],
  setupFilesAfterEnv: ['./jest.setup.js'],
  testTimeout: 20000,
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
}; 