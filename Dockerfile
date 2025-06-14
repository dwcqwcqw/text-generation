# 使用Python基础镜像
FROM python:3.10-slim

# 安装必要的系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
    git \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制requirements.txt
COPY runpod/requirements.txt .

# 安装Python依赖 (CPU版本)
RUN pip install --no-cache-dir -r requirements.txt

# 复制handler
COPY runpod/handler_llama_ai.py ./handler_llama_ai.py

# 暴露端口
EXPOSE 8000

# 启动命令 - 直接运行handler文件
CMD ["python", "handler_llama_ai.py"] 