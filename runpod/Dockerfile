# 综合修复版Dockerfile - 解决GPU兼容性和前端模型选择问题
FROM nvidia/cuda:12.3-devel-ubuntu22.04

# 防止时区配置交互
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# 基础环境变量
ENV GGML_CUDA=1
ENV CUDA_VISIBLE_DEVICES=0
ENV FORCE_CMAKE=1

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

# 安装Python依赖
RUN pip3 install --no-cache-dir \
    runpod \
    psutil \
    requests \
    numpy

# 设置工作目录
WORKDIR /app

# 复制所有修复脚本
COPY comprehensive_fix.py /app/
COPY fix_cuda_rtx4090.py /app/
COPY handler_rtx4090.py /app/
COPY handler_llama_ai.py /app/handler.py

# 设置权限
RUN chmod +x /app/comprehensive_fix.py
RUN chmod +x /app/fix_cuda_rtx4090.py

# 运行综合修复脚本
RUN python3 /app/comprehensive_fix.py

# 创建模型目录
RUN mkdir -p /runpod-volume/text_models

# 健康检查脚本
COPY <<EOF /app/health_check.py
#!/usr/bin/env python3
import sys
import subprocess
import os

def health_check():
    try:
        # 检查CUDA
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ NVIDIA驱动检查失败")
            return False
            
        # 检查GPU型号和计算能力
        gpu_result = subprocess.run(['nvidia-smi', '--query-gpu=name,compute_cap', '--format=csv,noheader'], 
                                  capture_output=True, text=True)
        if gpu_result.returncode == 0:
            gpu_info = gpu_result.stdout.strip()
            print(f"🎯 GPU信息: {gpu_info}")
        
        # 检查llama-cpp-python
        import llama_cpp
        print(f"✅ llama-cpp-python: {llama_cpp.__version__}")
        
        # 检查环境变量
        print(f"GGML_CUDA: {os.environ.get('GGML_CUDA', 'NOT SET')}")
        print(f"CUDA_VISIBLE_DEVICES: {os.environ.get('CUDA_VISIBLE_DEVICES', 'NOT SET')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False

if __name__ == "__main__":
    success = health_check()
    sys.exit(0 if success else 1)
EOF

RUN chmod +x /app/health_check.py

# 运行健康检查
RUN python3 /app/health_check.py

# 启动脚本
COPY <<EOF /app/start.sh
#!/bin/bash
set -e

echo "🚀 启动AI文本生成服务"
echo "📊 系统信息:"
echo "  - 容器架构: $(uname -m)"
echo "  - Python版本: $(python3 --version)"

echo "📊 GPU信息:"
nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv

echo "📊 环境变量:"
echo "  - GGML_CUDA: $GGML_CUDA"
echo "  - CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES"
echo "  - CMAKE_CUDA_ARCHITECTURES: ${CMAKE_CUDA_ARCHITECTURES:-auto}"

echo "🧪 最终验证:"
python3 /app/health_check.py

echo "🚀 启动Handler"
exec python3 /app/handler.py
EOF

RUN chmod +x /app/start.sh

# 端口
EXPOSE 8000

# 启动服务
CMD ["/app/start.sh"] 