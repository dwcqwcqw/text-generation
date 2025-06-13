#!/bin/bash

# AI Chat Application Deployment Script

set -e

echo "🚀 Starting deployment process..."

# 函数：部署前端到Cloudflare Pages
deploy_frontend() {
    echo "📦 Building frontend..."
    cd frontend
    
    # 安装依赖
    npm install
    
    # 构建项目
    npm run build
    
    echo "✅ Frontend build completed!"
    echo "📁 Build output is in frontend/out/"
    echo "🔗 Upload the 'out' folder to Cloudflare Pages"
    
    cd ..
}

# 函数：构建后端Docker镜像
build_backend() {
    echo "🐳 Building backend Docker image..."
    cd backend
    
    # 构建Docker镜像
    docker build -t ai-chat-api .
    
    echo "✅ Backend Docker image built successfully!"
    echo "🚀 You can now deploy this image to your cloud provider"
    
    cd ..
}

# 函数：构建RunPod Docker镜像
build_runpod() {
    echo "🔥 Building RunPod serverless Docker image..."
    cd runpod
    
    # 构建Docker镜像
    docker build -t ai-chat-runpod .
    
    echo "✅ RunPod Docker image built successfully!"
    echo "📤 Push this image to a container registry for RunPod deployment"
    
    cd ..
}

# 函数：验证环境
check_environment() {
    echo "🔍 Checking environment..."
    
    # 检查Node.js
    if ! command -v node &> /dev/null; then
        echo "❌ Node.js is not installed"
        exit 1
    fi
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed"
        exit 1
    fi
    
    # 检查配置文件
    if [ ! -f "backend/config.env" ]; then
        echo "⚠️  Warning: backend/config.env not found"
        echo "📝 Please copy backend/config.env.example to backend/config.env and configure it"
    fi
    
    echo "✅ Environment check completed"
}

# 主菜单
show_menu() {
    echo ""
    echo "🤖 AI Chat Application Deployment"
    echo "================================="
    echo "1. Check environment"
    echo "2. Deploy frontend (build only)"
    echo "3. Build backend Docker image"
    echo "4. Build RunPod Docker image"
    echo "5. Build all components"
    echo "6. Exit"
    echo ""
}

# 主循环
while true; do
    show_menu
    read -p "Select an option (1-6): " choice
    
    case $choice in
        1)
            check_environment
            ;;
        2)
            deploy_frontend
            ;;
        3)
            build_backend
            ;;
        4)
            build_runpod
            ;;
        5)
            check_environment
            deploy_frontend
            build_backend
            build_runpod
            echo ""
            echo "🎉 All components built successfully!"
            echo ""
            echo "📋 Next steps:"
            echo "1. Upload frontend/out/ to Cloudflare Pages"
            echo "2. Deploy backend Docker image to your cloud provider"  
            echo "3. Push RunPod image to container registry and deploy to RunPod"
            echo "4. Update API endpoints in your configuration"
            ;;
        6)
            echo "👋 Goodbye!"
            exit 0
            ;;
        *)
            echo "❌ Invalid option. Please try again."
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
done 