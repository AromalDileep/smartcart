FROM python:3.10-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y \
    git wget curl libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Install torch CPU manually
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY ./app /app/app


CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
