const eslint = require('@eslint/js');
const tseslint = require('typescript-eslint');
const playwright = require('eslint-plugin-playwright');
const prettier = require('eslint-config-prettier');
const globals = require('globals');

module.exports = tseslint.config(
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  {
    ...playwright.configs['flat/recommended'],
    files: ['**/*.spec.ts'],
  },
  {
    ignores: [
      'node_modules/',
      'dist/',
      'build/',
      '.venv/',
      'tests/artifacts/',
      'test-results/',
      'playwright-report/',
      'reports/',
      'workspace/',
      'eslint.config.cjs',
      'src/workbench/web/static/vendor/',
    ],
  },
  {
    // Node.js scripts shipped in the package — allow require(), process, __dirname, etc.
    files: ['src/workbench/**/*.js'],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
  },
  {
    files: ['tests/ui/**/*.spec.ts'],
    rules: {
      'playwright/expect-expect': [
        'warn',
        { assertFunctionNames: ['expectResult', 'expectNoSeriousViolations'] },
      ],
    },
  },
  {
    rules: {
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
      'no-console': 'off',
      '@typescript-eslint/no-require-imports': 'off',
    },
  },
  prettier
);
