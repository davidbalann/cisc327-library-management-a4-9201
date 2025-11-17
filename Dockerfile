FROM python:3.11-slim

# Prevent Python from writing pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies if needed later; keep minimal for Flask + SQLite
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#  && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first to leverage Docker layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source (including the bundled SQLite DB)
COPY . .

# Expose Flask port
EXPOSE 5000

# Run the Flask app (app.py binds to 0.0.0.0:5000 in __main__)
CMD ["python", "app.py"]

