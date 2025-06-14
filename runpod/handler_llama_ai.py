#!/usr/bin/env python3
"""
RunPod Handler - 强制GPU模式，彻底删除CPU代码
专为L40 GPU优化，45GB显存
"""

import runpod
import os
import logging
import time
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

# 强制设置环境变量
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
os.environ['LLAMA_CUBLAS'] = '1'
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'

def check_gpu_usage():
    """检查GPU使用情况"""
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            gpu_info = result.stdout.strip().split(', ')
            gpu_util = gpu_info[0]
            memory_used = float(gpu_info[1]) / 1024  # GB
            memory_total = float(gpu_info[2]) / 1024  # GB
            temperature = gpu_info[3]
            logger.info(f"🔥 GPU状态: 利用率{gpu_util}%, 显存{memory_used:.1f}/{memory_total:.1f}GB, 温度{temperature}°C")
            return True
        else:
            logger.error("无法获取GPU状态")
            return False
    except Exception as e:
        logger.error(f"GPU状态检查失败: {e}")
        return False

def check_gpu():
    """检查GPU可用性"""
    try:
        # 检查PyTorch CUDA支持
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3 if gpu_count > 0 else 0
            logger.info(f"✅ GPU检测成功: {gpu_name}, 显存: {gpu_memory:.1f}GB")
            return True, gpu_name, gpu_memory
        else:
            logger.error("❌ PyTorch CUDA不可用")
            raise RuntimeError("GPU不可用，无法继续")
    except Exception as e:
        logger.error(f"❌ GPU检查失败: {e}")
        raise RuntimeError(f"GPU检查失败: {e}")

def discover_models():
    """发现可用模型"""
    model_paths = [
        "/runpod-volume/text_models/L3.2-8X4B.gguf",  # 较小的模型
        "/runpod-volume/text_models/L3.2-8X3B.gguf"   # 较大的模型
    ]
    
    available_models = []
    for path in model_paths:
        if os.path.exists(path):
            size = os.path.getsize(path) / (1024**3)  # 大小(GB)
            available_models.append((path, size))
            logger.info(f"📁 发现模型: {path} ({size:.1f}GB)")
        else:
            logger.warning(f"⚠️ 模型未找到: {path}")
    
    return available_models

def load_gguf_model(model_path: str):
    """强制GPU模式加载GGUF模型"""
    try:
        from llama_cpp import Llama
        import llama_cpp
        
        logger.info(f"🚀 llama-cpp-python版本: {llama_cpp.__version__}")
        logger.info(f"📂 加载模型: {model_path}")
        
        # 检查GPU
        gpu_available, gpu_name, gpu_memory = check_gpu()
        
        # 强制使用全部GPU层
        logger.info(f"🎯 强制GPU模式: 全部层到GPU ({gpu_name})")
        
        # 检查初始GPU状态
        check_gpu_usage()
        
        model = Llama(
            model_path=model_path,
            n_ctx=4096,           # 更大的上下文窗口
            n_batch=1024,         # 更大的批处理大小
            n_gpu_layers=-1,      # 全部层到GPU
            verbose=False,        # 关闭详细日志减少噪音
            use_mmap=True,
            use_mlock=False,
            n_threads=1,          # GPU模式下减少CPU线程
        )
        
        logger.info("✅ 模型GPU加载成功")
        
        # 检查加载后GPU状态
        check_gpu_usage()
        
        return model, "gguf_gpu"
        
    except Exception as e:
        logger.error(f"❌ 模型加载失败: {e}")
        raise RuntimeError(f"模型加载失败: {e}")

def initialize_model():
    """初始化模型"""
    global model, model_type, model_path
    
    logger.info("🔄 开始模型初始化...")
    
    # 发现可用模型
    available_models = discover_models()
    
    if not available_models:
        raise RuntimeError("未找到任何模型")
    
    # 按大小排序模型（优先使用较小的模型）
    available_models.sort(key=lambda x: x[1])
    
    # 加载第一个可用模型
    model_path_candidate, size = available_models[0]
    logger.info(f"🎯 选择模型: {model_path_candidate} ({size:.1f}GB)")
    
    if model_path_candidate.endswith('.gguf'):
        loaded_model, loaded_type = load_gguf_model(model_path_candidate)
        
        if loaded_model:
            model = loaded_model
            model_type = loaded_type
            model_path = model_path_candidate
            logger.info(f"✅ 模型初始化完成: {model_path}")
            return True
    
    raise RuntimeError("模型初始化失败")

def get_personality_prompt(personality: str) -> str:
    """获取AI人格提示词"""
    personalities = {
        "default": "You are a helpful AI assistant. Provide clear, accurate, and helpful responses.",
        "creative": "You are a creative AI assistant. Think outside the box and provide imaginative ideas.",
        "academic": "You are an academic AI assistant. Provide well-researched, precise, and scholarly responses.",
        "friendly": "You are a friendly AI assistant. Be warm, approachable, and conversational in your responses.",
        "professional": "You are a professional AI assistant. Provide concise, practical, and business-oriented advice."
    }
    return personalities.get(personality, personalities["default"])

def format_llama_prompt(prompt: str, personality: str = "default") -> str:
    """格式化Llama 3.2提示词"""
    system_prompt = get_personality_prompt(personality)
    
    # 直接构建提示词，不检查重复
    formatted_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
    
    return formatted_prompt

def generate_response(prompt: str, personality: str = "default") -> str:
    """生成响应"""
    global model, model_type, model_path
    
    if model is None:
        raise RuntimeError("模型未加载")
    
    try:
        # 格式化提示词
        formatted_prompt = format_llama_prompt(prompt, personality)
        logger.info(f"💭 生成响应 (人格: {personality})")
        
        # 检查生成前GPU状态
        check_gpu_usage()
        
        # 生成参数
        generation_params = {
            "max_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "stop": ["<|eot_id|>", "<|end_of_text|>", "<|start_header_id|>"],
            "echo": False
        }
        
        # 生成响应
        start_time = time.time()
        output = model(formatted_prompt, **generation_params)
        elapsed = time.time() - start_time
        
        # 检查生成后GPU状态
        check_gpu_usage()
        
        # 提取响应文本
        if isinstance(output, dict) and "choices" in output and len(output["choices"]) > 0:
            response_text = output["choices"][0].get("text", "").strip()
        else:
            response_text = str(output).strip()
        
        if not response_text:
            response_text = "抱歉，我无法生成有效的响应。"
        
        logger.info(f"⚡ 生成完成: {elapsed:.2f}秒, 长度: {len(response_text)}")
        
        return response_text
        
    except Exception as e:
        logger.error(f"❌ 生成响应错误: {e}")
        return f"生成错误: {str(e)}"

def handler(event):
    """RunPod handler函数"""
    try:
        logger.info("🎯 Handler调用")
        
        # 提取输入
        user_input = event.get("input", {})
        prompt = user_input.get("prompt", "")
        personality = user_input.get("personality", "default")
        
        if not prompt:
            return {
                "output": "请提供有效的提示词",
                "status": "error"
            }
        
        logger.info(f"📝 提示词: {prompt[:50]}...")
        
        # 初始化模型（如果未初始化）
        global model
        if model is None:
            logger.info("🔄 模型未初始化，开始初始化...")
            success = initialize_model()
            if not success:
                return {
                    "output": "模型初始化失败",
                    "status": "error"
                }
        
        # 生成响应
        response = generate_response(prompt, personality)
        
        # 返回标准格式
        result = {
            "output": response,
            "status": "success",
            "model_info": {
                "model_path": model_path,
                "model_type": model_type
            }
        }
        
        logger.info(f"✅ 响应返回: {len(response)}字符")
        return result
        
    except Exception as e:
        logger.error(f"❌ Handler错误: {e}")
        return {
            "output": f"系统错误: {str(e)}",
            "status": "error"
        }

# 启动RunPod serverless
if __name__ == "__main__":
    logger.info("🚀 启动GPU优化RunPod handler...")
    runpod.serverless.start({"handler": handler})