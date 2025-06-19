# 🚀 Cloudflare Pages 部署设置指南

## 📋 构建配置

由于 `wrangler.toml` 文件不支持 Pages 构建配置，需要在 Cloudflare Pages 控制台中手动设置：

### 🔧 构建设置

**Build command (构建命令):**
```bash
./cf-build.sh
```

**Build output directory (构建输出目录):**
```
frontend/out
```

**Root directory (根目录):**
```
/
```

### 🌍 环境变量

在 Cloudflare Pages 控制台中设置以下环境变量：

```
NODE_VERSION = 18
NEXT_PUBLIC_API_URL = https://api-text-generation.runpod.app
NEXT_PUBLIC_R2_BUCKET = text-generation
```

## 📖 设置步骤

### 1. 进入 Cloudflare Pages 控制台
- 登录 Cloudflare Dashboard
- 选择您的项目 `text-generation-chat`

### 2. 配置构建设置
- 进入 **Settings** > **Builds & deployments**
- 点击 **Configure build**
- 设置：
  - **Framework preset**: `None`
  - **Build command**: `./cf-build.sh`
  - **Build output directory**: `frontend/out`
  - **Root directory**: `/` (保持默认)

### 3. 配置环境变量
- 在同一页面下找到 **Environment variables**
- 添加上述环境变量

### 4. 保存并重新部署
- 点击 **Save**
- 触发重新部署

## ✅ 验证

成功部署后，您应该看到：
- ✅ CSS 样式正确加载
- ✅ JavaScript 功能正常
- ✅ 页面完整渲染
- ✅ 模型选择器正常显示

## 🔍 故障排除

如果仍然有问题：
1. 检查构建日志中是否包含 `./cf-build.sh` 的执行
2. 确认文件数量应该是 30+ 个文件
3. 验证 `_headers`、`_redirects`、`_routes.json` 文件存在
4. 清除浏览器缓存并硬刷新

## 📊 预期构建日志

正确的构建应该显示：
```
🚀 Starting Cloudflare Pages build...
📦 Installing dependencies...
🔨 Building project...
✅ Build successful!
📊 Build statistics:
  - File count: 31
🎉 Build completed successfully!
``` 