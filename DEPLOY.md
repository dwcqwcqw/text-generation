# AI Text Chat 部署指南

## 🔧 最新修复方案

### 核心问题解决
1. **移除 wrangler.toml**：Cloudflare Pages 对 wrangler.toml 的支持有限，改为在 Dashboard 手动配置
2. **替换 llama-cpp-python**：使用 transformers 库避免编译问题
3. **简化依赖管理**：使用预编译的 wheel 包

## 🚀 部署流程

### 1. 前端部署到 Cloudflare Pages

#### 步骤1：推送代码
```bash
git add .
git commit -m "最终修复：移除wrangler.toml，替换llama-cpp-python"
git push origin main
```

#### 步骤2：配置 Cloudflare Pages
在 Cloudflare Dashboard > Pages > 项目设置中配置：

**构建设置:**
- 框架预设: `None`
- 构建命令: `./build.sh`
- 构建输出目录: `frontend/out`
- 根目录: `/`

**环境变量:**
```
NODE_VERSION=18
NEXT_PUBLIC_API_URL=https://api-text-generation.runpod.app
NEXT_PUBLIC_R2_BUCKET=text-generation
```

### 2. 后端部署到 RunPod

#### 已修复的问题
- ✅ 移除了需要编译的 llama-cpp-python
- ✅ 使用 transformers + PyTorch CPU 版本
- ✅ 简化了 Docker 配置

#### 部署方法
```bash
# RunPod 会自动从 GitHub 构建
# 使用根目录的 Dockerfile
```

## 📋 关键配置文件

### Dockerfile
```dockerfile
FROM python:3.10-slim

# 安装必要的系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖 (无编译问题)
COPY runpod/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY runpod/handler.py .
CMD ["python", "-m", "runpod.serverless.start", "--handler_file", "handler.py"]
```

### requirements.txt
```
runpod==1.5.1
transformers==4.35.2
torch==2.0.1+cpu -f https://download.pytorch.org/whl/torch_stable.html
numpy==1.24.3
fastapi==0.103.2
uvicorn==0.23.2
pydantic==2.4.2
python-multipart==0.0.6
requests==2.31.0
```

### handler.py 更新
- 使用 transformers 的 AutoModelForCausalLM
- 支持多种预训练模型
- 无需编译即可运行

## 🧪 测试部署

运行测试脚本：
```bash
./test-deploy.sh
```

预期输出：
- ✅ wrangler.toml not found (good for Pages deployment)
- ✅ No problematic dependencies detected
- ✅ All configuration checks passed

## 🔗 手动配置指南

详细的 Cloudflare Pages 配置说明请查看：
- `cloudflare-pages-config.md`

## 📊 部署状态验证

### 前端验证
1. 构建完成后检查日志
2. 访问 Pages URL 确认部署成功
3. 测试聊天界面功能

### 后端验证
1. RunPod 构建日志无错误
2. 端点状态显示运行中
3. API 响应测试正常

## 🚨 故障排除

### 前端问题
- **构建失败**: 检查 build.sh 权限和路径
- **环境变量**: 确保在 Dashboard 中正确设置
- **路由问题**: 检查 _redirects 文件

### 后端问题
- **Docker 构建**: 检查 requirements.txt 格式
- **模型加载**: 确认 transformers 版本兼容性
- **内存不足**: 考虑使用更小的模型

## ✅ 部署检查清单

### 准备阶段
- [ ] 移除了 wrangler.toml
- [ ] 更新了 requirements.txt (无 llama-cpp-python)
- [ ] 修改了 handler.py 使用 transformers
- [ ] 确保 build.sh 可执行

### 前端部署
- [ ] 代码推送到 GitHub
- [ ] Cloudflare Pages 手动配置完成
- [ ] 环境变量设置正确
- [ ] 构建成功无错误

### 后端部署
- [ ] Dockerfile 配置正确
- [ ] RunPod 构建成功
- [ ] 端点运行正常
- [ ] API 测试通过

## 🎯 预期结果

完成配置后，应该实现：
1. **前端**: Cloudflare Pages 自动构建和部署
2. **后端**: RunPod 成功构建并运行 AI 模型
3. **整合**: 前后端正常通信，聊天功能完整

## 🚀 最终状态

- ❌ **旧方案**: wrangler.toml + llama-cpp-python（编译失败）
- ✅ **新方案**: Dashboard 配置 + transformers（预编译）

🎉 **这次修复应该能彻底解决部署问题！** 