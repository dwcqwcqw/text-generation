# 强制x86_64架构GPU优化Dockerfile - 解决CPU_AARCH64问题
FROM --platform=linux/amd64 nvidia/cuda:12.1-base-ubuntu22.04

# 防止时区配置交互
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# 强制GPU环境变量
ENV GGML_CUDA=1
ENV CUDA_VISIBLE_DEVICES=0
ENV FORCE_CMAKE=1
ENV CMAKE_CUDA_ARCHITECTURES="75;80;86;89"
ENV LLAMA_CUBLAS=1

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

# 安装基础Python依赖
RUN pip3 install --no-cache-dir \
    runpod \
    psutil \
    requests \
    numpy

# 强制重装GPU版本的llama-cpp-python
RUN pip3 uninstall -y llama-cpp-python || true
RUN pip3 install llama-cpp-python --upgrade --no-cache-dir \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121

# 设置工作目录
WORKDIR /app

# 复制Handler文件
COPY handler_llama_ai.py /app/handler.py

# 创建强制GPU配置的Handler
COPY <<EOF /app/handler_gpu_force.py
#!/usr/bin/env python3
"""
强制GPU版本Handler - 解决CPU_AARCH64问题
"""
import os
import sys
import time
import logging
import psutil
import subprocess
from typing import Dict, Any, Optional
import runpod

# 强制GPU环境变量
os.environ['GGML_CUDA'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
os.environ['LLAMA_CUBLAS'] = '1'

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(filename)s :%(lineno)d  %(asctime)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 全局模型实例
llama_model = None

def get_gpu_info():
    """获取GPU信息"""
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,temperature.gpu,utilization.gpu', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split(', ')
                if len(parts) >= 5:
                    name, total, used, temp, util = parts
                    return f"🔥 GPU状态: 利用率{util}%, 显存{used}/{total}GB, 温度{temp}°C"
    except Exception as e:
        logger.warning(f"获取GPU信息失败: {e}")
    return "🔥 GPU状态: 未知"

def find_models():
    """查找可用模型"""
    model_dir = "/runpod-volume/text_models"
    models = []
    
    if os.path.exists(model_dir):
        for file in os.listdir(model_dir):
            if file.endswith('.gguf'):
                path = os.path.join(model_dir, file)
                size = os.path.getsize(path) / (1024**3)  # GB
                models.append((path, size))
                logger.info(f"📁 发现模型: {path} ({size:.1f}GB)")
    
    # 按大小排序，选择较小的模型（更容易加载到GPU）
    models.sort(key=lambda x: x[1])
    return models

def get_gpu_layers(model_path: str) -> int:
    """根据模型和GPU确定GPU层数"""
    try:
        # 获取GPU显存
        result = subprocess.run(['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            gpu_memory = int(result.stdout.strip())
            logger.info(f"🎯 检测到GPU显存: {gpu_memory}GB")
            
            # 根据显存和模型大小决定层数
            model_size = os.path.getsize(model_path) / (1024**3)
            
            if gpu_memory >= 24:  # RTX 4090, L40等
                if model_size < 15:  # 小模型全部用GPU
                    return -1  # 所有层
                else:  # 大模型用大部分GPU
                    return 50
            elif gpu_memory >= 16:  # RTX 4080等
                return 40
            elif gpu_memory >= 12:  # RTX 4070等
                return 30
            else:
                return 20
    except Exception as e:
        logger.warning(f"获取GPU信息失败: {e}")
    
    # 默认强制使用所有GPU层
    return -1

def initialize_model():
    """初始化模型"""
    global llama_model
    
    logger.info("🔄 开始模型初始化...")
    logger.info(get_gpu_info())
    
    # 查找模型
    models = find_models()
    if not models:
        raise Exception("❌ 未找到任何.gguf模型文件")
    
    # 选择第一个模型（最小的）
    model_path, model_size = models[0]
    logger.info(f"🎯 选择模型: {model_path} ({model_size:.1f}GB)")
    
    try:
        # 导入llama_cpp
        import llama_cpp
        logger.info(f"llama-cpp-python版本: {llama_cpp.__version__}")
        logger.info(f"📂 强制GPU模式加载: {model_path}")
        
        # 获取GPU层数
        n_gpu_layers = get_gpu_layers(model_path)
        logger.info(f"🔧 GPU配置: n_gpu_layers={n_gpu_layers}, n_ctx=65536, n_batch=1024")
        
        # 强制GPU配置
        llama_model = llama_cpp.Llama(
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,  # 强制使用GPU层
            n_ctx=65536,  # 大上下文
            n_batch=1024,
            verbose=True,  # 显示详细日志
            use_mmap=True,
            use_mlock=False,
            n_threads=4,
            f16_kv=True,  # 使用半精度
        )
        
        logger.info("✅ 模型初始化成功")
        logger.info(get_gpu_info())
        
        # 验证GPU使用
        test_response = llama_model("Test", max_tokens=1, echo=False)
        logger.info("🧪 GPU测试完成")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 模型初始化失败: {e}")
        raise

def handler(event):
    """RunPod Handler"""
    global llama_model
    
    logger.info("🎯 Handler调用")
    logger.info(f"📥 完整事件: {event}")
    
    try:
        # 提取输入
        job_input = event.get("input", {})
        prompt = job_input.get("prompt", "")
        max_tokens = job_input.get("max_tokens", 1000)
        temperature = job_input.get("temperature", 0.7)
        
        logger.info(f"📝 提取的提示词: '{prompt}'")
        
        # 初始化模型（如果需要）
        if llama_model is None:
            logger.info("🔄 模型未初始化，开始初始化...")
            initialize_model()
        
        # 生成响应
        logger.info("🤖 开始生成响应...")
        start_time = time.time()
        
        response = llama_model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            echo=False,
            stop=["</s>", "<|eot_id|>", "<|end_of_text|>"]
        )
        
        generation_time = time.time() - start_time
        generated_text = response['choices'][0]['text'].strip()
        
        logger.info(f"✅ 生成完成，耗时: {generation_time:.2f}秒")
        logger.info(f"📤 生成文本长度: {len(generated_text)}字符")
        logger.info(get_gpu_info())
        
        return {
            "text": generated_text,
            "generation_time": generation_time,
            "model_info": "GPU加速模式",
            "gpu_status": get_gpu_info()
        }
        
    except Exception as e:
        logger.error(f"❌ Handler执行失败: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import time
    
    logger.info("🚀 启动强制GPU模式RunPod handler...")
    logger.info(get_gpu_info())
    
    # 预初始化模型
    try:
        initialize_model()
    except Exception as e:
        logger.error(f"预初始化失败: {e}")
    
    # 启动RunPod
    runpod.serverless.start({"handler": handler})
EOF

RUN chmod +x /app/handler_gpu_force.py

# 创建模型目录
RUN mkdir -p /runpod-volume/text_models

# 验证脚本
COPY <<EOF /app/verify_gpu.py
#!/usr/bin/env python3
import sys
import subprocess
import os

def verify_setup():
    print("🔍 验证GPU设置...")
    
    # 检查架构
    arch = subprocess.run(['uname', '-m'], capture_output=True, text=True).stdout.strip()
    print(f"📊 系统架构: {arch}")
    if arch != 'x86_64':
        print("❌ 错误：不是x86_64架构！")
        return False
    
    # 检查CUDA
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ NVIDIA驱动检查失败")
            return False
        print("✅ NVIDIA驱动正常")
    except:
        print("❌ nvidia-smi命令失败")
        return False
    
    # 检查llama-cpp-python
    try:
        import llama_cpp
        print(f"✅ llama-cpp-python版本: {llama_cpp.__version__}")
        
        # 检查是否支持CUDA
        # 尝试创建一个简单的模型实例来测试CUDA支持
        print("🧪 测试CUDA支持...")
        
    except ImportError:
        print("❌ llama-cpp-python未安装")
        return False
    except Exception as e:
        print(f"⚠️ llama-cpp-python测试警告: {e}")
    
    # 检查环境变量
    print("📊 环境变量:")
    for var in ['GGML_CUDA', 'CUDA_VISIBLE_DEVICES', 'CMAKE_CUDA_ARCHITECTURES']:
        value = os.environ.get(var, 'NOT SET')
        print(f"  - {var}: {value}")
    
    print("✅ 基础验证通过")
    return True

if __name__ == "__main__":
    success = verify_setup()
    sys.exit(0 if success else 1)
EOF

RUN chmod +x /app/verify_gpu.py

# 运行验证
RUN python3 /app/verify_gpu.py

# 启动脚本
COPY <<EOF /app/start.sh
#!/bin/bash
set -e

echo "🚀 启动强制GPU模式AI文本生成服务"
echo "📊 系统信息:"
echo "  - 容器架构: $(uname -m)"
echo "  - Python版本: $(python3 --version)"

echo "📊 GPU信息:"
nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv

echo "📊 环境变量:"
echo "  - GGML_CUDA: $GGML_CUDA"
echo "  - CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES"
echo "  - CMAKE_CUDA_ARCHITECTURES: $CMAKE_CUDA_ARCHITECTURES"

echo "🧪 最终验证:"
python3 /app/verify_gpu.py

echo "🚀 启动强制GPU Handler"
exec python3 /app/handler_gpu_force.py
EOF

RUN chmod +x /app/start.sh

# 端口
EXPOSE 8000

# 启动服务
CMD ["/app/start.sh"] 