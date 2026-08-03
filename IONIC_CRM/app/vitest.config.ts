import { defineConfig } from 'vitest/config';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    /**
     * Run test FILES one at a time.
     *
     * Each PGlite instance carries a whole Postgres compiled to WebAssembly, and
     * the database-backed suites create one per test for isolation — the schema
     * deliberately offers no way to delete a punch, so a fresh database is the
     * honest way to isolate rather than building an escape hatch an attacker
     * could also use. Running files in parallel multiplies those heaps and kills
     * the worker with `ERR_IPC_CHANNEL_CLOSED`, which looks nothing like the
     * out-of-memory failure it actually is.
     */
    fileParallelism: false,

    testTimeout: 30_000,
    hookTimeout: 30_000,
  },
});
