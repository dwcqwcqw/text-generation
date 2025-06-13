# Cloudflare Pages 配置说明

由于 wrangler.toml 对 Pages 项目的支持有限，请在 Cloudflare Dashboard 中手动配置以下设置：

## 项目配置

### 构建设置
- **框架预设**: None
- **构建命令**: `./build.sh`
- **构建输出目录**: `frontend/out`
- **根目录**: `/` (默认)

### 环境变量
在 Settings > Environment variables 中添加：

#### Production 环境
```
NODE_VERSION=18
NEXT_PUBLIC_API_URL=https://api-text-generation.runpod.app
NEXT_PUBLIC_R2_BUCKET=text-generation
```

#### Preview 环境（可选）
```
NODE_VERSION=18
NEXT_PUBLIC_API_URL=https://preview-api-text-generation.runpod.app
NEXT_PUBLIC_R2_BUCKET=text-generation-preview
```

## 部署流程

1. 推送代码到 GitHub
2. Cloudflare Pages 会自动检测更改
3. 使用配置的构建命令进行构建
4. 部署到全球 CDN

## 注意事项

- 确保 `build.sh` 有执行权限
- Next.js 配置了静态导出（`output: 'export'`）
- 重定向规则在 `frontend/public/_redirects` 中配置 