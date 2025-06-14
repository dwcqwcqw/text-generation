# RTX 4090 与 llama-cpp-python 兼容性指南

## 🎯 主要问题

RTX 4090使用Ada Lovelace架构，计算能力为**8.9**，这是一个相对较新的架构，在编译llama-cpp-python时常遇到以下问题：

### 1. CUDA架构不匹配
```bash
# 错误信息
nvcc fatal: Unsupported gpu architecture 'compute_native'
CMake Error: Failed to detect a default CUDA architecture
```

### 2. CMAKE配置问题
```bash
# 错误信息
Target "ggml" links to: CUDA::cublas but the target was not found
CMAKE_CUDA_ARCHITECTURES not set correctly
```

### 3. 环境变量过时
```bash
# 旧的环境变量（不适用于新版本）
LLAMA_CUBLAS=1  # 已弃用，应使用 GGML_CUDA=1
```

## ✅ 解决方案

### 核心修复要点

1. **正确的计算能力设置**
   ```bash
   CMAKE_CUDA_ARCHITECTURES=89  # RTX 4090专用
   ```

2. **正确的环境变量**
   ```bash
   GGML_CUDA=1                    # 新版本语法
   CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=89"
   FORCE_CMAKE=1
   ```

3. **编译器兼容性**
   ```bash
   NVCC_APPEND_FLAGS="--allow-unsupported-compiler"
   CMAKE_CUDA_COMPILER_FORCED=ON
   ```

### 完整安装命令

```bash
# 卸载旧版本
pip uninstall llama-cpp-python -y

# RTX 4090专用安装
CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=89 -DCMAKE_CUDA_COMPILER_FORCED=ON" \
FORCE_CMAKE=1 \
pip install llama-cpp-python --no-cache-dir --verbose
```

### 备用安装方案

如果上述方案失败，可以尝试包含多个架构：

```bash
CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=89;86;80;75" \
FORCE_CMAKE=1 \
pip install llama-cpp-python --no-cache-dir
```

## 🔧 自动化修复脚本

已创建 `fix_cuda_rtx4090.py` 脚本，自动处理所有兼容性问题：

```bash
python3 fix_cuda_rtx4090.py
```

该脚本会：
- 检测RTX 4090 GPU
- 设置正确的环境变量
- 卸载并重新编译llama-cpp-python
- 验证安装是否成功

## 📊 RTX 4090优化配置

### 推荐模型参数

```python
# RTX 4090有24GB显存，可以使用更激进的配置
rtx4090_config = {
    'n_gpu_layers': 50-60,    # 大部分层放到GPU
    'n_ctx': 16384-32768,     # 大上下文支持
    'use_mmap': True,
    'use_mlock': False,
    'low_vram': False,        # RTX 4090不需要低显存模式
}
```

### 不同模型的建议配置

| 模型 | n_gpu_layers | n_ctx | 备注 |
|------|-------------|-------|------|
| L3.2-8X3B | 50 | 16384 | 较大模型，保守配置 |
| L3.2-8X4B | 45 | 8192 | 最大模型，需要保守 |
| 其他小模型 | 60 | 32768 | 可以更激进 |

## 🐳 Docker支持

已创建 `Dockerfile.rtx4090` 专门支持RTX 4090：

```bash
# 构建RTX 4090专用镜像
docker build -f Dockerfile.rtx4090 -t llama-rtx4090 .

# 运行RTX 4090容器
docker run --gpus all -p 8000:8000 llama-rtx4090
```

## ✨ 预期性能提升

成功配置后，RTX 4090应该能提供：

- **推理速度**: 50-150 tokens/秒（取决于模型大小）
- **显存利用**: 18-22GB（接近满载）
- **GPU利用率**: 90%+
- **加载时间**: 5-15秒（模型大小决定）

## 🔍 故障排除

### 常见错误及解决方案

1. **"compute_native" not supported**
   - 解决：设置 `CMAKE_CUDA_ARCHITECTURES=89`

2. **CUDA::cublas not found**
   - 解决：确保安装了完整的CUDA Toolkit

3. **GPU layers = 0**
   - 解决：运行 `fix_cuda_rtx4090.py` 重新编译

4. **内存不足错误**
   - 解决：减少 `n_gpu_layers` 或 `n_ctx`

### 验证GPU使用

```python
import llama_cpp
model = llama_cpp.Llama(
    model_path="your_model.gguf",
    n_gpu_layers=50,
    verbose=True
)
# 应该看到 "assigned to device CUDA:0" 的消息
```

## 📈 性能监控

使用以下命令监控RTX 4090性能：

```bash
# GPU监控
nvidia-smi -l 1

# 详细GPU信息
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv -l 1
```

## 🎯 总结

RTX 4090的主要兼容性问题源于其新的Ada Lovelace架构（计算能力8.9）。通过：

1. 使用正确的 `CMAKE_CUDA_ARCHITECTURES=89`
2. 更新环境变量为 `GGML_CUDA=1`
3. 强制重新编译llama-cpp-python
4. 优化GPU配置参数

可以完美解决兼容性问题，充分发挥RTX 4090的24GB显存和强大计算能力。 