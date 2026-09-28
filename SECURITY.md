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
machine against a local LLM (LM Studio or Ollama), and it deliberately does
things that would be unsafe on a shared server:

- It **executes LLM-generated Playwright code** with `npx playwright test`.
  Treat every generated or healed spec as untrusted code and review it before
  running it outside the workbench.
- It **opens whatever URL you give it** in a real browser to collect DOM,
  accessibility, console and network context.
- The Gradio UI binds to `127.0.0.1` by default. The Docker image binds to
  `0.0.0.0` so the port can be published; only publish it on a trusted network.

Reports in scope include path traversal out of `tests/generated/`, prompt
injection from page content that leads to code running outside the Playwright
sandbox, secrets written to logs or artifacts, and vulnerable dependencies.

## Automated checks

- CodeQL scans Python, TypeScript and the GitHub Actions workflows on every
  pull request and weekly.
- Ruff runs the flake8-bandit (`S`) security rules in CI.
- Dependabot opens weekly update PRs for uv, npm, GitHub Actions and the Docker
  base image.
