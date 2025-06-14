#!/usr/bin/env python3
"""
RunPod Handler - 修复GPU使用和前端响应问题
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 全局变量
model = None
model_type = None
model_path = None

# 强制设置环境变量 - 使用新的GGML_CUDA
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
os.environ['GGML_CUDA'] = '1'  # 新版本使用GGML_CUDA
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'

def check_gpu_usage():
    """检查GPU使用情况"""
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            gpu_info = result.stdout.strip().split(', ')
            if len(gpu_info) >= 4:
                util = gpu_info[0]
                mem_used = float(gpu_info[1]) / 1024  # MB to GB
                mem_total = float(gpu_info[2]) / 1024  # MB to GB
                temp = gpu_info[3]
                logger.info(f"🔥 GPU状态: 利用率{util}%, 显存{mem_used:.1f}/{mem_total:.1f}GB, 温度{temp}°C")
                return util, mem_used, mem_total, temp
    except Exception as e:
        logger.error(f"GPU状态检查失败: {e}")
    return None, None, None, None

def find_models():
    """查找可用的模型文件"""
    model_dir = "/runpod-volume/text_models"
    models = []
    
    if os.path.exists(model_dir):
        for file in os.listdir(model_dir):
            if file.endswith('.gguf'):
                file_path = os.path.join(model_dir, file)
                file_size = os.path.getsize(file_path) / (1024**3)  # GB
                models.append((file_path, file_size))
                logger.info(f"📁 发现模型: {file_path} ({file_size:.1f}GB)")
    
    return sorted(models, key=lambda x: x[1])  # 按大小排序

def load_gguf_model(model_path: str):
    """使用llama-cpp-python加载GGUF模型，强制使用GPU"""
    try:
        # 导入llama-cpp
        from llama_cpp import Llama
        import llama_cpp
        
        logger.info(f"llama-cpp-python版本: {llama_cpp.__version__}")
        logger.info(f"📂 强制GPU模式加载: {model_path}")
        
        # 检查GPU状态
        check_gpu_usage()
        
        # 根据GPU显存动态设置参数
        _, mem_used, mem_total, _ = check_gpu_usage()
        if mem_total and mem_total > 40:  # L40 GPU有45GB显存
            logger.info(f"🎯 检测到L40 GPU ({mem_total:.1f}GB)，使用全部GPU层和完整上下文")
            n_gpu_layers = -1  # 全部层到GPU
            n_ctx = 131072     # 使用模型的完整上下文长度
            n_batch = 2048     # 大批处理
        elif mem_total and mem_total > 20:  # L4 GPU有22.5GB显存
            logger.info(f"🎯 检测到L4 GPU ({mem_total:.1f}GB)，使用大部分GPU层")
            n_gpu_layers = 25  # 大部分层到GPU
            n_ctx = 65536      # 使用一半上下文
            n_batch = 1024     # 中等批处理
        else:
            logger.info(f"🎯 检测到其他GPU ({mem_total:.1f}GB)，使用适量GPU层")
            n_gpu_layers = 15  # 适量层到GPU
            n_ctx = 32768      # 使用四分之一上下文
            n_batch = 512      # 小批处理
        
        logger.info(f"🔧 GPU配置: n_gpu_layers={n_gpu_layers}, n_ctx={n_ctx}, n_batch={n_batch}")
        
        # 强制GPU模式，不允许CPU回退
        model = Llama(
            model_path=model_path,
            n_ctx=n_ctx,              # 使用完整或适当的上下文长度
            n_batch=n_batch,          # 大批处理大小
            n_gpu_layers=n_gpu_layers, # GPU层数
            verbose=True,             # 显示详细日志以查看层分配
            n_threads=1,              # 最少CPU线程，专注GPU
            use_mmap=True,            # 使用内存映射
            use_mlock=False,          # 不锁定内存
            f16_kv=True,              # 使用FP16 KV缓存节省显存
            logits_all=False,         # 不计算所有logits节省计算
        )
        
        logger.info("✅ 模型GPU加载成功")
        check_gpu_usage()  # 显示加载后的GPU状态
        return model, "gguf"
        
    except Exception as e:
        logger.error(f"❌ GGUF模型加载失败: {e}")
        raise e

def initialize_model():
    """初始化模型"""
    global model, model_type, model_path
    
    logger.info("🔄 开始模型初始化...")
    
    # 查找模型
    models = find_models()
    if not models:
        raise Exception("未找到任何GGUF模型文件")
    
    # 选择最小的模型（更快加载）
    selected_model = models[0]
    model_path = selected_model[0]
    model_size = selected_model[1]
    
    logger.info(f"🎯 选择模型: {model_path} ({model_size:.1f}GB)")
    
    # 加载模型
    model, model_type = load_gguf_model(model_path)
    
    logger.info(f"✅ 模型初始化完成: {model_path}")
    return True

def format_prompt(prompt: str, persona: str = "default") -> str:
    """格式化提示词，避免重复BOS标记"""
    
    # 首先清理可能的重复BOS标记
    prompt = prompt.replace("<|begin_of_text|><|begin_of_text|>", "<|begin_of_text|>")
    prompt = prompt.replace("<|begin_of_text|>", "")  # 先移除所有BOS标记
    prompt = prompt.strip()
    
    # 根据人格设置系统提示词
    system_prompts = {
        "default": "You are a helpful, intelligent AI assistant for general conversations.",
        "creative": "You are a creative AI assistant specialized in creative writing, storytelling, and fiction.",
        "professional": "You are a professional AI assistant providing formal, structured responses for business and analysis.",
        "casual": "You are a friendly, relaxed AI assistant with a conversational style.",
        "technical": "You are a technical AI assistant with expertise in programming, technology, and engineering.",
        "chinese": "你是一个专业的中文AI助手，理解中文文化背景。"
    }
    
    system_prompt = system_prompts.get(persona, system_prompts["default"])
    
    # 使用正确的Llama-3.2格式，只添加一次BOS标记
    formatted_prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>

{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
    
    return formatted_prompt

def generate_response(prompt: str, persona: str = "default") -> str:
    """生成AI响应"""
    global model
    
    if not model:
        raise Exception("模型未初始化")
    
    logger.info(f"💭 生成响应 (人格: {persona})")
    logger.info(f"📝 原始输入: '{prompt}'")
    
    # 清理提示词
    formatted_prompt = format_prompt(prompt, persona)
    logger.info(f"📝 格式化后长度: {len(formatted_prompt)}")
    
    # 检查生成前GPU状态
    check_gpu_usage()
    
    start_time = time.time()
    
    try:
        # 生成响应
        response = model(
            formatted_prompt,
            max_tokens=256,       # 减少token数量
            temperature=0.7,
            top_p=0.9,
            top_k=40,
            repeat_penalty=1.1,
            stop=["<|eot_id|>", "<|end_of_text|>", "\n\n---", "<|start_header_id|>"],
            echo=False,           # 不回显输入
            stream=False
        )
        
        # 提取响应文本
        response_text = ""
        if isinstance(response, dict) and 'choices' in response:
            if len(response['choices']) > 0:
                response_text = response['choices'][0].get('text', '').strip()
        else:
            response_text = str(response).strip()
        
        generation_time = time.time() - start_time
        
        # 检查生成后GPU状态
        check_gpu_usage()
        
        logger.info(f"⚡ 生成完成: {generation_time:.2f}秒")
        logger.info(f"📤 原始响应: '{response_text}'")
        
        # 清理响应文本
        if response_text:
            # 移除可能的格式标记
            response_text = response_text.replace('<|eot_id|>', '').replace('<|end_of_text|>', '').strip()
            logger.info(f"📤 清理后响应: '{response_text}' (长度: {len(response_text)})")
        
        # 如果响应为空，返回默认消息
        if not response_text:
            response_text = "我理解了您的问题，但目前无法提供具体回答。请尝试重新表述您的问题。"
            logger.warning("⚠️ 响应为空，使用默认消息")
        
        return response_text
        
    except Exception as e:
        logger.error(f"❌ 生成响应失败: {e}")
        return f"抱歉，生成响应时出现错误: {str(e)}"

def handler(event):
    """RunPod处理函数"""
    global model, model_path
    
    try:
        logger.info("🎯 Handler调用")
        logger.info(f"📥 完整事件: {json.dumps(event, indent=2, ensure_ascii=False)}")
        
        # 获取输入
        input_data = event.get("input", {})
        prompt = input_data.get("prompt", "").strip()
        persona = input_data.get("persona", "default")
        requested_model_path = input_data.get("model_path", "")  # 前端指定的模型路径
        
        logger.info(f"📝 提取的提示词: '{prompt}'")
        logger.info(f"👤 人格设置: '{persona}'")
        logger.info(f"🎯 请求的模型: '{requested_model_path}'")
        
        if not prompt:
            # RunPod格式的错误响应
            error_result = {
                "status": "FAILED",
                "error": "请提供有效的提示词",
                "output": None
            }
            logger.error(f"❌ 无效输入，返回: {json.dumps(error_result, ensure_ascii=False)}")
            return error_result
        
        # 检查是否需要切换模型
        if requested_model_path and requested_model_path != model_path:
            logger.info(f"🔄 需要切换模型: {model_path} -> {requested_model_path}")
            model = None  # 重置模型，强制重新加载
            model_path = requested_model_path
        
        # 初始化模型（如果需要）
        if not model:
            logger.info("🔄 模型未初始化，开始初始化...")
            initialize_model()
        
        # 生成响应
        response = generate_response(prompt, persona)
        
        # 返回RunPod标准格式
        result = {
            "status": "COMPLETED",  # 前端期望的状态
            "output": response,     # 前端期望的输出字段
            "model_info": f"模型: {os.path.basename(model_path) if model_path else 'unknown'}"
        }
        
        logger.info(f"✅ 最终返回结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Handler错误: {e}")
        # RunPod格式的错误响应
        error_result = {
            "status": "FAILED",
            "error": f"处理请求时出现错误: {str(e)}",
            "output": None
        }
        logger.error(f"❌ 错误返回: {json.dumps(error_result, ensure_ascii=False)}")
        return error_result

if __name__ == "__main__":
    logger.info("🚀 启动GPU优化RunPod handler...")
    
    # 启动时检查GPU
    check_gpu_usage()
    
    # 启动RunPod服务
    runpod.serverless.start({"handler": handler})