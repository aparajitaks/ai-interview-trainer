FROM python:3.10-slim

WORKDIR /app

# Keep Python output unbuffered and avoid .pyc files
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies (minimal) and pip dependencies
COPY requirements.txt ./
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get remove -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /app

# Expose port for uvicorn
EXPOSE 8000

# Run the FastAPI app with uvicorn (production: use a process manager / gunicorn + uvicorn workers as needed)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
