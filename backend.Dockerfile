# backend.Dockerfile
FROM python:3.13-slim-bookworm

# Set up uv for package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Don't generate .pyc, make logs unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy project metadata first so dependency install can be cached
COPY pyproject.toml README.md ./

# Install dependencies into a project-local virtualenv (.venv) using uv
# --no-dev: only install main dependencies, not dev/test tools
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy the application code
COPY app ./app

# Expose FastAPI port
EXPOSE 8000

# Run the app via uv, which automatically uses the .venv it created
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]