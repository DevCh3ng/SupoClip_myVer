# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies including ffmpeg, patchelf (for execstack fix), and build tools
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    unzip \
    git \
    build-essential \
    cmake \
    patchelf \
    && rm -rf /var/lib/apt/lists/*

# Install deno (required by yt-dlp for YouTube JS challenge solving)
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_DIR=/root/.deno
ENV PATH="/root/.deno/bin:${PATH}"

# Install uv package manager
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy pyproject.toml and uv.lock for dependency installation
COPY pyproject.toml uv.lock* ./

# Create virtual environment and install dependencies using uv sync
# Note: pyproject.toml is configured to use the cu121 index for torch/torchaudio
RUN uv venv .venv && uv sync

# --- Fix cuDNN 8/9 Coexistence for WhisperX Forced Alignment ---
# 1. Install legacy cuDNN 8.x
RUN uv pip install nvidia-cudnn-cu12==8.9.7.29

# 2. Extract cuDNN 8 libs to a stable location
RUN mkdir -p /app/libs/cudnn8 && \
    cp .venv/lib/python3.11/site-packages/nvidia/cudnn/lib/*.so.8 /app/libs/cudnn8/

# 3. Restore modern cuDNN 9 (for PyTorch 2.5 compatibility)
RUN uv pip install --upgrade nvidia-cudnn-cu12

# 4. Clear executable stack flag from libctranslate2 (Docker security restriction fix)
RUN find .venv -name "libctranslate2*.so*" -exec patchelf --clear-execstack {} \;

# Set permanent environment variables
ENV LD_LIBRARY_PATH="/app/libs/cudnn8:/app/.venv/lib/python3.11/site-packages/nvidia/cudnn/lib:${LD_LIBRARY_PATH}"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Copy source code
COPY src/ ./src/

# Copy fonts and transitions directories
COPY fonts/ ./fonts/
COPY transitions/ ./transitions/

# Create necessary directories for video processing
RUN mkdir -p /app/uploads /app/clips /app/logs /tmp

# Expose the port FastAPI will run on
EXPOSE 8000

# Start the application
CMD [".venv/bin/uvicorn", "src.main_refactored:app", "--host", "0.0.0.0", "--port", "8000"]
