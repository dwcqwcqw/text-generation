#!/bin/bash

# Cloudflare Pages Build Script for AI Chat Application

set -e

echo "🚀 Starting build process..."

# 设置Node.js版本
export NODE_VERSION="18"

# 设置环境变量
export NEXT_PUBLIC_API_URL="https://api-text-generation.runpod.app"
export NEXT_PUBLIC_R2_BUCKET="text-generation"

echo "📍 Current directory: $(pwd)"
echo "📂 Directory contents:"
ls -la

# 检查并进入前端目录
if [ ! -d "frontend" ]; then
    echo "❌ Frontend directory not found!"
    echo "📂 Available directories:"
    ls -la
    exit 1
fi

echo "📁 Entering frontend directory..."
cd frontend

echo "📦 Installing dependencies..."
npm ci --prefer-offline --no-audit

echo "🏗️ Building Next.js application..."
npm run build

# 检查构建输出
if [ ! -d "out" ]; then
    echo "❌ Build output directory not found!"
    echo "📂 Frontend directory contents:"
    ls -la
    exit 1
fi

echo "✅ Build completed successfully!"

# 返回根目录
cd ..

echo "📁 Copying build output to root dist directory..."
# 清理并创建 dist 目录
rm -rf dist
cp -R frontend/out dist

echo "📋 Final dist directory contents:"
ls -la dist/

echo "🎉 Ready for deployment!"

# 确保输出目录存在且有内容
if [ ! "$(ls -A dist)" ]; then
    echo "❌ Dist directory is empty!"
    exit 1
fi

echo "✨ Build verification successful!" 