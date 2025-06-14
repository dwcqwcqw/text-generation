#!/bin/bash
set -e

echo "🚀 启动GPU优化的AI文本生成服务"
echo "📊 系统信息:"
echo "  - 容器架构: $(uname -m)"
echo "  - Python版本: $(python3 --version)"

# 强制设置环境变量
export ARCHFLAGS="-arch x86_64"
export GGML_CUDA=1
export CUDA_VISIBLE_DEVICES=0
export LLAMA_CUBLAS=1
export CMAKE_CUDA_ARCHITECTURES="75;80;86;89"
export FORCE_CMAKE=1
export CMAKE_ARGS="-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75;80;86;89"

echo "📊 GPU信息:"
nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv || echo "⚠️ 无法获取GPU信息"

echo "📊 环境变量:"
echo "  - GGML_CUDA: $GGML_CUDA"
echo "  - CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES"
echo "  - CMAKE_CUDA_ARCHITECTURES: $CMAKE_CUDA_ARCHITECTURES"
echo "  - ARCHFLAGS: $ARCHFLAGS"

echo "🔧 运行最终GPU修复..."
python3 final_gpu_fix.py || echo "⚠️ GPU修复脚本执行完成（可能有警告）"

echo "🚀 启动Handler"
exec python3 handler_llama_ai.py 