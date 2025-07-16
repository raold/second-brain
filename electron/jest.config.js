module.exports = {
  testEnvironment: require.resolve('./jest.env.js'),
  testEnvironmentOptions: {
    url: 'http://localhost/',
  },
  roots: ['<rootDir>'],
  moduleFileExtensions: ['js', 'json'],
  testMatch: ['**/__tests__/**/*.js', '**/?(*.)+(spec|test).js'],
  transform: {},
  setupFiles: ['./jest.localstorage.js'],
  setupFilesAfterEnv: ['./jest.setup.js'],
}; 