#!/usr/bin/env python3
"""
RunPod GPU最终修复脚本
解决CPU_AARCH64错误和GPU层分配问题
"""

import os
import sys
import subprocess
import logging
import platform

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_system_info():
    """检查系统信息"""
    logger.info("🔍 系统信息检查:")
    logger.info(f"  操作系统: {platform.system()} {platform.release()}")
    logger.info(f"  架构: {platform.machine()}")
    logger.info(f"  Python版本: {sys.version}")
    
    # 检查CUDA
    try:
        result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"  CUDA版本: {result.stdout.split('release')[1].split(',')[0].strip()}")
        else:
            logger.warning("  CUDA未安装或不可用")
    except FileNotFoundError:
        logger.warning("  nvcc命令未找到")
    
    # 检查GPU
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                logger.info(f"  GPU: {line}")
        else:
            logger.warning("  GPU信息获取失败")
    except FileNotFoundError:
        logger.warning("  nvidia-smi命令未找到")

def force_x86_64_environment():
    """强制设置x86_64环境"""
    logger.info("🔧 强制设置x86_64环境变量...")
    
    env_vars = {
        # CUDA相关
        'CUDA_VISIBLE_DEVICES': '0',
        'GGML_CUDA': '1',
        'LLAMA_CUBLAS': '1',
        'CMAKE_CUDA_ARCHITECTURES': '75;80;86;89',
        'FORCE_CMAKE': '1',
        'CMAKE_ARGS': '-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75;80;86;89',
        
        # 架构强制
        'ARCHFLAGS': '-arch x86_64',
        'CFLAGS': '-march=x86-64',
        'CXXFLAGS': '-march=x86-64',
        'LDFLAGS': '-arch x86_64',
        
        # Python相关
        'PYTHONPATH': '/usr/local/lib/python3.10/site-packages',
        'PIP_PREFER_BINARY': '1',
        
        # 编译相关
        'CC': 'gcc',
        'CXX': 'g++',
        'NVCC_APPEND_FLAGS': '--allow-unsupported-compiler',
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        logger.info(f"  设置 {key}={value}")

def install_dependencies():
    """安装所有必要的依赖"""
    logger.info("🔄 安装RunPod依赖...")
    
    packages = [
        ('GPUtil', 'GPUtil'),
        ('runpod', 'runpod'),
    ]
    
    success_count = 0
    for package_name, import_name in packages:
        try:
            # 检查是否已安装
            __import__(import_name)
            logger.info(f"✅ {package_name} 已安装")
            success_count += 1
        except ImportError:
            # 安装包
            logger.info(f"📦 安装 {package_name}...")
            try:
                result = subprocess.run([
                    sys.executable, '-m', 'pip', 'install', package_name
                ], capture_output=True, text=True, check=True)
                logger.info(f"✅ {package_name} 安装成功")
                success_count += 1
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ {package_name} 安装失败: {e.stderr}")
    
    return success_count == len(packages)

def reinstall_llama_cpp_cuda():
    """重新安装CUDA版本的llama-cpp-python"""
    logger.info("🔄 重新安装CUDA版本的llama-cpp-python...")
    
    try:
        # 卸载现有版本
        logger.info("  卸载现有版本...")
        subprocess.run([sys.executable, '-m', 'pip', 'uninstall', 'llama-cpp-python', '-y'], 
                      check=False)
        
        # 清理缓存
        logger.info("  清理pip缓存...")
        subprocess.run([sys.executable, '-m', 'pip', 'cache', 'purge'], check=False)
        
        # 安装CUDA版本
        logger.info("  安装CUDA版本...")
        cmd = [
            sys.executable, '-m', 'pip', 'install', 
            '--force-reinstall', '--no-cache-dir', '--no-deps',
            'llama-cpp-python', 
            '--extra-index-url', 'https://abetlen.github.io/llama-cpp-python/whl/cu121'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ CUDA版本安装成功")
            return True
        else:
            logger.error(f"❌ 安装失败: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 重新安装失败: {e}")
        return False

def test_gpu_loading():
    """测试GPU加载"""
    logger.info("🧪 测试GPU加载...")
    
    try:
        from llama_cpp import Llama
        
        # 创建一个简单的测试
        test_code = '''
import os
os.environ['GGML_CUDA'] = '1'
from llama_cpp import Llama

# 查找模型文件
import glob
models = glob.glob("/runpod-volume/text_models/*.gguf")
if not models:
    print("❌ 未找到模型文件")
    exit(1)

model_path = models[0]
print(f"📂 测试模型: {model_path}")

# 尝试加载模型
try:
    model = Llama(
        model_path=model_path,
        n_ctx=2048,
        n_batch=512,
        n_gpu_layers=-1,  # 强制所有层到GPU
        verbose=True,
        n_threads=1,
        use_mmap=True,
        f16_kv=True,
        main_gpu=0,
    )
    print("✅ GPU加载测试成功")
    
    # 简单推理测试
    response = model("Hello", max_tokens=10, temperature=0.1)
    print(f"📤 推理测试: {response}")
    
except Exception as e:
    print(f"❌ GPU加载测试失败: {e}")
    exit(1)
'''
        
        # 写入测试文件
        with open('/tmp/gpu_test.py', 'w') as f:
            f.write(test_code)
        
        # 运行测试
        result = subprocess.run([sys.executable, '/tmp/gpu_test.py'], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info("✅ GPU加载测试通过")
            logger.info(f"输出: {result.stdout}")
            return True
        else:
            logger.error(f"❌ GPU加载测试失败: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试异常: {e}")
        return False

def create_optimized_dockerfile():
    """创建优化的Dockerfile"""
    logger.info("📝 创建优化的Dockerfile...")
    
    dockerfile_content = '''# 强制x86_64架构的CUDA基础镜像
FROM --platform=linux/amd64 nvidia/cuda:12.1-base-ubuntu22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV CUDA_VISIBLE_DEVICES=0
ENV GGML_CUDA=1
ENV LLAMA_CUBLAS=1
ENV CMAKE_CUDA_ARCHITECTURES="75;80;86;89"
ENV FORCE_CMAKE=1
ENV CMAKE_ARGS="-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75;80;86;89"
ENV ARCHFLAGS="-arch x86_64"
ENV CFLAGS="-march=x86-64"
ENV CXXFLAGS="-march=x86-64"
ENV NVCC_APPEND_FLAGS="--allow-unsupported-compiler"

# 安装系统依赖
RUN apt-get update && apt-get install -y \\
    python3 python3-pip python3-dev \\
    build-essential cmake \\
    nvidia-cuda-toolkit \\
    && rm -rf /var/lib/apt/lists/*

# 升级pip
RUN python3 -m pip install --upgrade pip

# 安装CUDA版本的llama-cpp-python
RUN pip install --no-cache-dir \\
    llama-cpp-python \\
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121

# 安装其他依赖
RUN pip install --no-cache-dir \\
    runpod GPUtil

# 复制handler
COPY handler_llama_ai.py /app/handler.py
WORKDIR /app

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD python3 -c "import llama_cpp; print('OK')" || exit 1

# 启动命令
CMD ["python3", "-u", "handler.py"]
'''
    
    with open('Dockerfile.gpu_optimized', 'w') as f:
        f.write(dockerfile_content)
    
    logger.info("✅ 优化Dockerfile已创建: Dockerfile.gpu_optimized")

def main():
    """主函数"""
    logger.info("🚀 开始RunPod GPU最终修复...")
    
    # 1. 检查系统信息
    check_system_info()
    
    # 2. 强制设置环境
    force_x86_64_environment()
    
    # 3. 安装基础依赖
    if not install_dependencies():
        logger.error("❌ 基础依赖安装失败")
        return False
    
    # 4. 重新安装CUDA版本
    if not reinstall_llama_cpp_cuda():
        logger.error("❌ CUDA版本安装失败，请检查网络连接")
        return False
    
    # 5. 测试GPU加载
    if not test_gpu_loading():
        logger.error("❌ GPU加载测试失败")
        return False
    
    # 6. 创建优化Dockerfile
    create_optimized_dockerfile()
    
    logger.info("🎉 RunPod GPU修复完成！")
    logger.info("📋 下一步:")
    logger.info("  1. 重启RunPod容器")
    logger.info("  2. 或使用新的Dockerfile.gpu_optimized重新构建镜像")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 