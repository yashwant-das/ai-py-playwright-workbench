// Shared by lint-staged and CI; only examines repository files or explicit paths.
const { execFileSync } = require('node:child_process');
const { readFileSync } = require('node:fs');

const files = process.argv.slice(2);
if (files.length === 0) {
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
  const bytes = readFileSync(file);
  if (bytes.includes(0)) continue;
  let text;
  try {
    text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  } catch {
    continue; // Binary assets do not have text whitespace conventions.
  }
  const report = (line, message) => {
    console.error(`${file}:${line}: ${message}`);
    failed = true;
  };
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
