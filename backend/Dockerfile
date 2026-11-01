FROM python:3.13-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY . .
RUN uv sync --no-dev --no-lock && chmod +x entrypoint.sh
EXPOSE 5000
CMD ["./entrypoint.sh"]
