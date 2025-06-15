// @ts-nocheck
import path from 'path';
import fs from 'fs';
import fetch from 'node-fetch';
import { spawn, ChildProcess } from 'child_process';
import { Verifier } from '@pact-foundation/pact';

/**
 * Pact provider verification test for the FastAPI backend.
 * Starts the uvicorn server on a test port, then verifies the pact file.
 */

describe('FastAPI Provider Pact Verification', () => {
  const port = 5005;
  const baseUrl = `http://localhost:${port}`;
  let server: ChildProcess | undefined;

  /** Helper: wait until /health returns 200 or timeout */
  const waitForServer = async (timeoutMs = 10000) => {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      try {
        const res = await fetch(`${baseUrl}/health`);
        if (res.ok) return;
      } catch (_) {
        /* ignore */
      }
      await new Promise((r) => setTimeout(r, 500));
    }
    throw new Error('Backend server did not start within timeout');
  };

  beforeAll(async () => {
    // Spawn uvicorn in a subprocess
    const projectRoot = path.resolve(__dirname, '../../..'); // repo root
    server = spawn('uvicorn', ['backend.main:app', '--port', port.toString()], {
      cwd: projectRoot,
      shell: true,
      stdio: 'inherit',
    });
    await waitForServer();
  }, 20000); // allow extra time for start

  afterAll(() => {
    if (server) server.kill();
  });

  it('validates the expectations of the Frontend consumer', async () => {
    // Ensure pact file exists (create minimal one if not present)
    const pactDir = path.resolve(process.cwd(), 'pacts');
    const pactPath = path.join(pactDir, 'frontend-llm-gen-report-backend.json');
    if (!fs.existsSync(pactDir)) fs.mkdirSync(pactDir);
    if (!fs.existsSync(pactPath)) {
      const pact = {
        consumer: { name: 'Frontend' },
        provider: { name: 'LLM-GEN-REPORT Backend' },
        interactions: [
          {
            description: 'a health check',
            providerStates: [{ name: 'provider is healthy' }],
            request: { method: 'GET', path: '/health' },
            response: {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
              body: { status: 'ok' },
            },
          },
        ],
        metadata: { pactSpecification: { version: '3.0.0' } },
      } as any;
      fs.writeFileSync(pactPath, JSON.stringify(pact, null, 2));
    }

    const opts = {
      provider: 'LLM-GEN-REPORT Backend',
      providerBaseUrl: baseUrl,
      pactFiles: [pactPath],
    } as any;

    const output = await new Verifier(opts).verifyProvider();
    console.log('Pact Verification Complete:\n', output);
  }, 30000);
});