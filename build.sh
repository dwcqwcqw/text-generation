#!/bin/bash

# Cloudflare Pages Build Script for AI Chat Application

set -e

echo "🚀 Starting build process..."

# 设置Node.js版本
export NODE_VERSION="18"

# 进入前端目录
cd frontend

echo "📦 Installing dependencies..."
npm install

echo "🏗️ Building Next.js application..."
npm run build

echo "✅ Build completed successfully!"

# 返回根目录
cd ..

echo "📁 Build output is in frontend/out/"
echo "🎉 Ready for deployment!" 