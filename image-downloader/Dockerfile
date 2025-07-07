FROM python:3.13-slim

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/app/src:/app

# Optional: Configure supported sources via environment variable
# ENV SUPPORTED_SOURCES='{"wikipedia": ["animals", "plants"], "other_source": ["data_type1"]}'

EXPOSE 9002
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "9002"] 