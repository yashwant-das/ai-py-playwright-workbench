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

test('strict JSON rejects comments and trailing commas without rejecting JSONC', () => {
  for (const content of ['{\n  // JSONC only\n  "value": 1\n}\n', '{"value": 1,}\n']) {
    const result = check('manifest.json', content);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /invalid JSON/);
  }
  const jsonc = check('config.jsonc', '{\n  // JSONC is allowed.\n  "value": 1,\n}\n');
  assert.equal(jsonc.status, 0, jsonc.stderr);
  const json = check('manifest.json', '{"value": 1}\n');
  assert.equal(json.status, 0, json.stderr);
});

test('strict JSON cannot bypass syntax checks through null or invalid UTF-8 bytes', () => {
  for (const content of [Buffer.from([123, 0, 125, 10]), Buffer.from([123, 255, 125, 10])]) {
    const result = check('manifest.json', content);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /invalid JSON/);
  }
});

test('full mode skips unstaged deletions and still checks remaining and untracked files', () => {
  const directory = mkdtempSync(path.join(tmpdir(), 'workbench-full-text-'));
  try {
    const deleted = path.join(directory, 'deleted.txt');
    const remaining = path.join(directory, 'remaining.txt');
    writeFileSync(deleted, 'valid\n');
    writeFileSync(remaining, 'valid\n');
    for (const args of [
      ['init', '-q'],
      ['add', '.'],
    ]) {
      const result = spawnSync('git', args, { cwd: directory, encoding: 'utf8' });
      assert.equal(result.status, 0, result.stderr);
    }
    rmSync(deleted);
    const valid = spawnSync(process.execPath, [checker], { cwd: directory, encoding: 'utf8' });
    assert.equal(valid.status, 0, valid.stderr);

    writeFileSync(remaining, 'bad \n');
    writeFileSync(path.join(directory, 'untracked.json'), '{"value": }\n');
    const invalid = spawnSync(process.execPath, [checker], { cwd: directory, encoding: 'utf8' });
    assert.equal(invalid.status, 1);
    assert.match(invalid.stderr, /remaining.txt.*trailing whitespace/);
    assert.match(invalid.stderr, /untracked.json.*invalid JSON/);
    assert.doesNotMatch(invalid.stderr, /ENOENT/);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});
