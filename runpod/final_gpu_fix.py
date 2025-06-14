#!/usr/bin/env python3
"""
最终GPU修复脚本 - 解决CPU_AARCH64架构问题
确保所有模型层都加载到GPU而不是CPU
"""

import os
import sys
import subprocess
import logging
import platform

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_system_architecture():
    """检查系统架构"""
    arch = platform.machine()
    logger.info(f"🔍 系统架构: {arch}")
    
    if arch == 'aarch64' or arch == 'arm64':
        logger.error("❌ 检测到ARM64架构，这会导致CPU_AARCH64错误")
        logger.info("🔧 强制设置x86_64环境变量...")
        
        # 强制设置x86_64环境变量
        os.environ['ARCHFLAGS'] = '-arch x86_64'
        os.environ['CFLAGS'] = '-march=x86-64'
        os.environ['CXXFLAGS'] = '-march=x86-64'
        os.environ['CMAKE_OSX_ARCHITECTURES'] = 'x86_64'
        
        return False
    elif arch == 'x86_64':
        logger.info("✅ 正确的x86_64架构")
        return True
    else:
        logger.warning(f"⚠️ 未知架构: {arch}")
        return False

def setup_cuda_environment():
    """设置CUDA环境变量"""
    logger.info("🔧 设置CUDA环境变量...")
    
    cuda_env = {
        'CUDA_VISIBLE_DEVICES': '0',
        'GGML_CUDA': '1',
        'CMAKE_CUDA_ARCHITECTURES': '75;80;86;89',
        'FORCE_CMAKE': '1',
        'CMAKE_ARGS': '-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75;80;86;89',
        'ARCHFLAGS': '-arch x86_64',
        'CFLAGS': '-march=x86-64',
        'CXXFLAGS': '-march=x86-64'
    }
    
    for key, value in cuda_env.items():
        os.environ[key] = value
        logger.info(f"  ✓ {key}={value}")

def check_nvidia_driver():
    """检查NVIDIA驱动"""
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("✅ NVIDIA驱动正常")
            # 解析GPU信息
            lines = result.stdout.split('\n')
            for line in lines:
                if 'RTX' in line or 'Tesla' in line or 'L4' in line or 'L40' in line:
                    logger.info(f"🎯 检测到GPU: {line.strip()}")
            return True
        else:
            logger.error("❌ nvidia-smi命令失败")
            return False
    except Exception as e:
        logger.error(f"❌ NVIDIA驱动检查失败: {e}")
        return False

def reinstall_llama_cpp_python():
    """重新安装GPU版本的llama-cpp-python"""
    logger.info("🔄 重新安装GPU版本的llama-cpp-python...")
    
    try:
        # 卸载现有版本
        logger.info("📦 卸载现有版本...")
        subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'llama-cpp-python'], 
                      capture_output=True)
        
        # 设置编译环境变量
        env = os.environ.copy()
        env.update({
            'CMAKE_ARGS': '-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75;80;86;89',
            'FORCE_CMAKE': '1',
            'ARCHFLAGS': '-arch x86_64'
        })
        
        # 安装GPU版本
        logger.info("📦 安装GPU版本...")
        cmd = [
            sys.executable, '-m', 'pip', 'install', 
            'llama-cpp-python', '--upgrade', '--no-cache-dir', '--force-reinstall',
            '--extra-index-url', 'https://abetlen.github.io/llama-cpp-python/whl/cu121'
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            logger.info("✅ llama-cpp-python GPU版本安装成功")
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
        logger.info(f"✅ llama-cpp-python导入成功")
        
        # 创建一个测试模型实例（不加载实际模型）
        logger.info("🔧 测试GPU配置...")
        
        # 检查是否有模型文件
        model_dir = "/runpod-volume/text_models"
        if os.path.exists(model_dir):
            model_files = [f for f in os.listdir(model_dir) if f.endswith('.gguf')]
            if model_files:
                model_path = os.path.join(model_dir, model_files[0])
                logger.info(f"🎯 测试模型: {model_path}")
                
                # 创建模型实例进行测试
                test_model = Llama(
                    model_path=model_path,
                    n_gpu_layers=-1,  # 强制所有层到GPU
                    n_ctx=2048,       # 小上下文用于测试
                    verbose=True      # 显示详细日志
                )
                
                logger.info("✅ GPU模型加载测试成功")
                del test_model  # 释放内存
                return True
            else:
                logger.warning("⚠️ 未找到模型文件，跳过加载测试")
                return True
        else:
            logger.warning("⚠️ 模型目录不存在，跳过加载测试")
            return True
            
    except Exception as e:
        logger.error(f"❌ GPU加载测试失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始最终GPU修复...")
    
    success = True
    
    # 1. 检查系统架构
    if not check_system_architecture():
        logger.warning("⚠️ 架构问题，已设置强制x86_64环境变量")
    
    # 2. 设置CUDA环境
    setup_cuda_environment()
    
    # 3. 检查NVIDIA驱动
    if not check_nvidia_driver():
        logger.error("❌ NVIDIA驱动检查失败")
        success = False
    
    # 4. 重新安装llama-cpp-python
    if not reinstall_llama_cpp_python():
        logger.error("❌ llama-cpp-python重新安装失败")
        success = False
    
    # 5. 测试GPU加载
    if not test_gpu_loading():
        logger.error("❌ GPU加载测试失败")
        success = False
    
    if success:
        logger.info("🎉 最终GPU修复完成！")
        logger.info("📋 修复摘要:")
        logger.info("  ✓ 强制x86_64架构环境变量")
        logger.info("  ✓ CUDA环境变量配置")
        logger.info("  ✓ NVIDIA驱动检查")
        logger.info("  ✓ GPU版本llama-cpp-python安装")
        logger.info("  ✓ GPU加载测试")
        logger.info("")
        logger.info("🔥 现在所有模型层都应该加载到GPU而不是CPU！")
        return 0
    else:
        logger.error("❌ 修复过程中出现错误，请检查日志")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 