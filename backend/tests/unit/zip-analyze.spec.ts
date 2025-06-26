import fs from 'fs';
import os from 'os';
import path from 'path';
import { execSync } from 'child_process';
import FormData from 'form-data';
import { startServer, stopServer, RunningServer } from '../utils/testServer';

describe('Zip file analyze', () => {
  let server: RunningServer;
  let tmpDir: string;

  beforeAll(async () => {
    server = await startServer(8012);
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ziptest-'));
    const csvPath = path.join(tmpDir, 'data.csv');
    fs.writeFileSync(csvPath, 'a,b\n1,2\n3,4');
    const xlsxPath = path.join(tmpDir, 'data.xlsx');
    fs.writeFileSync(xlsxPath, 'dummy');
    execSync(`zip -j ${path.join(tmpDir, 'files.zip')} ${csvPath} ${xlsxPath}`);
  }, 30000);

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
    stopServer(server);
  });

  it('processes a zip archive of CSV and Excel files', async () => {
    const form = new FormData();
    form.append('query', 'hello');
    const zipPath = path.join(tmpDir, 'files.zip');
    form.append('files', fs.createReadStream(zipPath));

    const res = await fetch(`${server.baseUrl}/analyze`, {
      method: 'POST',
      body: form as any,
      headers: form.getHeaders(),
    });

    expect(res.status).toBe(200);
  });
});
