# GPU-Only 模式使用指南

## 概述

这个指南介绍了如何在RunPod上使用强制GPU模式运行Llama模型。与之前的保守模式不同，这个版本强制使用GPU，不会回退到CPU模式。

## 为什么使用GPU-Only模式？

从日志分析来看，之前的模型已经能够在CPU模式下成功加载并运行，但是：

1. 推理速度较慢（约28秒生成一个响应）
2. 没有利用到L4 GPU的强大性能
3. 使用了超保守的设置（n_ctx=256, n_batch=32, n_gpu_layers=0）

GPU-Only模式的优势：
1. 大幅提高推理速度
2. 充分利用L4 GPU的22.5GB显存
3. 使用更大的上下文窗口和批处理大小

## 部署步骤

### 1. 部署GPU-Only版本

```bash
./deploy_gpu_only.sh <endpoint_id>
```

例如：
```bash
./deploy_gpu_only.sh 4cx6jtjdx6hdhr
```

### 2. 在RunPod上完成部署

登录到RunPod并运行：
```bash
cd gpu_only
./deploy.sh
```

### 3. 重新构建Docker镜像

在RunPod控制台中：
1. 停止当前endpoint
2. 重新构建Docker镜像
3. 启动endpoint

## 关键优化

GPU-Only版本包含以下关键优化：

1. **强制GPU模式**：
   - 设置n_gpu_layers=50（大量GPU层）
   - 不回退到CPU模式

2. **增大参数**：
   - 上下文窗口：4096（之前为256）
   - 批处理大小：512（之前为32）
   - 最大输出标记：1024（之前较小）

3. **CUDA优化**：
   - 指定L4 GPU的计算能力：89
   - 强制使用CUDA：LLAMA_CUBLAS=1

## 故障排除

如果遇到问题，可以尝试以下步骤：

### 1. 检查GPU是否正确检测

运行以下命令检查GPU：
```bash
nvidia-smi
```

### 2. 测试模型加载

运行测试脚本：
```bash
python test_load_only.py
```

### 3. 常见错误及解决方案

#### CUDA错误

错误：`CUDA error: no kernel image is available for execution on the device`

解决方案：
- 确保指定了正确的计算能力：`CMAKE_CUDA_ARCHITECTURES=89`
- 重新编译llama-cpp-python：
  ```bash
  CMAKE_ARGS="-DLLAMA_CUBLAS=on -DCMAKE_CUDA_ARCHITECTURES=89" FORCE_CMAKE=1 pip install llama-cpp-python==0.3.9 --no-cache-dir --force-reinstall
  ```

#### 内存错误

错误：`RuntimeError: CUDA out of memory`

解决方案：
- 减少GPU层数：将n_gpu_layers从50降低到30或更低
- 减小上下文窗口：将n_ctx从4096降低到2048或更低
- 减小批处理大小：将n_batch从512降低到256或更低

## 性能对比

| 模式 | 推理时间 | 上下文窗口 | GPU层数 |
|------|---------|-----------|--------|
| CPU模式 | ~28秒 | 256 | 0 |
| GPU-Only模式 | 预计~3-5秒 | 4096 | 50 |

## 结论

GPU-Only模式能够充分发挥L4 GPU的性能，大幅提高推理速度。虽然这种模式可能会在某些情况下出现错误，但通过适当的参数调整，应该能够在大多数情况下稳定运行。 