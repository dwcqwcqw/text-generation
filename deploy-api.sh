#!/bin/bash

echo "🚀 部署AI聊天后端API到Cloudflare Workers..."

# 检查wrangler是否安装
if ! command -v wrangler &> /dev/null; then
    echo "❌ Wrangler CLI未安装，请先安装："
    echo "npm install -g wrangler"
    exit 1
fi

# 检查登录状态
if ! wrangler whoami &> /dev/null; then
    echo "❌ 请先登录Cloudflare:"
    echo "wrangler login"
    exit 1
fi

# 部署到生产环境
echo "📦 部署API Worker..."
wrangler deploy --config wrangler-api.toml --env production

if [ $? -eq 0 ]; then
    echo "✅ API部署成功！"
    echo "🔗 API地址将会是: https://text-generation-api.your-domain.workers.dev"
    echo ""
    echo "📝 请更新前端配置中的NEXT_PUBLIC_API_URL变量"
    echo "   在Cloudflare Pages环境变量中设置:"
    echo "   NEXT_PUBLIC_API_URL=https://text-generation-api.your-domain.workers.dev"
else
    echo "❌ 部署失败"
    exit 1
fi 