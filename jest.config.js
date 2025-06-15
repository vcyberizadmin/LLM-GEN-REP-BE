/** @type {import('ts-jest').JestConfigWithTsJest} */
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  testMatch: ['**/backend/tests/**/*.spec.ts'],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  transform: { '\\.(ts|tsx)$': 'ts-jest' },
  globals: { 'ts-jest': { diagnostics: false } }
};
