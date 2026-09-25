// Minimal setup for PURE unit tests (i18n, isolated components) that must NOT spawn the Python
// API bridge in tests/setup.js. Used by vitest.unit.config.js so the CI `frontend` job can run
// build + these tests without a live backend / venv (the bridge-backed tests in the default
// config still exercise the real backend where one is available).
import {configure} from '@testing-library/react';
configure({asyncUtilTimeout: 4000});

// jsdom lacks these; provide harmless stubs so components that touch them don't crash.
if (typeof window !== 'undefined') {
  window.matchMedia = window.matchMedia || (() => ({
    matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {},
  }));
  globalThis.ResizeObserver = globalThis.ResizeObserver || class {observe() {} unobserve() {} disconnect() {}};
}
