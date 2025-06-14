#!/bin/bash

# Cloudflare Pages Build Script for AI Chat Application

set -e

echo "🚀 开始构建前端..."

# 设置Node.js版本
export NODE_VERSION="18"

# 设置环境变量
export NEXT_PUBLIC_API_URL="https://api-text-generation.runpod.app"
export NEXT_PUBLIC_R2_BUCKET="text-generation"

echo "📍 当前目录: $(pwd)"
echo "📂 目录内容:"
ls -la

# 检查并进入前端目录
if [ ! -d "frontend" ]; then
    echo "❌ 前端目录未找到!"
    echo "📂 可用目录:"
    ls -la
    exit 1
fi

echo "📁 进入前端目录..."
cd frontend

# 安装依赖
echo "📦 安装依赖..."
npm install

# 构建项目
echo "🔨 构建项目..."
npm run build

# 验证构建结果
echo "✅ 验证构建结果..."
if [ -d "out" ]; then
    echo "✅ out目录已生成"
    ls -la out/
    
    # 检查是否只有两个模型
    if grep -r "中文助手\|llama-chinese" out/ > /dev/null 2>&1; then
        echo "❌ 发现旧模型定义"
        exit 1
    else
        echo "✅ 没有旧模型定义"
    fi
    
    # 检查新模型
    model_count=$(grep -o "L3\.2-8X[^\"]*" out/_next/static/chunks/app/page-*.js 2>/dev/null | sort | uniq | wc -l || echo "0")
    echo "📊 找到 $model_count 个模型定义"
    
    echo "🎉 构建完成！输出目录: frontend/out"
else
    echo "❌ out目录未生成"
    exit 1
fi 