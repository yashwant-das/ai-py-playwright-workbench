# syntax=docker/dockerfile:1
FROM mcr.microsoft.com/playwright/python:v1.57.0-noble

LABEL org.opencontainers.image.title="ai-py-playwright-workbench" \
      org.opencontainers.image.description="Generates and repairs Playwright tests with local LLMs" \
      org.opencontainers.image.source="https://github.com/yashwant-das/ai-py-playwright-workbench" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install Node.js 24 LTS (needed for ts-morph AST repair and the Playwright runner)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates gnupg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_24.x nodistro main" > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends nodejs

# Set environment variables in a single layer
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
    GRADIO_SERVER_NAME="0.0.0.0" \
    GRADIO_SERVER_PORT=7860 \
    PYTHONUNBUFFERED=1 \
    UV_NO_SYNC=1

# Install Node.js dependencies with cache mount
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --ignore-scripts

# Install a pinned uv for reproducible dependency installs
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /bin/

# Install runtime Python dependencies only (no dev group) with cache mount
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Copy configuration files
COPY playwright.config.ts tsconfig.json ./

# Copy application source code and required resources
COPY src/ ./src/
COPY prompts/ ./prompts/
COPY schemas/ ./schemas/
COPY scripts/ ./scripts/
COPY benchmarks/ ./benchmarks/

# Run as the image's unprivileged user; it owns the directories the app writes to
RUN mkdir -p logs tests/generated tests/artifacts tests/screenshots \
             benchmarks/reports test-results playwright-report && \
    chown -R pwuser:pwuser logs tests benchmarks/reports test-results playwright-report
USER pwuser

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://127.0.0.1:7860/ > /dev/null || exit 1

CMD ["uv", "run", "src/app.py"]
