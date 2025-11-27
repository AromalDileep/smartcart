FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git curl wget libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# --------------------------------------------------
# 🔥 Install PyTorch CPU version manually
# --------------------------------------------------
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# --------------------------------------------------
# 🔥 Install other Python dependencies
# --------------------------------------------------
COPY ../requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir -r /workspace/requirements.txt

# Set working directory
WORKDIR /workspace

CMD ["bash"]
