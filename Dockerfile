FROM python:3.10-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    ssl-cert \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.10-slim AS runner

WORKDIR /app

# Copy installed libraries from builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Create folders for persistent volume mounts
RUN mkdir -p data logs downloads config

# Copy source code
COPY main.py setup_wizard.py ./
COPY config/ config/
COPY services/ services/
COPY telegram/ telegram/
COPY utils/ utils/

# Set standard environment variables
ENV PYTHONUNBUFFERED=1
ENV DOWNLOAD_DIR=/app/downloads
ENV STATE_FILE_PATH=/app/data/state.json

# Default command runs the CLI
ENTRYPOINT ["python", "main.py"]
CMD ["start"]
