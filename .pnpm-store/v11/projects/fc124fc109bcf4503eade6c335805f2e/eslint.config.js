import tseslint from 'typescript-eslint'

export default tseslint.config(
  ...tseslint.configs.recommended,
  {
    files: ['src/**/*.{ts,tsx}', 'vite.config.ts'],
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      // The existing API view models are incrementally typed; keep unused-value
      // checking strict without turning this tooling task into an API refactor.
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
)
