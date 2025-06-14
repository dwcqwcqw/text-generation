# 🔧 RunPod GPU修复指南 - 解决CPU_AARCH64问题

## 🚨 问题症状
- 日志显示：`load_tensors: tensor 'token_embd.weight' (q5_K) (and 354 others) cannot be used with preferred buffer type CPU_AARCH64, using CPU instead`
- 所有32层都分配到CPU：`load_tensors: layer 0-31 assigned to device CPU`
- 推理速度慢（28秒+）
- 没有看到：`llama_model_loader: using CUDA for GPU acceleration`

## 🎯 根本原因
1. **架构不匹配**：容器使用了ARM架构而不是x86_64
2. **llama-cpp-python版本错误**：安装了CPU版本而不是GPU版本
3. **CUDA配置不正确**：环境变量和编译参数错误

## 🔧 解决方案

### 方案1：使用修复后的Dockerfile（推荐）

```bash
# 使用强制x86_64架构的Dockerfile
docker build -f runpod/Dockerfile -t your-image:gpu-fixed .

# 或者使用RTX 4090专用版本
docker build -f runpod/Dockerfile.rtx4090 -t your-image:rtx4090 .
```

### 方案2：手动修复现有容器

```bash
# 1. 检查架构
uname -m  # 必须是 x86_64

# 2. 强制重装GPU版本
pip3 uninstall -y llama-cpp-python
CMAKE_CUDA_ARCHITECTURES="75;80;86;89" pip3 install llama-cpp-python --upgrade --no-cache-dir \
  --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121

# 3. 设置环境变量
export GGML_CUDA=1
export CUDA_VISIBLE_DEVICES=0
export CMAKE_CUDA_ARCHITECTURES="89"  # RTX 4090用89，其他GPU用对应值
export LLAMA_CUBLAS=1
```

## 📊 关键修复点

### 1. 强制x86_64架构
```dockerfile
FROM --platform=linux/amd64 nvidia/cuda:12.1-base-ubuntu22.04
```

### 2. 正确的GPU环境变量
```bash
ENV GGML_CUDA=1
ENV CUDA_VISIBLE_DEVICES=0
ENV CMAKE_CUDA_ARCHITECTURES="89"  # RTX 4090
ENV LLAMA_CUBLAS=1
```

### 3. 预编译GPU版本安装
```bash
pip3 install llama-cpp-python --upgrade --no-cache-dir \
  --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```

### 4. 强制GPU层配置
```python
llama_model = llama_cpp.Llama(
    model_path=model_path,
    n_gpu_layers=-1,  # 强制所有层用GPU
    n_ctx=65536,
    n_batch=1024,
    verbose=True,     # 显示详细日志
    use_mmap=True,
    f16_kv=True,
)
```

## 🎯 GPU计算能力对照表

| GPU型号 | 计算能力 | CMAKE_CUDA_ARCHITECTURES |
|---------|----------|--------------------------|
| RTX 4090 | 8.9 | 89 |
| RTX 4080 | 8.9 | 89 |
| RTX 4070 | 8.9 | 89 |
| RTX 3090 | 8.6 | 86 |
| RTX 3080 | 8.6 | 86 |
| L40 | 8.9 | 89 |
| A100 | 8.0 | 80 |
| V100 | 7.0 | 70 |

## ✅ 验证成功标志

部署成功后，日志中应该看到：

```
✅ 系统架构: x86_64
✅ NVIDIA驱动正常
✅ llama-cpp-python版本: 0.3.9
🎯 检测到GPU: NVIDIA GeForce RTX 4090
🔧 计算能力: 8.9
📊 RTX 4090环境变量:
  ✅ GGML_CUDA: 1 (期望: 1)
  ✅ CUDA_VISIBLE_DEVICES: 0 (期望: 0)
  ✅ CMAKE_CUDA_ARCHITECTURES: 89 (期望: 89)

# 模型加载时应该看到：
llama_model_loader: using CUDA for GPU acceleration  # 🎯 关键！
load_tensors: layer 0-31 assigned to device CUDA:0   # 🎯 关键！
```

## 🚀 快速部署命令

### RunPod部署
```bash
# 1. 克隆仓库
git clone https://github.com/dwcqwcqw/text-generation.git
cd text-generation

# 2. 构建镜像（选择一个）
docker build -f runpod/Dockerfile -t text-gen:gpu-fixed .
# 或者RTX 4090专用
docker build -f runpod/Dockerfile.rtx4090 -t text-gen:rtx4090 .

# 3. 推送到Docker Hub
docker tag text-gen:gpu-fixed your-dockerhub/text-gen:gpu-fixed
docker push your-dockerhub/text-gen:gpu-fixed

# 4. 在RunPod中使用新镜像
```

### 本地测试
```bash
# 测试GPU支持
docker run --gpus all -it text-gen:gpu-fixed python3 /app/verify_gpu.py

# 运行服务
docker run --gpus all -p 8000:8000 text-gen:gpu-fixed
```

## 🔍 故障排除

### 如果仍然显示CPU_AARCH64：
1. 检查Docker构建平台：`docker buildx ls`
2. 强制使用x86_64：`docker buildx build --platform linux/amd64`
3. 检查基础镜像：确保使用`--platform=linux/amd64`

### 如果GPU层仍然分配到CPU：
1. 检查CUDA驱动：`nvidia-smi`
2. 检查llama-cpp-python版本：`pip show llama-cpp-python`
3. 重新安装GPU版本：使用上面的安装命令

### 性能验证：
- CPU模式：推理时间 > 20秒
- GPU模式：推理时间 < 3秒
- 显存使用：应该看到GPU显存被占用

## 📞 支持

如果问题仍然存在，请提供：
1. `uname -m` 输出
2. `nvidia-smi` 输出
3. `pip show llama-cpp-python` 输出
4. 完整的模型加载日志 