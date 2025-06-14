#!/usr/bin/env python3
"""
修复CUDA支持脚本 - 重新编译llama-cpp-python
"""

import os
import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_command(cmd, description):
    """运行命令并记录输出"""
    logger.info(f"🔄 {description}")
    logger.info(f"执行命令: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        
        if result.stdout:
            logger.info(f"输出: {result.stdout}")
        if result.stderr:
            logger.warning(f"错误: {result.stderr}")
            
        if result.returncode == 0:
            logger.info(f"✅ {description} 成功")
        else:
            logger.error(f"❌ {description} 失败，返回码: {result.returncode}")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        logger.error(f"❌ {description} 超时")
        return False
    except Exception as e:
        logger.error(f"❌ {description} 异常: {e}")
        return False

def main():
    logger.info("🚀 开始修复CUDA支持...")
    
    # 设置环境变量
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    os.environ['GGML_CUDA'] = '1'
    os.environ['CMAKE_ARGS'] = '-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=89'
    os.environ['FORCE_CMAKE'] = '1'
    
    logger.info("🔧 设置环境变量:")
    for key in ['CUDA_VISIBLE_DEVICES', 'GGML_CUDA', 'CMAKE_ARGS', 'FORCE_CMAKE']:
        logger.info(f"  {key}={os.environ.get(key)}")
    
    # 1. 检查CUDA
    if not run_command("nvidia-smi", "检查CUDA"):
        logger.error("❌ CUDA不可用，无法继续")
        return False
    
    # 2. 卸载现有的llama-cpp-python
    run_command("pip uninstall llama-cpp-python -y", "卸载现有llama-cpp-python")
    
    # 3. 清理缓存
    run_command("pip cache purge", "清理pip缓存")
    
    # 4. 重新安装llama-cpp-python with CUDA
    install_cmd = (
        "CMAKE_ARGS='-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=89' "
        "FORCE_CMAKE=1 "
        "pip install --no-cache-dir --force-reinstall --verbose "
        "llama-cpp-python==0.3.9"
    )
    
    if not run_command(install_cmd, "重新安装llama-cpp-python with CUDA"):
        logger.error("❌ 安装失败")
        return False
    
    # 5. 验证安装
    logger.info("🔍 验证CUDA支持...")
    
    try:
        import llama_cpp
        logger.info(f"✅ llama-cpp-python版本: {llama_cpp.__version__}")
        
        # 尝试创建一个简单的模型来测试CUDA
        logger.info("🧪 测试CUDA支持...")
        
        # 查找模型文件
        model_paths = [
            "/runpod-volume/text_models/L3.2-8X4B.gguf",
            "/runpod-volume/text_models/L3.2-8X3B.gguf"
        ]
        
        model_path = None
        for path in model_paths:
            if os.path.exists(path):
                model_path = path
                break
        
        if model_path:
            logger.info(f"📂 使用模型: {model_path}")
            
            # 测试GPU模式
            from llama_cpp import Llama
            
            model = Llama(
                model_path=model_path,
                n_ctx=512,
                n_batch=128,
                n_gpu_layers=1,  # 只测试1层
                verbose=True
            )
            
            logger.info("✅ CUDA支持测试成功！")
            del model
            
        else:
            logger.warning("⚠️ 未找到模型文件，跳过CUDA测试")
            
    except Exception as e:
        logger.error(f"❌ CUDA支持验证失败: {e}")
        return False
    
    logger.info("🎉 CUDA修复完成！")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 