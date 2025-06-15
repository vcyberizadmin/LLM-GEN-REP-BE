import FormData from 'form-data';
import { startServer, stopServer, RunningServer } from '../utils/testServer';

describe('Parse handler validation', () => {
  let server: RunningServer;
  beforeAll(async () => {
    server = await startServer(8010);
  }, 20000);
  afterAll(() => stopServer(server));

  it('returns 400 when no files uploaded', async () => {
    const form = new FormData();
    form.append('query', 'hello');

    const res = await fetch(`${server.baseUrl}/analyze`, {
      method: 'POST',
      body: form as any,
      headers: form.getHeaders(),
    });
    expect(res.status).toBe(400);
  });
});