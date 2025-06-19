#!/bin/bash

# Cloudflare Pages Build Script
set -e

echo "🚀 Starting Cloudflare Pages build..."
echo "📍 Current directory: $(pwd)"
echo "📂 Directory contents:"
ls -la

# Set environment variables
export NODE_VERSION="18"
export NEXT_PUBLIC_API_URL="https://api-text-generation.runpod.app"
export NEXT_PUBLIC_R2_BUCKET="text-generation"

# Check Node.js version
echo "📊 Node.js version: $(node --version)"
echo "📊 npm version: $(npm --version)"

# Enter frontend directory
echo "📁 Entering frontend directory..."
cd frontend

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Build project
echo "🔨 Building project..."
npm run build

# Verify build result
echo "✅ Verifying build result..."
if [ -d "out" ]; then
    echo "✅ Build successful!"
    echo "📊 Build statistics:"
    find out -type f | wc -l | xargs echo "  - File count:"
    du -sh out | xargs echo "  - Directory size:"
    
    # Check for config files
    echo "📄 Configuration files:"
    ls -la out/_* || echo "No config files found"
    
    echo "🎉 Build completed successfully!"
else
    echo "❌ Build failed - out directory not found"
    exit 1
fi 