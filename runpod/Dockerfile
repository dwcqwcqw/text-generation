# RunPod Serverless Dockerfile
# 修复 "No module named runpod.serverless.start" 问题

FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel-ubuntu22.04

# 设置工作目录
WORKDIR /workspace

# 更新系统包
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 升级pip
RUN pip install --upgrade pip

# 安装最新版本的runpod (修复模块缺失问题)
RUN pip uninstall runpod -y || true
RUN pip install runpod>=1.6.0

# 验证runpod安装
RUN python -c "import runpod; from runpod.serverless import start; print('RunPod安装成功')"

# 安装其他依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制应用代码
COPY . .

# 设置入口点
CMD ["python", "handler.py"] 