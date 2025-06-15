import fetch from 'node-fetch';
import FormData from 'form-data';
import fs from 'fs';
import path from 'path';

const isProd = !!process.env.PROD_API_URL;

(isProd ? describe : describe.skip)('Nightly Production Smoke', () => {
  const baseUrl = process.env.PROD_API_URL || 'http://localhost:8000';

  it('Health check', async () => {
    const res = await fetch(`${baseUrl}/health`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.status).toBe('ok');
  });

  it(
    'Basic analyze flow with small CSV',
    async () => {
      const form = new FormData();
      form.append('query', 'Show summary');
      const csvPath = path.resolve(__dirname, '../utils/sample.csv');
      const csvContent = fs.readFileSync(csvPath);
      form.append('files', csvContent, {
        filename: 'sample.csv',
        contentType: 'text/csv',
      });

      const res = await fetch(`${baseUrl}/analyze`, {
        method: 'POST',
        body: form as any,
        headers: form.getHeaders(),
      });
      expect(res.status).toBe(200);
    },
    30000,
  );
});