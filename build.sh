#!/bin/bash

# Cloudflare Pages Build Script for AI Chat Application

set -e

echo "🚀 Starting build process..."

# 设置Node.js版本
export NODE_VERSION="18"

# 设置环境变量
export NEXT_PUBLIC_API_URL="https://api-text-generation.runpod.app"
export NEXT_PUBLIC_R2_BUCKET="text-generation"

# 检查并进入前端目录
if [ ! -d "frontend" ]; then
    echo "❌ Frontend directory not found!"
    exit 1
fi

cd frontend

echo "📦 Installing dependencies..."
npm ci --prefer-offline --no-audit

echo "🏗️ Building Next.js application..."
npm run build

# 检查构建输出
if [ ! -d "out" ]; then
    echo "❌ Build output directory not found!"
    exit 1
fi

echo "✅ Build completed successfully!"

# 返回根目录
cd ..

echo "📁 Build output is in frontend/out/"
echo "🎉 Ready for deployment!"

# 列出输出目录内容以便调试
echo "📋 Output directory contents:"
ls -la frontend/out/ 