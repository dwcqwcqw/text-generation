# RunPod 后端部署指南

## 问题诊断
当前错误：`/usr/local/bin/python: No module named runpod.serverless.start`

这个错误表明你的RunPod worker正在使用旧的handler代码。

## 解决方案

### 1. 下载新的后端文件
从GitHub下载最新的runpod文件夹：
```bash
# 克隆或下载这些文件：
runpod/handler_llama.py     # 新的Llama GGUF handler
runpod/requirements.txt     # 更新的依赖项
runpod/Dockerfile          # Docker配置
```

### 2. 更新RunPod Serverless Function

#### 方法A: 通过RunPod控制台
1. 登录 [RunPod控制台](https://www.runpod.io/console/serverless)
2. 找到你的endpoint: `4cx6jtjdx6hdhr`
3. 点击 "Edit" 或 "Update"
4. 上传新的 `handler_llama.py` 文件替换原来的handler
5. 确保requirements.txt包含：
   ```
   runpod>=1.6.0
   llama-cpp-python>=0.2.11
   torch>=2.0.1
   numpy
   ```

#### 方法B: 重新创建Function
1. 创建新的Serverless Function
2. 选择适当的GPU (建议RTX 4090或A100)
3. 上传 `handler_llama.py` 作为main handler
4. 设置环境变量（如果需要）
5. 部署并获取新的endpoint ID

### 3. 确保模型文件存在
确认以下路径的模型文件存在：
- `/runpod-volume/text_models/L3.2-8X3B.gguf`
- `/runpod-volume/text_models/L3.2-8X4B.gguf`

### 4. 测试API
使用前端的测试页面 `/test` 来验证连接：
- 输入正确的API Key: `rpa_YT0BFBFZYAZMQHR231H4DOKQEOAJXSMVIBDYN4ZQ1tdxlb`
- 选择模型进行测试
- 查看详细的错误信息

## handler_llama.py 关键特性
新的handler支持：
- ✅ GGUF格式的Llama模型
- ✅ 严格的模型验证（只允许指定的两个模型）
- ✅ 适当的提示格式化
- ✅ 错误处理和日志记录
- ✅ RunPod serverless兼容性

## 如果仍有问题
1. 检查RunPod logs查看详细错误
2. 确认GPU内存足够加载模型
3. 验证模型文件路径和权限
4. 考虑重新上传模型文件

## 当前状态分析
根据测试结果：
- ✅ Endpoint健康检查通过
- ✅ 有2个idle和2个ready workers
- ❌ API请求返回"IN_QUEUE"状态
- ❌ 请求超时

这通常意味着worker启动了但处理请求时失败，很可能是因为使用了错误的handler代码。 