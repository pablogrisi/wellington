// Setup file for Vitest tests
import { expect, afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/dom';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock fetch for API calls
global.fetch = vi.fn();

// Mock console.error to fail tests on unexpected errors
const originalConsoleError = console.error;
console.error = (...args) => {
  if (args[0]?.includes?.('Warning:')) return;
  originalConsoleError(...args);
};
