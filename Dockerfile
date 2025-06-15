# 强制x86_64架构GPU优化Dockerfile - 解决CPU_AARCH64问题
FROM --platform=linux/amd64 nvidia/cuda:12.1.1-devel-ubuntu22.04

# 防止时区配置交互
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# GPU环境变量
ENV GGML_CUDA=1
ENV CUDA_VISIBLE_DEVICES=0

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
COPY runpod/requirements.txt .

# 安装Python依赖
RUN pip3 install --no-cache-dir -r requirements.txt

# 安装预编译的GPU版本llama-cpp-python - 强制使用预编译包
RUN pip3 install --no-cache-dir --only-binary=llama-cpp-python \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121 \
    "llama-cpp-python>=0.3.4"

# 验证GPU安装
COPY runpod/verify_gpu_install.py /tmp/verify_gpu_install.py
RUN python3 /tmp/verify_gpu_install.py && rm /tmp/verify_gpu_install.py

# 复制所有必要文件
COPY runpod/handler_llama_ai.py ./handler_llama_ai.py
COPY runpod/final_gpu_fix.py ./final_gpu_fix.py
COPY runpod/start_with_fix.sh ./start_with_fix.sh

# 设置执行权限
RUN chmod +x start_with_fix.sh final_gpu_fix.py

# 创建模型目录
RUN mkdir -p /runpod-volume/text_models

# 端口
EXPOSE 8000

# 启动服务
CMD ["./start_with_fix.sh"] 