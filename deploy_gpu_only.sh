#!/bin/bash
# GPU-only 部署脚本

# 颜色设置
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===== GPU-only 部署脚本 =====${NC}"
echo "此脚本将部署强制使用GPU的handler和Dockerfile到RunPod"

# 检查参数
if [ -z "$1" ]; then
    echo -e "${RED}错误: 缺少RunPod endpoint ID${NC}"
    echo "用法: ./deploy_gpu_only.sh <endpoint_id>"
    echo "例如: ./deploy_gpu_only.sh 4cx6jtjdx6hdhr"
    exit 1
fi

ENDPOINT_ID=$1
echo -e "${YELLOW}将部署到RunPod endpoint: ${ENDPOINT_ID}${NC}"

# 创建临时目录
TEMP_DIR="gpu_only_deploy"
mkdir -p $TEMP_DIR
echo "创建临时目录: $TEMP_DIR"

# 复制文件
echo "复制文件..."
cp runpod/handler_gpu_only.py $TEMP_DIR/
cp runpod/Dockerfile.gpu $TEMP_DIR/
cp runpod/requirements.txt $TEMP_DIR/
cp runpod/l4_gpu_test.py $TEMP_DIR/
cp runpod/test_load_only.py $TEMP_DIR/

# 创建README
echo "创建README文件..."
cat > $TEMP_DIR/README.md << EOL
# GPU-only 部署包

这个包包含了强制使用GPU的handler和Dockerfile。

## 文件说明

- \`handler_gpu_only.py\` - 强制使用GPU的handler
- \`Dockerfile.gpu\` - 针对L4 GPU优化的Dockerfile
- \`requirements.txt\` - 依赖项
- \`l4_gpu_test.py\` - GPU测试脚本
- \`test_load_only.py\` - 模型加载测试脚本

## 使用方法

1. 运行 \`./deploy.sh\` 部署GPU-only版本
2. 等待部署完成
3. 测试GPU功能: \`python test_load_only.py\`
EOL

# 创建部署脚本
echo "创建部署脚本..."
cat > $TEMP_DIR/deploy.sh << EOL
#!/bin/bash
# 部署GPU-only版本

echo "开始部署GPU-only版本..."

# 重命名handler
cp handler_gpu_only.py handler.py
echo "已将GPU-only handler复制为handler.py"

# 重命名Dockerfile
cp Dockerfile.gpu Dockerfile
echo "已将GPU优化的Dockerfile复制为Dockerfile"

echo "部署完成!"
echo "现在可以重新构建和部署RunPod endpoint了"
echo "请在RunPod控制台中重新构建Docker镜像"
EOL

# 添加执行权限
chmod +x $TEMP_DIR/deploy.sh

# 创建ZIP文件
ZIP_FILE="gpu_only_deploy.zip"
echo "创建ZIP文件: $ZIP_FILE"
(cd $TEMP_DIR && zip -r ../$ZIP_FILE *)

# 上传到RunPod
echo -e "${YELLOW}正在上传到RunPod endpoint: ${ENDPOINT_ID}${NC}"
echo "此功能需要RunPod CLI，请确保已安装并配置"
echo "如果未安装，请访问: https://github.com/runpod/runpodctl"

# 检查runpodctl是否已安装
if command -v runpodctl &> /dev/null; then
    echo "使用runpodctl上传文件..."
    runpodctl upload $ZIP_FILE $ENDPOINT_ID:/workspace/gpu_only_deploy.zip
    
    echo "解压文件到RunPod..."
    runpodctl exec $ENDPOINT_ID "mkdir -p gpu_only && unzip gpu_only_deploy.zip -d gpu_only && cd gpu_only && chmod +x deploy.sh"
    
    echo -e "${GREEN}部署完成!${NC}"
    echo "文件已上传到RunPod endpoint: $ENDPOINT_ID"
    echo "请登录RunPod并运行以下命令:"
    echo "  cd gpu_only"
    echo "  ./deploy.sh            # 部署GPU-only版本"
    echo "  python test_load_only.py  # 测试GPU功能"
else
    echo -e "${YELLOW}未找到runpodctl，跳过自动上传${NC}"
    echo "请手动上传 $ZIP_FILE 到RunPod endpoint"
    echo "然后在RunPod上运行:"
    echo "  mkdir -p gpu_only && unzip gpu_only_deploy.zip -d gpu_only && cd gpu_only && chmod +x deploy.sh"
fi

# 清理
echo "清理临时文件..."
rm -rf $TEMP_DIR

echo -e "${GREEN}===== 脚本执行完成 =====${NC}" 