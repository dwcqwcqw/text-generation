#!/usr/bin/env python3
"""
RunPod 测试 Handler
仅用于测试RunPod环境，不加载任何模型
"""

import runpod
import os
import sys
import logging
import json
import time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_environment():
    """检查环境并返回系统信息"""
    info = {
        "python_version": sys.version,
        "working_directory": os.getcwd(),
        "environment_variables": {
            "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES", "Not set"),
            "LLAMA_CUBLAS": os.environ.get("LLAMA_CUBLAS", "Not set"),
            "PATH": os.environ.get("PATH", "Not set")[:100] + "...",  # 截断过长的路径
        }
    }
    
    # 检查GPU
    try:
        import torch
        info["torch_version"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            info["gpu_count"] = torch.cuda.device_count()
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["gpu_memory"] = f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
    except Exception as e:
        info["torch_error"] = str(e)
    
    # 检查llama-cpp-python
    try:
        import llama_cpp
        info["llama_cpp_version"] = llama_cpp.__version__
        info["llama_cpp_cuda"] = getattr(llama_cpp, "_LLAMA_CUDA", False)
    except Exception as e:
        info["llama_cpp_error"] = str(e)
    
    # 检查模型文件
    model_paths = [
        "/runpod-volume/text_models/L3.2-8X4B.gguf",
        "/runpod-volume/text_models/L3.2-8X3B.gguf"
    ]
    
    info["models"] = {}
    for path in model_paths:
        if os.path.exists(path):
            try:
                size = os.path.getsize(path) / (1024**3)
                info["models"][path] = f"{size:.1f} GB"
            except Exception as e:
                info["models"][path] = f"Error: {str(e)}"
        else:
            info["models"][path] = "Not found"
    
    return info

def handler(event):
    """简单的handler函数，返回环境信息而不加载模型"""
    try:
        logger.info("Handler被调用")
        start_time = time.time()
        
        # 获取输入
        input_data = event.get("input", {})
        prompt = input_data.get("prompt", "Hello")
        
        # 检查环境
        env_info = check_environment()
        
        # 构建响应
        response = {
            "status": "success",
            "message": f"RunPod测试成功! 收到的提示词: {prompt[:50]}...",
            "environment": env_info,
            "timestamp": time.time(),
            "elapsed": f"{time.time() - start_time:.2f}秒"
        }
        
        logger.info(f"返回测试响应，耗时: {time.time() - start_time:.2f}秒")
        return response
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Handler错误: {e}\n{error_details}")
        return {
            "status": "error",
            "message": f"错误: {str(e)}",
            "error_details": error_details
        }

if __name__ == "__main__":
    logger.info("启动RunPod测试handler...")
    runpod.serverless.start({"handler": handler}) 