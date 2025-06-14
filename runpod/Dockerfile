# 强制x86_64架构GPU优化Dockerfile - 解决CPU_AARCH64问题
FROM --platform=linux/amd64 nvidia/cuda:11.8-devel-ubuntu22.04

# 防止时区配置交互
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# 强制x86_64架构和GPU环境变量
ENV ARCHFLAGS="-arch x86_64"
ENV GGML_CUDA=1
ENV CUDA_VISIBLE_DEVICES=0
ENV FORCE_CMAKE=1
ENV CMAKE_CUDA_ARCHITECTURES="75;80;86;89"
ENV LLAMA_CUBLAS=1
ENV CMAKE_ARGS="-DLLAMA_CUBLAS=on -DCMAKE_CUDA_ARCHITECTURES=75;80;86;89"

# 基础系统更新和依赖安装
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    ninja-build \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 升级pip
RUN pip3 install --upgrade pip

# 设置工作目录
WORKDIR /app

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip3 install --no-cache-dir -r requirements.txt

# 强制重装GPU版本的llama-cpp-python
RUN pip3 uninstall -y llama-cpp-python || true
RUN CMAKE_ARGS="-DLLAMA_CUBLAS=on -DCMAKE_CUDA_ARCHITECTURES=75;80;86;89" \
    FORCE_CMAKE=1 \
    pip3 install llama-cpp-python --upgrade --no-cache-dir --force-reinstall \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu118

# 复制所有必要文件
COPY handler_llama_ai.py ./handler_llama_ai.py
COPY final_gpu_fix.py ./final_gpu_fix.py
COPY start_with_fix.sh ./start_with_fix.sh

# 设置执行权限
RUN chmod +x start_with_fix.sh final_gpu_fix.py

# 创建模型目录
RUN mkdir -p /runpod-volume/text_models

# 端口
EXPOSE 8000

# 启动服务
CMD ["./start_with_fix.sh"] 