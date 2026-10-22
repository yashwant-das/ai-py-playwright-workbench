// Shared by lint-staged and CI; only examines repository files or explicit paths.
const { execFileSync } = require('node:child_process');
const { readFileSync } = require('node:fs');

const files = process.argv.slice(2);
const fullMode = files.length === 0;
if (fullMode) {
  files.push(
    ...execFileSync('git', ['ls-files', '--cached', '--others', '--exclude-standard', '-z'], {
      encoding: 'utf8',
    })
      .split('\0')
      .filter(Boolean)
  );
}

let failed = false;
for (const file of new Set(files)) {
  // Historical records, generated assets and vendored libraries retain their bytes.
  const relative = file.replaceAll('\\', '/');
  if (
    /(^|\/)(docs\/superpowers\/(plans|specs)|src\/workbench\/web\/static\/vendor)\//.test(relative)
  ) {
    continue;
  }
  const report = (line, message) => {
    console.error(`${file}:${line}: ${message}`);
    failed = true;
  };
  let bytes;
  try {
    bytes = readFileSync(file);
  } catch (error) {
    // git's index still lists an unstaged deletion; it is not working-tree content.
    if (fullMode && error.code === 'ENOENT') continue;
    throw error;
  }
  const strictJson = /\.json$/i.test(file);
  if (!strictJson && bytes.includes(0)) continue;
  let text;
  try {
    text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  } catch {
    if (strictJson) report(1, 'invalid JSON: expected UTF-8 text');
    continue; // Binary assets do not have text whitespace conventions.
  }
  if (strictJson) {
    try {
      JSON.parse(text);
    } catch {
      report(1, 'invalid JSON syntax');
    }
  }
  const lines = text.split(/\r?\n/);
  if (text && !text.endsWith('\n')) report(lines.length, 'missing final newline');
  lines.forEach((line, index) => {
    if (/^(<<<<<<< |=======$|>>>>>>> )/.test(line)) report(index + 1, 'merge-conflict marker');
    const whitespace = line.match(/[\t ]+$/)?.[0];
    const hardBreak = /\.md$/i.test(file) && whitespace === '  ' && /\S/.test(line);
    if (whitespace && !hardBreak) report(index + 1, 'trailing whitespace');
  });
}
process.exitCode = failed ? 1 : 0;
