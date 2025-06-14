#!/usr/bin/env python3
"""
CUDA诊断脚本 - 检查llama-cpp-python的CUDA支持
"""

import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_environment():
    """检查环境变量"""
    logger.info("=== 环境变量检查 ===")
    cuda_vars = [
        'CUDA_VISIBLE_DEVICES',
        'LLAMA_CUBLAS', 
        'CMAKE_ARGS',
        'FORCE_CMAKE',
        'CUDA_LAUNCH_BLOCKING'
    ]
    
    for var in cuda_vars:
        value = os.environ.get(var, 'Not set')
        logger.info(f"{var}: {value}")

def check_nvidia_smi():
    """检查nvidia-smi"""
    logger.info("=== nvidia-smi检查 ===")
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("nvidia-smi输出:")
            print(result.stdout)
        else:
            logger.error(f"nvidia-smi失败: {result.stderr}")
    except Exception as e:
        logger.error(f"nvidia-smi错误: {e}")

def check_pytorch_cuda():
    """检查PyTorch CUDA支持"""
    logger.info("=== PyTorch CUDA检查 ===")
    try:
        import torch
        logger.info(f"PyTorch版本: {torch.__version__}")
        logger.info(f"CUDA可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            logger.info(f"CUDA版本: {torch.version.cuda}")
            logger.info(f"GPU数量: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                logger.info(f"GPU {i}: {torch.cuda.get_device_name(i)}")
                props = torch.cuda.get_device_properties(i)
                logger.info(f"  显存: {props.total_memory / 1024**3:.1f}GB")
                logger.info(f"  计算能力: {props.major}.{props.minor}")
    except Exception as e:
        logger.error(f"PyTorch检查失败: {e}")

def check_llama_cpp_cuda():
    """检查llama-cpp-python的CUDA支持"""
    logger.info("=== llama-cpp-python CUDA检查 ===")
    try:
        import llama_cpp
        logger.info(f"llama-cpp-python版本: {llama_cpp.__version__}")
        
        # 检查是否有CUDA支持
        try:
            # 尝试创建一个简单的模型实例来测试CUDA
            logger.info("测试CUDA支持...")
            
            # 检查llama_cpp的内部CUDA支持
            if hasattr(llama_cpp, '_lib'):
                logger.info("llama_cpp._lib存在")
            else:
                logger.warning("llama_cpp._lib不存在")
                
        except Exception as e:
            logger.error(f"CUDA支持测试失败: {e}")
            
    except ImportError as e:
        logger.error(f"无法导入llama-cpp-python: {e}")

def check_cuda_libraries():
    """检查CUDA库"""
    logger.info("=== CUDA库检查 ===")
    try:
        result = subprocess.run(['ldconfig', '-p'], capture_output=True, text=True)
        if result.returncode == 0:
            cuda_libs = [line for line in result.stdout.split('\n') if 'cuda' in line.lower()]
            if cuda_libs:
                logger.info("找到CUDA库:")
                for lib in cuda_libs[:10]:  # 只显示前10个
                    logger.info(f"  {lib.strip()}")
            else:
                logger.warning("未找到CUDA库")
    except Exception as e:
        logger.error(f"CUDA库检查失败: {e}")

def test_simple_model():
    """测试简单模型加载"""
    logger.info("=== 简单模型测试 ===")
    try:
        from llama_cpp import Llama
        
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
                
        if not model_path:
            logger.error("未找到模型文件")
            return
            
        logger.info(f"测试加载模型: {model_path}")
        
        # 测试GPU模式
        logger.info("测试GPU模式...")
        try:
            model = Llama(
                model_path=model_path,
                n_ctx=512,
                n_batch=128,
                n_gpu_layers=1,  # 只测试1层
                verbose=True
            )
            logger.info("✅ GPU模式测试成功")
            del model
        except Exception as e:
            logger.error(f"❌ GPU模式测试失败: {e}")
            
    except Exception as e:
        logger.error(f"模型测试失败: {e}")

if __name__ == "__main__":
    logger.info("🔍 开始CUDA诊断...")
    
    check_environment()
    check_nvidia_smi()
    check_pytorch_cuda()
    check_llama_cpp_cuda()
    check_cuda_libraries()
    test_simple_model()
    
    logger.info("🔍 CUDA诊断完成") 