# Security Policy

## Supported versions

Only the latest commit on `main` receives security fixes.

## Reporting a vulnerability

Please report vulnerabilities privately through
[GitHub's private vulnerability reporting](https://github.com/yashwant-das/ai-py-playwright-workbench/security/advisories/new),
not in a public issue.

Include what you found, how to reproduce it, and what an attacker could do with
it. You can expect an acknowledgement within a week.

## Scope and threat model

The workbench is a local developer tool. It is designed to run on your own
machine with a local model (LM Studio or Ollama), and it deliberately does
things that would be unsafe on a shared server:

- It **runs Playwright specs** with `npx playwright test`: the samples, specs
  you upload, and specs a model wrote. A spec is code, and it runs with your
  permissions. Heal only files you trust, and review a generated or healed spec
  before using it elsewhere.
- It **opens whatever URL you give it** in a real browser to collect the page's
  accessibility snapshot, console messages and network requests.

How the app protects itself:

- It listens on `127.0.0.1` only.
- It answers only requests whose `Host` header is `127.0.0.1` or `localhost`,
  so a page that rebinds its DNS name to your machine is refused.
- State-changing requests must have a matching `Origin` when that header is
  present. Without `Origin`, the guard accepts local tools unless Fetch Metadata
  identifies a cross-site browser request. This blocks another website from
  posting a spec through the browser; it is not authentication against local
  processes.
- An upload must be a single `.spec.ts` file of at most 200 KB. It is copied
  into the workspace under a cleaned-up name; your original file is never
  touched.
- Report ids are validated before they are used as file names.

Reports in scope include a way around those checks, path traversal out of the
`workspace/` folder, prompt injection from page content that leads to code
running outside the Playwright test, secrets written to reports or logs, and
vulnerable dependencies.

## Automated checks

- CodeQL scans Python, TypeScript and the GitHub Actions workflows on pull
  requests to `main` and weekly.
- Ruff runs the flake8-bandit (`S`) security rules in CI.
- Dependabot opens grouped update pull requests weekly for uv, npm and GitHub
  Actions; security updates open as soon as they are published.
