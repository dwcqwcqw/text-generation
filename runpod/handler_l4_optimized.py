#!/usr/bin/env python3
"""
RunPod Handler - 专为NVIDIA L4 GPU优化
针对L4 GPU (计算能力8.9, Ada Lovelace架构) 特别调整
"""

import runpod
import os
import logging
import time
import threading
import subprocess
import json
from typing import Optional, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局变量
model = None
model_type = None
model_path = None
gpu_available = False

# 环境变量检查
def check_environment():
    """检查CUDA环境变量"""
    env_vars = {
        'CUDA_VISIBLE_DEVICES': os.environ.get('CUDA_VISIBLE_DEVICES', 'Not set'),
        'LLAMA_CUBLAS': os.environ.get('LLAMA_CUBLAS', 'Not set'),
        'CMAKE_ARGS': os.environ.get('CMAKE_ARGS', 'Not set'),
    }
    
    # 强制设置环境变量（Docker ENV可能不生效）
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    os.environ['LLAMA_CUBLAS'] = '1'
    
    for var, value in env_vars.items():
        logger.info(f"环境变量 {var}: {value}")
    
    return env_vars

# GPU检查
def check_gpu():
    """检查GPU可用性和CUDA支持"""
    try:
        # 检查环境变量
        check_environment()
        
        # 检查nvidia-smi
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,compute_cap', '--format=csv,noheader'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                gpu_info = result.stdout.strip().split('\n')[0].split(', ')
                gpu_name = gpu_info[0].strip()
                gpu_memory = float(gpu_info[1].split()[0]) / 1024  # 转换为GB
                compute_cap = gpu_info[2] if len(gpu_info) > 2 else "Unknown"
                logger.info(f"GPU检测: {gpu_name}, 内存: {gpu_memory:.1f}GB, 计算能力: {compute_cap}")
                
                # 检查是否为L4
                if "L4" in gpu_name:
                    logger.info("✅ 检测到NVIDIA L4 GPU")
                    return True, gpu_name, gpu_memory
            else:
                logger.warning("nvidia-smi命令失败")
        except Exception as e:
            logger.warning(f"nvidia-smi检查失败: {e}")
        
        # 检查PyTorch CUDA支持
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3 if gpu_count > 0 else 0
            logger.info(f"PyTorch CUDA可用: {gpu_count} GPU, 名称: {gpu_name}, 内存: {gpu_memory:.1f}GB")
            
            # 不进行GPU分配测试，避免可能的卡住
            return True, gpu_name, gpu_memory
        else:
            logger.warning("PyTorch CUDA不可用，将使用CPU")
            return False, "None", 0
    except Exception as e:
        logger.error(f"GPU检查错误: {e}")
        return False, "Error", 0

# 发现模型
def discover_models():
    """在卷中发现可用模型"""
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
    
    return available_models

# 加载GGUF模型
def load_gguf_model(model_path: str):
    """使用llama-cpp-python加载GGUF模型，针对L4 GPU优化"""
    try:
        # 导入llama-cpp
        from llama_cpp import Llama
        import llama_cpp
        
        logger.info(f"llama-cpp-python版本: {llama_cpp.__version__}")
        logger.info(f"从{model_path}加载GGUF模型")
        
        # 检查GPU可用性
        global gpu_available
        gpu_available, gpu_name, gpu_memory = check_gpu()
        
        # 针对L4 GPU优化的参数
        if gpu_available and "L4" in gpu_name:
            logger.info("使用针对L4 GPU优化的参数...")
            try:
                # 首先尝试GPU模式
                logger.info("尝试GPU模式 (30层)...")
                model = Llama(
                    model_path=model_path,
                    n_ctx=2048,           # 适中的上下文窗口
                    n_batch=512,          # 批处理大小
                    n_gpu_layers=30,      # L4 GPU层数
                    verbose=True,         # 详细日志
                    use_mmap=True,
                    use_mlock=False,
                )
                logger.info("✅ 模型在GPU模式下成功加载")
                return model, "gguf_gpu"
            except Exception as e:
                logger.warning(f"GPU模式加载失败: {e}")
                logger.info("尝试CPU回退模式...")
        
        # CPU模式 (回退或者GPU不可用)
        logger.info("使用CPU模式加载模型...")
        model = Llama(
            model_path=model_path,
            n_ctx=512,            # 较小的上下文窗口
            n_batch=128,          # 较小的批处理大小
            n_gpu_layers=0,       # CPU模式
            verbose=True,
            n_threads=4,          # 线程数
            use_mmap=True,
            use_mlock=False,
        )
        logger.info("✅ 模型在CPU模式下成功加载")
        return model, "gguf_cpu"
        
    except Exception as e:
        logger.error(f"模型加载失败: {e}")
        import traceback
        logger.error(f"异常详情: {traceback.format_exc()}")
        return None, None

# 初始化模型
def initialize_model():
    """初始化最佳可用模型，带有超时保护"""
    global model, model_type, model_path
    
    logger.info("开始模型初始化...")
    
    # 发现可用模型
    available_models = discover_models()
    
    if not available_models:
        logger.error("在指定路径未找到模型")
        return False
    
    # 按大小排序模型（优先使用较小的模型）
    available_models.sort(key=lambda x: x[1])
    
    # 添加超时保护
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("模型加载超时")
    
    # 尝试加载每个模型
    for model_path_candidate, size in available_models:
        logger.info(f"尝试加载模型: {model_path_candidate} ({size:.1f}GB)")
        
        if model_path_candidate.endswith('.gguf'):
            try:
                # 设置60秒超时
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(60)
                
                try:
                    loaded_model, loaded_type = load_gguf_model(model_path_candidate)
                    signal.alarm(0)  # 取消超时
                    
                    if loaded_model:
                        model = loaded_model
                        model_type = loaded_type
                        model_path = model_path_candidate
                        logger.info(f"成功加载GGUF模型: {model_path}")
                        return True
                    else:
                        logger.warning("GGUF模型加载返回None")
                except TimeoutError:
                    signal.alarm(0)
                    logger.error("模型加载在60秒后超时")
                    continue
                    
            except Exception as e:
                logger.error(f"GGUF加载异常: {e}")
                import traceback
                logger.error(f"完整异常堆栈: {traceback.format_exc()}")
                continue  # 尝试下一个模型
    
    logger.error("无法加载任何模型")
    return False

# 获取人格提示词
def get_personality_prompt(personality: str) -> str:
    """获取不同AI人格的系统提示词"""
    personalities = {
        "default": "You are a helpful AI assistant. Provide clear, accurate, and helpful responses.",
        "creative": "You are a creative AI assistant. Think outside the box and provide imaginative ideas.",
        "academic": "You are an academic AI assistant. Provide well-researched, precise, and scholarly responses.",
        "friendly": "You are a friendly AI assistant. Be warm, approachable, and conversational in your responses.",
        "professional": "You are a professional AI assistant. Provide concise, practical, and business-oriented advice."
    }
    
    return personalities.get(personality, personalities["default"])

# 格式化Llama提示词
def format_llama_prompt(prompt: str, personality: str = "default") -> str:
    """格式化Llama 3.2的提示词"""
    system_prompt = get_personality_prompt(personality)
    
    formatted_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
    
    return formatted_prompt

# 生成响应
def generate_response(prompt: str, personality: str = "default") -> str:
    """使用加载的模型生成响应"""
    global model, model_type, model_path
    
    if model is None:
        return "错误: 模型未加载。请检查服务器日志。"
    
    try:
        # 格式化提示词
        formatted_prompt = format_llama_prompt(prompt, personality)
        logger.info(f"生成响应，使用人格: {personality}")
        
        # 生成参数
        generation_params = {
            "max_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "stop": ["<|eot_id|>", "<|end_of_text|>", "<|start_header_id|>"]
        }
        
        # 生成响应
        start_time = time.time()
        output = model(formatted_prompt, **generation_params)
        elapsed = time.time() - start_time
        
        # 提取响应文本
        response_text = output["choices"][0]["text"] if isinstance(output, dict) else output
        
        logger.info(f"生成完成，耗时: {elapsed:.2f}秒")
        return response_text
        
    except Exception as e:
        logger.error(f"生成响应错误: {e}")
        import traceback
        logger.error(f"异常详情: {traceback.format_exc()}")
        return f"生成错误: {str(e)}"

# Handler函数
def handler(event):
    """RunPod handler函数"""
    try:
        logger.info("Handler被调用")
        
        # 提取输入
        user_input = event.get("input", {})
        prompt = user_input.get("prompt", "")
        personality = user_input.get("personality", "default")
        
        logger.info(f"收到提示词: {prompt[:50]}...")
        logger.info(f"人格: {personality}")
        
        # 初始化模型（如果未初始化）
        global model
        if model is None:
            logger.info("模型未初始化，开始初始化...")
            success = initialize_model()
            if not success:
                return {
                    "output": "错误: 模型初始化失败。请检查服务器日志。",
                    "status": "error"
                }
        
        # 生成响应
        response = generate_response(prompt, personality)
        
        logger.info(f"返回响应: {response[:50]}...")
        
        return {
            "output": response,
            "status": "success",
            "model": model_path,
            "model_type": model_type,
            "gpu_used": gpu_available
        }
        
    except Exception as e:
        logger.error(f"Handler错误: {e}")
        import traceback
        logger.error(f"异常详情: {traceback.format_exc()}")
        return {
            "output": f"错误: {str(e)}",
            "status": "error"
        }

# 启动RunPod serverless
if __name__ == "__main__":
    logger.info("启动L4优化的RunPod handler...")
    runpod.serverless.start({"handler": handler}) 