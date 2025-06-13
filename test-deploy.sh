#!/bin/bash

# 测试部署配置脚本

set -e

echo "🧪 Testing deployment configuration..."

# 测试wrangler.toml格式
echo "📋 Checking wrangler.toml..."
if [ -f "wrangler.toml" ]; then
    echo "✅ wrangler.toml exists"
    # 检查关键配置
    if grep -q "pages_build_output_dir" wrangler.toml; then
        echo "✅ pages_build_output_dir found"
    else
        echo "❌ pages_build_output_dir missing"
        exit 1
    fi
else
    echo "❌ wrangler.toml not found"
    exit 1
fi

# 测试构建脚本
echo "📋 Checking build script..."
if [ -f "build.sh" ] && [ -x "build.sh" ]; then
    echo "✅ build.sh exists and is executable"
else
    echo "❌ build.sh missing or not executable"
    exit 1
fi

# 测试前端目录
echo "📋 Checking frontend structure..."
if [ -d "frontend" ]; then
    echo "✅ frontend directory exists"
    if [ -f "frontend/package.json" ]; then
        echo "✅ package.json exists"
    else
        echo "❌ frontend/package.json missing"
        exit 1
    fi
else
    echo "❌ frontend directory missing"
    exit 1
fi

# 测试Docker配置
echo "📋 Checking Docker configuration..."
if [ -f "Dockerfile" ]; then
    echo "✅ Dockerfile exists"
else
    echo "❌ Dockerfile missing"
    exit 1
fi

if [ -f "runpod/requirements.txt" ]; then
    echo "✅ requirements.txt exists"
else
    echo "❌ runpod/requirements.txt missing"
    exit 1
fi

# 检查functions目录是否存在（应该不存在）
if [ -d "functions" ]; then
    echo "⚠️  functions directory exists (should be removed for static site)"
else
    echo "✅ functions directory removed (correct for static site)"
fi

echo "🎉 All deployment configuration checks passed!"
echo ""
echo "🚀 Ready for deployment:"
echo "   Frontend: Push to GitHub, auto-deployed to Cloudflare Pages"
echo "   Backend: Build Docker image and deploy to RunPod" 