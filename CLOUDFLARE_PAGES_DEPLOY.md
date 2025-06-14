# 🚀 Cloudflare Pages部署指南

## 📋 部署配置

### 方案1：使用预构建文件（推荐）

由于仓库已包含预构建的`frontend/out`目录，Cloudflare Pages可以直接使用：

**构建设置：**
- **构建命令**: `./cloudflare-build.sh` 或留空
- **构建输出目录**: `frontend/out`
- **根目录**: `/`（默认）

### 方案2：动态构建

如果需要动态构建，使用以下配置：

**构建设置：**
- **构建命令**: `cd frontend && npm install && npm run build`
- **构建输出目录**: `frontend/out`
- **根目录**: `/`（默认）

## 🔧 环境变量配置

在Cloudflare Pages项目设置中添加以下环境变量：

```bash
NODE_VERSION=18
NEXT_PUBLIC_API_URL=https://api-text-generation.runpod.app
NEXT_PUBLIC_R2_BUCKET=text-generation
```

## 📊 部署验证

部署成功后，应该看到：

### 1. 构建日志
```
✅ frontend/out目录已存在，使用预构建文件
📊 构建文件统计:
  - 文件数量: 27
  - 目录大小: 1.1M frontend/out
✅ index.html存在
✅ _redirects存在
🎉 预构建文件验证通过！
```

### 2. 前端功能验证
- ✅ 左下角只显示两个模型选项：
  - L3.2-8X3B.gguf
  - L3.2-8X4B.gguf
- ✅ 没有"中文助手"等旧模型
- ✅ 聊天界面正常工作
- ✅ API连接正常

## 🔍 故障排除

### 问题1：Output directory "frontend/out" not found

**解决方案：**
1. 确保仓库包含`frontend/out`目录
2. 检查`.gitignore`是否正确配置
3. 使用构建命令：`./cloudflare-build.sh`

### 问题2：构建失败

**解决方案：**
1. 检查Node.js版本设置：`NODE_VERSION=18`
2. 确保package.json存在
3. 检查构建脚本权限：`chmod +x cloudflare-build.sh`

### 问题3：前端显示错误的模型

**解决方案：**
1. 清除Cloudflare缓存
2. 检查构建文件是否包含正确的模型定义
3. 重新部署

## 📁 文件结构

部署后的文件结构：
```
frontend/out/
├── index.html          # 主页面
├── _redirects          # 路由重定向
├── _next/              # Next.js静态资源
│   ├── static/
│   │   ├── chunks/     # JavaScript代码块
│   │   └── css/        # 样式文件
├── debug/              # 调试页面
├── test/               # 测试页面
└── 404.html           # 404错误页面
```

## 🎯 性能优化

### 1. 缓存配置
Cloudflare Pages自动配置缓存，静态资源会被缓存。

### 2. 压缩
所有静态文件都经过压缩优化。

### 3. CDN
通过Cloudflare全球CDN分发，提供快速访问。

## 🔗 相关链接

- [Cloudflare Pages文档](https://developers.cloudflare.com/pages/)
- [Next.js静态导出](https://nextjs.org/docs/app/building-your-application/deploying/static-exports)
- [项目GitHub仓库](https://github.com/dwcqwcqw/text-generation)

## 📞 支持

如果部署遇到问题，请检查：
1. 构建日志中的错误信息
2. 环境变量是否正确设置
3. 构建输出目录是否正确
4. 前端功能是否正常

部署成功后，你的AI聊天应用将通过Cloudflare Pages提供服务，具有高可用性和全球CDN加速。 