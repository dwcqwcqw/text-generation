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
    echo ""
    echo "🔗 API 端点："
    echo "   Worker URL: https://text-generation-api.YOUR_SUBDOMAIN.workers.dev"
    echo ""
    echo "📝 请在 Cloudflare Pages 环境变量中设置:"
    echo "   NEXT_PUBLIC_API_URL=https://text-generation-api.YOUR_SUBDOMAIN.workers.dev"
    echo ""
    echo "🎯 支持的 API 端点："
    echo "   POST /speech/stt     - 语音转文字"
    echo "   POST /speech/tts     - 文字转语音"
    echo "   POST /chat/save      - 保存聊天记录"
    echo "   GET  /chat/load/{id} - 加载聊天记录"
    echo "   GET  /health         - 健康检查"
    echo ""
    echo "⚠️  注意：请将 YOUR_SUBDOMAIN 替换为你实际的 Workers 子域名"
else
    echo "❌ 部署失败"
    exit 1
fi 