FROM ubuntu:22.04

# 设置环境变量
ENV PYTHON_VERSION=3.11
ENV DEBIAN_FRONTEND=noninteractive

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-dev \
    python3-pip \
    git \
    curl \
    cmake \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 设置Python别名
RUN ln -s /usr/bin/python${PYTHON_VERSION} /usr/bin/python

# 设置工作目录
WORKDIR /app

# 复制RunPod相关文件
COPY runpod/requirements.txt .
COPY runpod/handler.py .

# 安装Python依赖，确保CUDA支持
ENV CMAKE_ARGS="-DLLAMA_CUBLAS=on"
ENV FORCE_CMAKE=1
RUN pip install --no-cache-dir -r requirements.txt

# 创建模型目录
RUN mkdir -p /runpod-volume/text_models

# 设置启动命令
CMD ["python", "handler.py"] 