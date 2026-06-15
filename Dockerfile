# Daimon - container for the Hugging Face Space (Docker SDK).
# CUDA-enabled build: llama-server uses GGML_BACKEND_DL=ON, so the CUDA backend
# loads as a plugin only when a GPU + driver are present. model/serve.sh's
# HARDWARE=auto detects the GPU via nvidia-smi and sets -ngl accordingly, so the
# same image runs unchanged on the free CPU-only tier, a GPU tier, or ZeroGPU.

ARG CUDA_VERSION=12.8.1
ARG UBUNTU_VERSION=24.04

# ---- Build llama-server ----
FROM nvidia/cuda:${CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION} AS llama-build

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential cmake git \
    && rm -rf /var/lib/apt/lists/*

# CMAKE_CUDA_ARCHITECTURES="75-virtual" compiles PTX (not per-GPU SASS) for a
# single baseline (Turing, compute 7.5). The NVIDIA driver JIT-compiles that PTX
# for whatever GPU is actually present (T4, RTX 30xx/40xx, A100, L4, H100, ...),
# so one build covers any GPU with far less build time/RAM than per-arch SASS.
# GGML_CPU_ALL_VARIANTS keeps the CPU backend fast on any host CPU. -j4 caps
# parallel nvcc jobs (each can use 1-2GB RAM) to avoid OOM-killing the daemon.
RUN git clone --depth 1 https://github.com/ggml-org/llama.cpp /tmp/llama.cpp \
    && cmake /tmp/llama.cpp -B /tmp/llama.cpp/build \
         -DGGML_CUDA=ON -DGGML_BACKEND_DL=ON -DGGML_CPU_ALL_VARIANTS=ON \
         -DGGML_NATIVE=OFF -DCMAKE_CUDA_ARCHITECTURES="75-virtual" \
         -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF \
    && cmake --build /tmp/llama.cpp/build --config Release -j4 --target llama-server \
    && mkdir -p /opt/llama/lib /opt/llama/bin \
    && find /tmp/llama.cpp/build -name "*.so*" -exec cp -P {} /opt/llama/lib/ \; \
    && cp /tmp/llama.cpp/build/bin/llama-server /opt/llama/bin/

# ---- Runtime image ----
FROM nvidia/cuda:${CUDA_VERSION}-runtime-ubuntu${UBUNTU_VERSION}

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    LD_LIBRARY_PATH=/usr/local/bin

# Python (for the app), Node 20 (for @personaxis/persona.md), and libgomp1
# (OpenMP runtime required by llama-server's CPU backend).
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip ca-certificates curl git libgomp1 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/local/bin/python \
    && ln -sf /usr/bin/pip3 /usr/local/bin/pip

# ggml_backend_load_all() (GGML_BACKEND_DL=ON) looks for backend plugins
# (ggml-cpu*.so, ggml-cuda.so, ...) next to the executable, so everything lives
# in /usr/local/bin alongside llama-server. LD_LIBRARY_PATH covers the shared
# library dependencies (libggml-base.so, libllama.so, ...) of those plugins.
COPY --from=llama-build /opt/llama/lib/ /usr/local/bin/
COPY --from=llama-build /opt/llama/bin/llama-server /usr/local/bin/

WORKDIR /app

# Python deps first (better layer caching).
COPY requirements.txt ./
RUN pip install --break-system-packages -r requirements.txt

# The persona.md spec engine (single source of truth for safety).
RUN npm install -g @personaxis/persona.md

COPY . .

# Model weights are NOT baked in (offline-capable, no secrets, large files). They are
# downloaded at runtime via model/download_model.py once MODEL_REPO/MODEL_FILE are set.

# HF Space serves the app on 7860; the model server runs on 8080 internally.
EXPOSE 7860 8080

# F4: bring up the local model server (if TEXT_MODEL_PROVIDER=local) and the app.
CMD ["bash", "app/start.sh"]
