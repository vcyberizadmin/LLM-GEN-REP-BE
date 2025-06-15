// @ts-nocheck
import { spawn, ChildProcess } from 'child_process';
import fetch from 'node-fetch';
import path from 'path';

export interface RunningServer {
  proc: ChildProcess;
  baseUrl: string;
}

/**
 * Start the FastAPI server on a given port and wait until /health is OK.
 */
export async function startServer(port: number = 8000, timeoutMs: number = 30000): Promise<RunningServer> {
  const proc = spawn('python3', ['-m', 'uvicorn', 'backend.main:app', '--port', String(port)], {
    stdio: 'inherit',
    shell: true,
    cwd: path.resolve(__dirname, '../../..'),
    env: {
      ...process.env,
      PYTHONPATH: `${path.resolve(__dirname, '../stubs')}:${process.env.PYTHONPATH || ''}`,
      ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY || 'dummy',
    },
  });

  const baseUrl = `http://127.0.0.1:${port}`;
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${baseUrl}/health`);
      if (res.ok) {
        return { proc, baseUrl };
      }
    } catch (e) {
      // ignore
    }
    await new Promise(r => setTimeout(r, 500));
  }

  proc.kill();
  throw new Error('Server failed to start within timeout');
}

export function stopServer(server: RunningServer) {
  if (server && server.proc) {
    server.proc.kill();
  }
}
