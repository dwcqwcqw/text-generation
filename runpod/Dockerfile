# RunPod Serverless Dockerfile
# 针对NVIDIA L4 GPU (计算能力8.9) 优化 - 强制GPU模式

# 使用NVIDIA CUDA基础镜像
FROM nvidia/cuda:12.1-devel-ubuntu22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0
ENV GGML_CUDA=1
ENV CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=89"
ENV FORCE_CMAKE=1
ENV CUDA_LAUNCH_BLOCKING=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建符号链接
RUN ln -s /usr/bin/python3 /usr/bin/python

# 升级pip
RUN pip install --upgrade pip

# 设置工作目录
WORKDIR /app

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖（先安装其他依赖）
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 复制CUDA修复脚本
COPY fix_cuda.py .

# 运行CUDA修复脚本，强制重新编译llama-cpp-python
RUN python fix_cuda.py || echo "CUDA修复脚本执行完成"

# 安装其他依赖
RUN pip install -r requirements.txt

# 复制应用代码
COPY . .

# 复制诊断脚本
COPY cuda_diagnostic.py .

# 运行诊断脚本验证CUDA支持
RUN python cuda_diagnostic.py || echo "诊断完成"

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-u", "handler_llama_ai.py"] 