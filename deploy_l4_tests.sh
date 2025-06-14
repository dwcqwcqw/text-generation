#!/bin/bash
# L4 GPU 测试和优化部署脚本

# 颜色设置
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===== L4 GPU 测试和优化部署脚本 =====${NC}"
echo "此脚本将部署L4 GPU测试和优化文件到RunPod"

# 检查参数
if [ -z "$1" ]; then
    echo -e "${RED}错误: 缺少RunPod endpoint ID${NC}"
    echo "用法: ./deploy_l4_tests.sh <endpoint_id>"
    echo "例如: ./deploy_l4_tests.sh 4cx6jtjdx6hdhr"
    exit 1
fi

ENDPOINT_ID=$1
echo -e "${YELLOW}将部署到RunPod endpoint: ${ENDPOINT_ID}${NC}"

# 创建临时目录
TEMP_DIR="l4_gpu_test_deploy"
mkdir -p $TEMP_DIR
echo "创建临时目录: $TEMP_DIR"

# 复制测试文件
echo "复制测试文件..."
cp runpod/l4_gpu_test.py $TEMP_DIR/
cp runpod/test_load_only.py $TEMP_DIR/
cp runpod/handler_test.py $TEMP_DIR/
cp runpod/handler_l4_optimized.py $TEMP_DIR/
cp runpod/handler_simple.py $TEMP_DIR/
cp runpod/Dockerfile $TEMP_DIR/Dockerfile.l4
cp L4_GPU_FIX_GUIDE.md $TEMP_DIR/

# 创建README
echo "创建README文件..."
cat > $TEMP_DIR/README.md << EOL
# L4 GPU 测试和优化套件

这个套件包含了用于测试和优化NVIDIA L4 GPU上的Llama模型的工具。

## 文件说明

- \`l4_gpu_test.py\` - 全面测试GPU检测和模型加载
- \`test_load_only.py\` - 只测试模型加载，不涉及RunPod
- \`handler_test.py\` - 测试RunPod环境，不加载模型
- \`handler_l4_optimized.py\` - 针对L4 GPU优化的handler
- \`handler_simple.py\` - 简化的handler，不加载模型
- \`Dockerfile.l4\` - 针对L4 GPU优化的Dockerfile
- \`L4_GPU_FIX_GUIDE.md\` - 详细的优化指南

## 使用方法

1. 运行环境诊断: \`python handler_test.py\`
2. 测试模型加载: \`python test_load_only.py\`
3. 全面GPU测试: \`python l4_gpu_test.py\`

## 部署优化的handler

1. 将 \`handler_l4_optimized.py\` 重命名为 \`handler.py\`
2. 使用 \`Dockerfile.l4\` 构建新的Docker镜像
3. 部署到RunPod

详细说明请参考 \`L4_GPU_FIX_GUIDE.md\`
EOL

# 创建部署脚本
echo "创建部署脚本..."
cat > $TEMP_DIR/deploy.sh << EOL
#!/bin/bash
# 部署优化的handler

# 重命名优化的handler
cp handler_l4_optimized.py handler.py
echo "已将优化的handler复制为handler.py"

# 重命名Dockerfile
cp Dockerfile.l4 Dockerfile
echo "已将优化的Dockerfile复制为Dockerfile"

echo "现在可以重新构建和部署RunPod endpoint了"
echo "请参考L4_GPU_FIX_GUIDE.md获取更多信息"
EOL

# 添加执行权限
chmod +x $TEMP_DIR/deploy.sh

# 创建ZIP文件
ZIP_FILE="l4_gpu_test_deploy.zip"
echo "创建ZIP文件: $ZIP_FILE"
(cd $TEMP_DIR && zip -r ../$ZIP_FILE *)

# 上传到RunPod
echo -e "${YELLOW}正在上传到RunPod endpoint: ${ENDPOINT_ID}${NC}"
echo "此功能需要RunPod CLI，请确保已安装并配置"
echo "如果未安装，请访问: https://github.com/runpod/runpodctl"

# 检查runpodctl是否已安装
if command -v runpodctl &> /dev/null; then
    echo "使用runpodctl上传文件..."
    runpodctl upload $ZIP_FILE $ENDPOINT_ID:/workspace/l4_gpu_test_deploy.zip
    
    echo "解压文件到RunPod..."
    runpodctl exec $ENDPOINT_ID "mkdir -p l4_gpu_test && unzip l4_gpu_test_deploy.zip -d l4_gpu_test && cd l4_gpu_test && chmod +x deploy.sh"
    
    echo -e "${GREEN}部署完成!${NC}"
    echo "文件已上传到RunPod endpoint: $ENDPOINT_ID"
    echo "请登录RunPod并运行以下命令:"
    echo "  cd l4_gpu_test"
    echo "  python l4_gpu_test.py  # 运行测试"
    echo "  ./deploy.sh            # 部署优化的handler"
else
    echo -e "${YELLOW}未找到runpodctl，跳过自动上传${NC}"
    echo "请手动上传 $ZIP_FILE 到RunPod endpoint"
    echo "然后在RunPod上运行:"
    echo "  mkdir -p l4_gpu_test && unzip l4_gpu_test_deploy.zip -d l4_gpu_test && cd l4_gpu_test && chmod +x deploy.sh"
fi

# 清理
echo "清理临时文件..."
rm -rf $TEMP_DIR

echo -e "${GREEN}===== 脚本执行完成 =====${NC}" 