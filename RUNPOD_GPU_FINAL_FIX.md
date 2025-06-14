# RunPod GPU最终修复指南

## 问题分析

从日志可以看出主要问题：
1. **CPU_AARCH64架构错误**: `tensor 'token_embd.weight' (q5_K) cannot be used with preferred buffer type CPU_AARCH64, using CPU instead`
2. **所有层分配到CPU**: 32层全部分配到CPU而不是GPU
3. **推理速度慢**: 28秒加载时间，没有GPU加速

## 根本原因

1. **架构不匹配**: 系统检测为ARM64架构，但实际是x86_64
2. **CUDA版本问题**: llama-cpp-python没有正确编译CUDA支持
3. **环境变量缺失**: 缺少强制GPU的环境变量

## 解决方案

### 1. 立即修复脚本

运行GPU修复脚本：
```bash
cd /app
python3 runpod/fix_gpu_final.py
```

### 2. 手动修复步骤

#### 步骤1: 强制设置环境变量
```bash
export CUDA_VISIBLE_DEVICES=0
export GGML_CUDA=1
export LLAMA_CUBLAS=1
export CMAKE_CUDA_ARCHITECTURES="75;80;86;89"
export FORCE_CMAKE=1
export CMAKE_ARGS="-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75;80;86;89"
export ARCHFLAGS="-arch x86_64"
export CFLAGS="-march=x86-64"
export CXXFLAGS="-march=x86-64"
```

#### 步骤2: 重新安装CUDA版本的llama-cpp-python
```bash
pip uninstall llama-cpp-python -y
pip cache purge
pip install --force-reinstall --no-cache-dir \
    llama-cpp-python \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```

#### 步骤3: 验证GPU支持
```python
import os
os.environ['GGML_CUDA'] = '1'
from llama_cpp import Llama

# 测试GPU加载
model = Llama(
    model_path="/runpod-volume/text_models/L3.2-8X4B.gguf",
    n_ctx=2048,
    n_batch=512,
    n_gpu_layers=-1,  # 强制所有层到GPU
    verbose=True,
    main_gpu=0,
)
```

### 3. 优化的Dockerfile

使用新的Dockerfile重新构建镜像：
```dockerfile
# 强制x86_64架构的CUDA基础镜像
FROM --platform=linux/amd64 nvidia/cuda:12.1-base-ubuntu22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV CUDA_VISIBLE_DEVICES=0
ENV GGML_CUDA=1
ENV LLAMA_CUBLAS=1
ENV CMAKE_CUDA_ARCHITECTURES="75;80;86;89"
ENV FORCE_CMAKE=1
ENV CMAKE_ARGS="-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75;80;86;89"
ENV ARCHFLAGS="-arch x86_64"
ENV CFLAGS="-march=x86-64"
ENV CXXFLAGS="-march=x86-64"
ENV NVCC_APPEND_FLAGS="--allow-unsupported-compiler"

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-dev \
    build-essential cmake \
    nvidia-cuda-toolkit \
    && rm -rf /var/lib/apt/lists/*

# 升级pip
RUN python3 -m pip install --upgrade pip

# 安装CUDA版本的llama-cpp-python
RUN pip install --no-cache-dir \
    llama-cpp-python \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121

# 安装其他依赖
RUN pip install --no-cache-dir \
    runpod GPUtil

# 复制handler
COPY handler_llama_ai.py /app/handler.py
WORKDIR /app

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import llama_cpp; print('OK')" || exit 1

# 启动命令
CMD ["python3", "-u", "handler.py"]
```

### 4. Handler配置优化

关键配置更改：
```python
# 强制所有层到GPU
n_gpu_layers = -1  # 不是25或其他数字，而是-1表示全部

# 强制CUDA后端参数
model = Llama(
    model_path=model_path,
    n_ctx=n_ctx,
    n_batch=n_batch,
    n_gpu_layers=-1,          # 强制所有层到GPU
    verbose=True,             # 显示详细日志
    n_threads=1,              # 最少CPU线程
    use_mmap=True,
    use_mlock=False,
    f16_kv=True,
    logits_all=False,
    main_gpu=0,               # 使用第一个GPU
    tensor_split=None,        # 不分割张量
    rope_scaling_type=None,
    rope_freq_base=0.0,
    rope_freq_scale=0.0,
)
```

## 验证成功标志

修复成功后，日志应该显示：
```
load_tensors: layer   0 assigned to device CUDA:0, is_swa = 0
load_tensors: layer   1 assigned to device CUDA:0, is_swa = 0
...
load_tensors: layer  31 assigned to device CUDA:0, is_swa = 0
```

而不是：
```
load_tensors: layer   0 assigned to device CPU, is_swa = 0
```

## GPU性能预期

修复后的性能指标：
- **加载时间**: 从28秒降至5-8秒
- **推理速度**: 从CPU的慢速推理提升到GPU的快速推理
- **显存使用**: 应该看到GPU显存被占用
- **层分配**: 所有32层都分配到CUDA:0

## 故障排除

### 如果仍然出现CPU_AARCH64错误
1. 确认Docker镜像使用了`--platform=linux/amd64`
2. 检查环境变量是否正确设置
3. 重新安装llama-cpp-python的CUDA版本

### 如果GPU显存不足
根据GPU类型调整配置：
- **RTX 4090 (24GB)**: n_ctx=131072, n_batch=2048
- **L4 (22.5GB)**: n_ctx=65536, n_batch=1024  
- **其他GPU**: n_ctx=32768, n_batch=512

### 如果推理仍然慢
1. 检查GPU利用率: `nvidia-smi`
2. 确认所有层都在GPU上
3. 验证CUDA版本兼容性

## 联系支持

如果问题仍然存在，请提供：
1. 完整的启动日志
2. `nvidia-smi`输出
3. GPU型号和显存大小
4. 使用的模型文件大小

---

**最后更新**: 2025-01-14
**适用版本**: RunPod Serverless, CUDA 12.1+, llama-cpp-python 0.3.9+ 