// @ts-nocheck
import fetch from 'node-fetch';
import { startServer, stopServer, RunningServer } from '../utils/testServer';

describe('CORS & Auth integration', () => {
  let server: RunningServer;
  beforeAll(async () => {
    server = await startServer(8020);
  }, 30000);
  afterAll(() => stopServer(server));

  it('responds with CORS headers', async () => {
    const res = await fetch(`${server.baseUrl}/health`, {
      method: 'GET',
      headers: {
        Origin: 'http://example.com',
      },
    });
    expect(res.status).toBe(200);
    // FastAPI CORS middleware should echo back the Origin when regex matches
    expect(res.headers.get('access-control-allow-origin')).toBe('http://example.com');
  });

  it('allows requests without Authorization header (public endpoints)', async () => {
    const res = await fetch(`${server.baseUrl}/health`);
    expect(res.status).toBe(200);
  });
});