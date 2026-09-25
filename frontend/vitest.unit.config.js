import {defineConfig} from 'vitest/config';

// Pure unit tests only (no Python API bridge). Runs in the CI `frontend` job without a backend.
// The default vitest.config.js still runs the bridge-backed integration tests where a real
// backend + venv exist.
export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.unit.js'],
    include: ['tests/nova-i18n.test.jsx', 'tests/nova-components.test.jsx', 'tests/nova-i18n-parity.test.jsx'],
    testTimeout: 10000,
  },
});
