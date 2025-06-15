// @ts-nocheck
import fs from 'fs';
import path from 'path';
import FormData from 'form-data';
import fetch from 'node-fetch';
import { startServer, stopServer, RunningServer } from '../utils/testServer';

describe('File upload integration', () => {
  let server: RunningServer;
  const tmpCsv = path.resolve(__dirname, '../utils/tmp-upload.csv');

  beforeAll(async () => {
    server = await startServer(8021);
    fs.writeFileSync(tmpCsv, 'col1,col2\n1,2\n3,4');
  }, 30000);

  afterAll(() => {
    fs.unlinkSync(tmpCsv);
    stopServer(server);
  });

  it('uploads CSV successfully', async () => {
    const form = new FormData();
    form.append('files', fs.createReadStream(tmpCsv));

    const res = await fetch(`${server.baseUrl}/upload`, {
      method: 'POST',
      body: form as any,
      headers: form.getHeaders(),
    });
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.uploaded).toHaveLength(1);
    expect(json.uploaded[0].filename).toBe('tmp-upload.csv');
  });
});