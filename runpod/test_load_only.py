#!/usr/bin/env python3
"""
纯模型加载测试
不涉及RunPod，只测试模型加载
"""

import os
import sys
import time
import logging
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    logger.info("=== 纯模型加载测试 ===")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"当前工作目录: {os.getcwd()}")
    
    # 检查环境变量
    env_vars = {
        'CUDA_VISIBLE_DEVICES': os.environ.get('CUDA_VISIBLE_DEVICES', 'Not set'),
        'LLAMA_CUBLAS': os.environ.get('LLAMA_CUBLAS', 'Not set'),
        'CMAKE_ARGS': os.environ.get('CMAKE_ARGS', 'Not set'),
    }
    
    # 强制设置环境变量
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    os.environ['LLAMA_CUBLAS'] = '1'
    
    logger.info(f"环境变量: {env_vars}")
    
    # 检查模型文件
    model_paths = [
        "/runpod-volume/text_models/L3.2-8X4B.gguf",  # 较小的模型
        "/runpod-volume/text_models/L3.2-8X3B.gguf"   # 较大的模型
    ]
    
    available_models = []
    for path in model_paths:
        if os.path.exists(path):
            size = os.path.getsize(path) / (1024**3)  # 大小(GB)
            available_models.append((path, size))
            logger.info(f"发现模型: {path} ({size:.1f}GB)")
        else:
            logger.warning(f"模型未找到: {path}")
    
    if not available_models:
        logger.error("没有找到可用的模型文件")
        return
    
    # 按大小排序，先尝试较小的模型
    available_models.sort(key=lambda x: x[1])
    model_path, size = available_models[0]
    
    logger.info(f"将尝试加载模型: {model_path} ({size:.1f}GB)")
    
    # 测试导入llama-cpp
    try:
        from llama_cpp import Llama
        import llama_cpp
        logger.info(f"llama-cpp-python版本: {llama_cpp.__version__}")
    except Exception as e:
        logger.error(f"导入llama-cpp失败: {e}")
        return
    
    # 测试CPU加载
    try:
        logger.info("\n=== 测试CPU加载 ===")
        logger.info("使用最小化参数...")
        
        start_time = time.time()
        model = Llama(
            model_path=model_path,
            n_ctx=32,            # 极小的上下文窗口
            n_batch=1,           # 最小批处理大小
            n_gpu_layers=0,      # CPU模式
            verbose=True,        # 详细日志
            n_threads=1,         # 单线程
            use_mmap=False,      # 禁用mmap
            use_mlock=False,     # 禁用mlock
        )
        elapsed = time.time() - start_time
        
        logger.info(f"✅ CPU模型加载成功! 耗时: {elapsed:.2f}秒")
        
        # 测试简单推理
        logger.info("测试简单推理...")
        output = model("Hello", max_tokens=1)
        logger.info(f"推理结果: {output}")
        
        # 释放模型
        del model
        logger.info("模型已释放")
        
    except Exception as e:
        logger.error(f"CPU模型加载失败: {e}")
        logger.error(f"异常堆栈: {traceback.format_exc()}")
    
    # 测试GPU加载 (从1层开始逐渐增加)
    for n_layers in [1, 5, 10, 20]:
        try:
            logger.info(f"\n=== 测试GPU加载 ({n_layers}层) ===")
            
            start_time = time.time()
            model = Llama(
                model_path=model_path,
                n_ctx=32,              # 极小的上下文窗口
                n_batch=1,             # 最小批处理大小
                n_gpu_layers=n_layers, # GPU层数
                verbose=True,          # 详细日志
                n_threads=1,           # 单线程
                use_mmap=False,        # 禁用mmap
                use_mlock=False,       # 禁用mlock
            )
            elapsed = time.time() - start_time
            
            logger.info(f"✅ GPU模型加载成功 ({n_layers}层)! 耗时: {elapsed:.2f}秒")
            
            # 测试简单推理
            logger.info("测试简单推理...")
            output = model("Hello", max_tokens=1)
            logger.info(f"推理结果: {output}")
            
            # 释放模型
            del model
            logger.info("模型已释放")
            
            # 如果成功，就不继续测试更多层
            logger.info(f"GPU加载测试成功，使用{n_layers}层")
            break
            
        except Exception as e:
            logger.error(f"GPU模型加载失败 ({n_layers}层): {e}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
    
    logger.info("\n=== 测试完成 ===")

if __name__ == "__main__":
    main() 