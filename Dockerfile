# Container image for JobPilot. Works on Hugging Face Spaces (Docker SDK),
# Fly.io, Render (Docker), or anywhere that runs containers.
FROM python:3.11-slim

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hugging Face Spaces expects the app on port 7860; most PaaS inject $PORT.
# Default to 7860, but honor $PORT when provided.
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
