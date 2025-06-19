# 后端API设置说明

## 问题说明

你遇到的错误 `https://api-text-generation.runpod.app` 404错误是因为这个地址不存在。这个项目有两个不同的API：

1. **RunPod Serverless API** (AI推理) - ✅ 正确配置
   - 地址: `https://api.runpod.ai/v2/4cx6jtjdx6hdhr/runsync`
   - 用途: AI模型推理和对话生成

2. **Backend API** (聊天历史管理) - ❌ 需要部署
   - 用途: 保存/加载聊天历史到你的R2存储

## 你提供的正确信息

- **R2 S3 API**: `https://c7c141ce43d175e60601edc46d904553.r2.cloudflarestorage.com/text-generation`
- **Public Development URL**: `https://pub-f314a707297b4748936925bba8dd4962.r2.dev`
- **Access Key**: `5885b29961ce9fc2b593139d9de52f81`
- **Secret Key**: `a4415c670e669229db451ea7b38544c0a2e44dbe630f1f35f99f28a27593d181`

## 解决方案

### 方案1: 部署Cloudflare Workers API (推荐)

1. **安装Wrangler CLI**:
   ```bash
   npm install -g wrangler
   ```

2. **登录Cloudflare**:
   ```bash
   wrangler login
   ```

3. **部署API**:
   ```bash
   ./deploy-api.sh
   ```

4. **获取Worker URL** (类似于):
   ```
   https://text-generation-api.你的用户名.workers.dev
   ```

5. **更新前端配置**:
   在Cloudflare Pages环境变量中设置:
   ```
   NEXT_PUBLIC_API_URL=https://text-generation-api.你的用户名.workers.dev
   ```

### 方案2: 临时使用本地存储

如果暂时不想部署后端，前端已经配置了本地存储备份机制：

1. 聊天历史会自动保存到浏览器本地存储
2. 页面刷新后会自动恢复
3. 功能基本完整，只是没有云端备份

## 文件说明

- `cloudflare-api-worker.js` - Cloudflare Workers API代码
- `wrangler-api.toml` - Workers配置文件
- `deploy-api.sh` - 部署脚本
- `backend/main.py` - FastAPI版本（如果需要部署到其他平台）

## R2存储配置

后端API已经正确配置了你提供的R2凭据：
- Endpoint: `https://c7c141ce43d175e60601edc46d904553.r2.cloudflarestorage.com`
- Bucket: `text-generation`
- Access Key: `5885b29961ce9fc2b593139d9de52f81`
- Secret Key: `a4415c670e669229db451ea7b38544c0a2e44dbe630f1f35f99f28a27593d181`

## 当前状态

- ✅ RunPod AI API: 正常工作
- ✅ R2存储配置: 已正确设置
- ✅ 前端本地存储: 作为备份方案
- ⚠️ 后端API: 需要部署

部署后端API后，聊天历史将自动同步到你的R2存储。 