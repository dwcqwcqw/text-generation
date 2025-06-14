#!/bin/bash
set -e

echo "🚀 Cloudflare Pages构建脚本"
echo "📍 当前目录: $(pwd)"
echo "📂 目录内容:"
ls -la

# 检查frontend/out是否已存在
if [ -d "frontend/out" ]; then
    echo "✅ frontend/out目录已存在，使用预构建文件"
    echo "📊 构建文件统计:"
    find frontend/out -type f | wc -l | xargs echo "  - 文件数量:"
    du -sh frontend/out | xargs echo "  - 目录大小:"
    
    # 验证关键文件
    if [ -f "frontend/out/index.html" ]; then
        echo "✅ index.html存在"
    else
        echo "❌ index.html缺失"
        exit 1
    fi
    
    if [ -f "frontend/out/_redirects" ]; then
        echo "✅ _redirects存在"
    else
        echo "❌ _redirects缺失"
        exit 1
    fi
    
    echo "🎉 预构建文件验证通过！"
else
    echo "⚠️ frontend/out目录不存在，开始构建..."
    
    # 检查Node.js版本
    echo "📊 Node.js版本: $(node --version)"
    echo "📊 npm版本: $(npm --version)"
    
    # 进入前端目录
    cd frontend
    
    # 安装依赖
    echo "📦 安装依赖..."
    npm install
    
    # 构建项目
    echo "🔨 构建项目..."
    npm run build
    
    # 验证构建结果
    if [ -d "out" ]; then
        echo "✅ 构建成功！"
        echo "📊 构建文件统计:"
        find out -type f | wc -l | xargs echo "  - 文件数量:"
        du -sh out | xargs echo "  - 目录大小:"
    else
        echo "❌ 构建失败，out目录未生成"
        exit 1
    fi
    
    cd ..
fi

echo "🎉 Cloudflare Pages构建完成！" 