#!/bin/bash

# 测试部署配置脚本

set -e

echo "🧪 Testing deployment configuration..."

# 测试是否移除了wrangler.toml（推荐做法）
echo "📋 Checking wrangler.toml..."
if [ -f "wrangler.toml" ]; then
    echo "⚠️  wrangler.toml exists (may cause issues with Pages)"
    echo "   Recommend configuring build settings in Cloudflare Dashboard instead"
else
    echo "✅ wrangler.toml not found (good for Pages deployment)"
fi

# 检查配置文档
echo "📋 Checking configuration documentation..."
if [ -f "cloudflare-pages-config.md" ]; then
    echo "✅ Configuration documentation exists"
else
    echo "❌ Configuration documentation missing"
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
    
    # 检查是否使用了有问题的依赖
    if grep -q "llama-cpp-python" runpod/requirements.txt; then
        echo "⚠️  llama-cpp-python detected (may cause build issues)"
    else
        echo "✅ No problematic dependencies detected"
    fi
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
echo "   Frontend: Configure in Cloudflare Pages Dashboard (see cloudflare-pages-config.md)"
echo "   Backend: Build Docker image and deploy to RunPod"
echo ""
echo "📖 Next steps:"
echo "   1. Push code to GitHub"
echo "   2. Configure Cloudflare Pages settings manually"
echo "   3. Deploy backend to RunPod" 