FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into a project-local virtual environment
RUN uv sync --frozen --no-dev

# Copy application code
COPY ./MCP .

EXPOSE 8080

CMD [".venv/bin/python", "server.py"]