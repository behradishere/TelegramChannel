# Docker support for containerized deployment
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py ./
COPY tests/ ./tests/

# Create directories for session and logs
RUN mkdir -p /data

# Environment variables (override with docker run -e or docker-compose)
ENV SESSION_NAME=signals_session
ENV DRY_RUN=true
ENV LOG_FILE=/data/bot.log
ENV HEALTH_FILE=/data/health.txt

# Volume for persistent data (sessions, logs, config)
VOLUME ["/data"]

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD python health_check.py || exit 1

# Run the bot
CMD ["python", "main.py"]

