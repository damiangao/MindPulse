import { expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';

afterEach(() => {
  cleanup();
});

expect.extend({
  toBeWithin(received, start, end) {
    const pass = received >= start && received <= end;
    return {
      pass,
      message: () => `expected ${received} ${pass ? 'not ' : ''}to be within ${start} and ${end}`,
    };
  },
});