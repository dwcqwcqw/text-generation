# RunPod Serverless Dockerfile
# 针对NVIDIA L4 GPU (计算能力8.9) 优化 - 强制GPU模式

FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel-ubuntu22.04

# 设置工作目录
WORKDIR /workspace

# 更新系统包
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    htop \
    vim \
    && rm -rf /var/lib/apt/lists/*

# 升级pip
RUN pip install --upgrade pip

# 安装最新版本的runpod
RUN pip uninstall runpod -y || true
RUN pip install runpod>=1.6.0

# 验证runpod安装
RUN python -c "import runpod; from runpod.serverless import start; print('RunPod安装成功')"

# 设置CUDA环境变量用于llama-cpp-python (L4 GPU是计算能力8.9)
ENV CUDA_VISIBLE_DEVICES=0
ENV LLAMA_CUBLAS=1
ENV CMAKE_ARGS="-DLLAMA_CUBLAS=on -DCMAKE_CUDA_ARCHITECTURES=89"
ENV FORCE_CMAKE=1

# 先安装基础依赖
COPY requirements.txt .
RUN pip install runpod==1.7.11 requests>=2.28.0 torch>=2.0.0 transformers>=4.30.0 accelerate>=0.20.0

# 强制重新编译llama-cpp-python with CUDA for L4 GPU (compute capability 8.9)
RUN pip uninstall llama-cpp-python -y || true
RUN CMAKE_ARGS="-DLLAMA_CUBLAS=on -DCMAKE_CUDA_ARCHITECTURES=89" FORCE_CMAKE=1 pip install llama-cpp-python==0.3.9 --no-cache-dir --force-reinstall

# 验证CUDA支持
RUN python -c "from llama_cpp import Llama; print('llama-cpp-python CUDA support verified for L4 GPU')"

# 复制应用代码
COPY . .

# 设置入口点
CMD ["python", "handler.py"] 