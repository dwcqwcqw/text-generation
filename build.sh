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
npm install

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

echo "📁 Copying build output to root dist directory..."
cd ..

# 清理并重新创建dist目录
rm -rf dist
mkdir -p dist

# 复制Next.js输出
cp -r frontend/out/* dist/

# 确保_redirects文件在正确位置
echo "📋 Copying _redirects file..."
cp _redirects dist/

# 验证dist目录内容
echo "📋 Final dist directory contents:"
ls -la dist/

echo "🎉 Ready for deployment!"

# 验证关键文件
if [ -f "dist/index.html" ]; then
    echo "✨ index.html found"
else
    echo "❌ index.html missing"
fi

if [ -f "dist/_redirects" ]; then
    echo "✨ _redirects found"
else
    echo "❌ _redirects missing"
fi

if [ -d "dist/_next" ]; then
    echo "✨ _next directory found"
else
    echo "❌ _next directory missing"
fi

echo "✨ Build verification successful!" 