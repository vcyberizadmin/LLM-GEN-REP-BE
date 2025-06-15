import fs from 'fs';
import path from 'path';
import FormData from 'form-data';
import { startServer, stopServer, RunningServer } from '../utils/testServer';

describe('Validation errors', () => {
  let server: RunningServer;
  beforeAll(async () => {
    server = await startServer(8011);
  }, 20000);
  afterAll(() => stopServer(server));

  it('rejects unsupported file type', async () => {
    const form = new FormData();
    form.append('query', 'Hello');
    const txtPath = path.resolve(__dirname, '../utils/unsupported.txt');
    fs.writeFileSync(txtPath, 'dummy');
    form.append('files', fs.readFileSync(txtPath), {
      filename: 'unsupported.exe',
      contentType: 'application/octet-stream',
    });
    const res = await fetch(`${server.baseUrl}/analyze`, {
      method: 'POST',
      body: form as any,
      headers: form.getHeaders(),
    });
    expect(res.status).toBe(400);
    fs.unlinkSync(txtPath);
  });
});