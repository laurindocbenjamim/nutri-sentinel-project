# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/SMARTurinalysis-main/backend:/app/SMARTurinalysis-main

# Set working directory inside the container
WORKDIR /app

# Copy requirements file first to leverage Docker build cache
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire workspace into the container
COPY . .

# Set working directory to the backend folder
WORKDIR /app/SMARTurinalysis-main/backend

# Expose port 8000
EXPOSE 8000

# Run uvicorn server binding to Render's dynamic $PORT
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
