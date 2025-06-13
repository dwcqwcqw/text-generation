# AI Text Chat 部署指南

## 🔧 已修复的问题

### 前端部署问题
- ✅ **修复 wrangler.toml 配置**：使用正确的 Cloudflare Pages 配置格式
- ✅ **添加 pages_build_output_dir**：指定构建输出目录
- ✅ **移除 functions 目录**：避免路由检测错误
- ✅ **优化构建脚本**：添加错误处理和环境变量设置

### 后端部署问题  
- ✅ **修复 Docker 构建**：添加 ninja-build 工具
- ✅ **简化依赖管理**：使用 CPU 版本避免编译错误
- ✅ **优化基础镜像**：使用 python:3.10-slim

## 🚀 部署流程

### 1. 前端部署到 Cloudflare Pages

```bash
# 推送到 GitHub，自动触发部署
git add .
git commit -m "Fix deployment configuration"
git push origin main
```

**配置说明：**
- wrangler.toml 使用正确的 Pages 配置格式
- 构建命令：`./build.sh`
- 输出目录：`frontend/out`
- 重定向规则：`/*  /  200`

### 2. 后端部署到 RunPod

#### 方法1：自动构建（推荐）
```bash
# RunPod 会自动从 GitHub 仓库构建
# 确保 Dockerfile 在根目录
```

#### 方法2：本地构建上传
```bash
# 构建 Docker 镜像
docker build -t text-generation-api .

# 推送到 Docker Hub
docker tag text-generation-api your-dockerhub/text-generation-api
docker push your-dockerhub/text-generation-api
```

## 📋 关键配置文件

### wrangler.toml
```toml
name = "text-generation-chat"
compatibility_date = "2024-01-15"

# Cloudflare Pages配置
pages_build_output_dir = "frontend/out"

[build]
command = "./build.sh"
cwd = "."

[env.production.vars]
NODE_VERSION = "18"
NEXT_PUBLIC_API_URL = "https://api-text-generation.runpod.app"
NEXT_PUBLIC_R2_BUCKET = "text-generation"
```

### Dockerfile
```dockerfile
FROM python:3.10-slim

# 安装构建工具（包括 ninja-build）
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖（CPU 版本）
COPY runpod/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY runpod/handler.py .
CMD ["python", "-m", "runpod.serverless.start", "--handler_file", "handler.py"]
```

## 🧪 测试部署

运行测试脚本验证配置：
```bash
./test-deploy.sh
```

## 🔗 API 密钥配置

确保在相应平台配置以下密钥：

### Cloudflare Pages 环境变量
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_R2_BUCKET`

### RunPod 环境变量
- `RUNPOD_API_KEY`
- `CLOUDFLARE_R2_*` 配置

## 📊 部署状态监控

### 前端
- Cloudflare Pages 控制台：https://dash.cloudflare.com/
- 构建日志可在 Pages 项目中查看

### 后端  
- RunPod 控制台：https://www.runpod.io/
- 查看 Serverless 端点状态和日志

## 🚨 常见问题

### 前端构建失败
1. 检查 `wrangler.toml` 格式
2. 确保 `build.sh` 有执行权限
3. 验证 Node.js 版本兼容性

### 后端构建失败
1. 确保 Docker 文件包含所有必要工具
2. 检查 `requirements.txt` 依赖版本
3. 验证 RunPod 构建日志

### 运行时错误
1. 检查环境变量配置
2. 验证 API 密钥设置
3. 查看应用日志

## ✅ 部署检查清单

- [ ] GitHub 仓库已更新
- [ ] wrangler.toml 配置正确
- [ ] build.sh 可执行
- [ ] Dockerfile 包含 ninja-build
- [ ] requirements.txt 使用 CPU 版本
- [ ] 环境变量已配置
- [ ] functions 目录已移除
- [ ] 测试脚本通过

🎉 **所有配置已优化，现在应该可以成功部署！** 