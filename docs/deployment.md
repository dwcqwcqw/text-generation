# 部署指南

本文档介绍如何部署AI聊天应用到各个服务平台。

## 前端部署 (Cloudflare Pages)

### 自动部署 (推荐)
1. 将代码推送到GitHub仓库
2. 在Cloudflare Dashboard中创建新的Pages项目
3. 连接GitHub仓库：`https://github.com/dwcqwcqw/text-generation.git`
4. 配置构建设置：
   - 框架预设：`Next.js`
   - 构建命令：`cd frontend && npm run build`
   - 构建输出目录：`frontend/out`
   - 根目录：`/`

### 环境变量设置
在Cloudflare Pages项目设置中添加：
```
NEXT_PUBLIC_API_URL=https://your-api-domain.com
NEXT_PUBLIC_R2_BUCKET=text-generation
```

### 手动部署
```bash
cd frontend
npm install
npm run build
# 上传 frontend/out 目录到Cloudflare Pages
```

## 后端API部署

### 使用Docker部署
```bash
cd backend
docker build -t ai-chat-api .
docker run -p 8000:8000 --env-file config.env ai-chat-api
```

### 直接部署
```bash
cd backend
pip install -r requirements.txt
# 复制 config.env.example 到 config.env 并配置环境变量
uvicorn main:app --host 0.0.0.0 --port 8000
```

## RunPod Serverless部署

### 准备模型文件
1. 在RunPod中创建一个持久存储卷
2. 将模型文件上传到：
   - `/runpod-volume/text_models/L3.2-8X3B.gguf`
   - `/runpod-volume/text_models/L3.2-8X4B.gguf`

### 部署Serverless函数
1. 构建Docker镜像：
```bash
cd runpod
docker build -t ai-chat-runpod .
```

2. 上传镜像到DockerHub或其他容器注册表

3. 在RunPod控制台创建Serverless端点：
   - 选择GPU实例类型
   - 设置容器镜像
   - 挂载持久存储卷到 `/runpod-volume`
   - 配置环境变量

### RunPod端点配置
- **容器镜像**: `your-registry/ai-chat-runpod:latest`
- **GPU类型**: RTX 4090 或更高
- **最小副本数**: 0 (按需启动)
- **最大副本数**: 5
- **空闲超时**: 300秒

## Cloudflare R2存储配置

### 创建R2存储桶
1. 登录Cloudflare Dashboard
2. 导航到 R2 Object Storage
3. 创建新存储桶：`text-generation`
4. 配置CORS策略：
```json
[
  {
    "AllowedOrigins": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    "AllowedHeaders": ["*"],
    "ExposedHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
  }
]
```

### 获取访问密钥
1. 在R2设置中创建API令牌
2. 记录以下信息：
   - Access Key ID
   - Secret Access Key
   - S3 API端点URL

## 环境变量配置

### 后端API环境变量
```bash
# RunPod配置
RUNPOD_API_KEY=your_runpod_api_key
RUNPOD_ENDPOINT=https://api.runpod.ai/v2/your-endpoint/runsync

# Cloudflare R2配置
CLOUDFLARE_ACCESS_KEY=your_access_key
CLOUDFLARE_SECRET_KEY=your_secret_key
S3_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
R2_BUCKET=text-generation
```

### GitHub Secrets配置
在GitHub仓库设置中添加以下Secrets：
- `CLOUDFLARE_API_TOKEN`: Cloudflare API令牌
- `CLOUDFLARE_ACCOUNT_ID`: Cloudflare账户ID
- `RUNPOD_API_KEY`: RunPod API密钥
- `API_URL`: 后端API的URL

## 验证部署

### 检查前端
1. 访问Cloudflare Pages URL
2. 验证聊天界面加载正常
3. 测试模型切换功能

### 检查后端API
```bash
curl https://your-api-domain.com/health
```

### 检查RunPod端点
```bash
curl -X POST https://api.runpod.ai/v2/your-endpoint/runsync \
  -H "Authorization: Bearer your_runpod_api_key" \
  -H "Content-Type: application/json" \
  -d '{"input": {"prompt": "Hello, how are you?", "model_path": "/runpod-volume/text_models/L3.2-8X3B.gguf"}}'
```

## 故障排除

### 常见问题
1. **前端无法连接后端**: 检查CORS配置和API URL
2. **模型加载失败**: 验证模型文件路径和权限
3. **R2存储错误**: 检查访问密钥和存储桶配置
4. **RunPod超时**: 增加GPU实例或优化模型加载

### 日志查看
- **前端**: 浏览器开发者工具
- **后端**: 服务器日志或Docker容器日志
- **RunPod**: RunPod控制台日志

## 监控和维护

### 性能监控
- 监控API响应时间
- 跟踪RunPod GPU使用率
- 观察R2存储使用量

### 定期维护
- 更新依赖包
- 清理旧的聊天记录
- 优化模型缓存策略 