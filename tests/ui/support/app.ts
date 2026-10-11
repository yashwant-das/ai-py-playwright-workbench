import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { type AddressInfo, createServer } from 'node:net';
import { tmpdir } from 'node:os';
import path from 'node:path';

import { test as base } from '@playwright/test';

/** How the app under test is started; see tests/ui/serve.py. */
export type AppOptions = {
  /** The saved model: none (first launch), Demo, a server that is down, or a fake server that answers. */
  model?: 'none' | 'demo' | 'unreachable' | 'fake';
  /** false: the app believes Chromium is not installed. */
  browsers?: boolean;
  /** Save one report per result state before the app starts; their ids arrive in `app.reports`. */
  seed?: boolean;
};

export type App = {
  url: string;
  workspace: string;
  /** Result state → report id, when started with `seed`. */
  reports: Record<string, string>;
};

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const START_TIMEOUT_MS = 30_000;
const STOP_TIMEOUT_MS = 12_000;

function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address() as AddressInfo;
      server.close(() => resolve(port));
    });
  });
}

async function startApp(options: AppOptions): Promise<{ app: App; stop: () => Promise<void> }> {
  const port = await freePort();
  const url = `http://127.0.0.1:${port}`;
  const workspace = mkdtempSync(path.join(tmpdir(), 'workbench-ui-'));
  const args = ['run', 'python', '-m', 'tests.ui.serve', '--port', String(port)];
  args.push('--model', options.model ?? 'demo');
  if (options.browsers === false) args.push('--no-browsers');
  if (options.seed) args.push('--seed');

  // Its own process group, so stopping it also stops any Playwright run it started.
  const child = spawn('uv', args, {
    cwd: REPO_ROOT,
    detached: true,
    env: { ...process.env, WORKBENCH_WORKSPACE: workspace },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let log = '';
  let gone = false;
  child.stdout?.on('data', (chunk: Buffer) => (log += chunk.toString()));
  child.stderr?.on('data', (chunk: Buffer) => (log += chunk.toString()));
  const exited = new Promise<void>((resolve) => {
    const finish = (note = ''): void => {
      gone = true;
      log += note;
      resolve();
    };
    child.once('exit', () => finish());
    child.once('error', (error) => finish(String(error)));
  });

  const signal = (name: NodeJS.Signals): void => {
    try {
      if (child.pid) process.kill(-child.pid, name);
    } catch {
      // already gone
    }
  };
  const stop = async (): Promise<void> => {
    signal('SIGTERM');
    const force = setTimeout(() => signal('SIGKILL'), STOP_TIMEOUT_MS);
    await exited;
    clearTimeout(force);
    rmSync(workspace, { recursive: true, force: true });
  };

  const deadline = Date.now() + START_TIMEOUT_MS;
  let up = false;
  while (!up && !gone && Date.now() < deadline) {
    try {
      up = (await fetch(`${url}/healthz`)).ok;
    } catch {
      // not listening yet
    }
    if (!up) await new Promise((resolve) => setTimeout(resolve, 150));
  }
  if (!up) {
    await stop();
    throw new Error(`The app did not start at ${url}.\n${log}`);
  }

  const reports: Record<string, string> = options.seed
    ? JSON.parse(readFileSync(path.join(workspace, 'seeded.json'), 'utf8'))
    : {};
  return { app: { url, workspace, reports }, stop };
}

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export const test = base.extend<{}, { appOptions: AppOptions; app: App }>({
  appOptions: [{}, { option: true, scope: 'worker' }],
  app: [
    async ({ appOptions }, use) => {
      const { app, stop } = await startApp(appOptions);
      await use(app);
      await stop();
    },
    { scope: 'worker', timeout: 60_000 },
  ],
  baseURL: async ({ app }, use) => {
    await use(app.url);
  },
});

export { expect } from '@playwright/test';
