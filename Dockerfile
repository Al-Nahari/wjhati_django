FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose Django port
EXPOSE 8000

# Copy start.sh
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Use the script as entrypoint
ENTRYPOINT ["/start.sh"]

# Run server
CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]
