const assert = require('node:assert/strict');
const { mkdtempSync, rmSync, writeFileSync } = require('node:fs');
const { tmpdir } = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { test } = require('node:test');

const checker = path.resolve(__dirname, '../../tooling/check-text.cjs');

function check(filename, content) {
  const directory = mkdtempSync(path.join(tmpdir(), 'workbench-text-'));
  try {
    const target = path.join(directory, filename);
    writeFileSync(target, content);
    return spawnSync(process.execPath, [checker, target], { encoding: 'utf8' });
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

test('accepts normal text, CRLF and Markdown hard breaks', () => {
  for (const [name, content] of [
    ['normal.txt', 'one\ntwo\n'],
    ['windows.txt', 'one\r\ntwo\r\n'],
    ['empty.txt', ''],
    ['guide.md', '# Guide\n\nA hard break.  \nNext line.\n'],
  ]) {
    const result = check(name, content);
    assert.equal(result.status, 0, result.stderr);
  }
});

test('rejects trailing whitespace outside intentional Markdown hard breaks', () => {
  for (const [name, content] of [
    ['source.py', 'value = 1  \n'],
    ['guide.md', 'text \n'],
    ['guide.md', 'text\t\n'],
  ]) {
    const result = check(name, content);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /trailing whitespace/);
  }
});

test('rejects missing final newlines and unresolved merge markers', () => {
  for (const [content, error] of [
    ['missing newline', /final newline/],
    ['<<<<<<< HEAD\none\n=======\ntwo\n>>>>>>> branch\n', /merge-conflict marker/],
  ]) {
    const result = check('source.txt', content);
    assert.equal(result.status, 1);
    assert.match(result.stderr, error);
  }
});

test('ignores binary assets instead of interpreting them as text', () => {
  const result = check('image.png', Buffer.from([137, 80, 78, 71, 0, 32]));
  assert.equal(result.status, 0, result.stderr);
});

test('reports all invalid files in one invocation', () => {
  const directory = mkdtempSync(path.join(tmpdir(), 'workbench-text-'));
  try {
    const first = path.join(directory, 'first.txt');
    const second = path.join(directory, 'second.txt');
    writeFileSync(first, 'first');
    writeFileSync(second, 'second \n');
    const result = spawnSync(process.execPath, [checker, first, second], { encoding: 'utf8' });
    assert.equal(result.status, 1);
    assert.match(result.stderr, /first.txt.*final newline/);
    assert.match(result.stderr, /second.txt.*trailing whitespace/);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});
