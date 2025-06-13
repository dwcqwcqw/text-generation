# AI Text Generation Chat Application

基于 Llama 3.2 模型的AI聊天应用，支持多模型切换。

## 架构

- **前端**: Next.js + React，部署到 Cloudflare Pages
- **后端**: Python FastAPI，部署到 RunPod Serverless
- **存储**: Cloudflare R2 用于聊天记录存储
- **模型**: Llama 3.2 MOE models (8X3B 和 8X4B)

## 项目结构

```
├── frontend/           # Next.js 前端应用
├── backend/           # FastAPI 后端API
├── runpod/           # RunPod serverless 处理程序
├── .github/          # GitHub Actions 自动部署
└── docs/             # 文档
```

## 模型支持

- **L3.2-8X3B**: Llama-3.2-8X3B-MOE-Dark-Champion (18.4B参数)
- **L3.2-8X4B**: Llama-3.2-8X4B-MOE-V2-Dark-Champion (21B参数)

## 部署

### 自动部署
推送到 GitHub 主分支将自动触发：
- 前端部署到 Cloudflare Pages
- 后端部署到 RunPod Serverless

### 环境变量
确保在相应平台设置以下环境变量：
- RunPod API Key
- Cloudflare R2 访问密钥
- 其他配置参数

## 开发

```bash
# 前端开发
cd frontend
npm install
npm run dev

# 后端开发
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## 功能特性

- 💬 实时聊天界面
- 🔄 多模型切换
- 💾 聊天记录持久化
- �� GPU加速推理
- 📱 响应式设计 