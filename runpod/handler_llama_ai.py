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
    """强制GPU模式加载GGUF模型"""
    try:
        from llama_cpp import Llama
        import llama_cpp
        
        logger.info(f"🚀 llama-cpp-python版本: {llama_cpp.__version__}")
        logger.info(f"📂 强制GPU模式加载: {model_path}")
        
        # 检查GPU
        util, mem_used, mem_total, temp = check_gpu_usage()
        if mem_total and mem_total > 40:  # L40 GPU
            logger.info(f"🎯 检测到L40 GPU ({mem_total:.1f}GB)，使用全部GPU层")
            n_gpu_layers = -1  # 全部层到GPU
        else:
            logger.info(f"🎯 使用默认GPU配置")
            n_gpu_layers = 32  # 大部分层到GPU
        
        # 强制GPU模式参数 - 使用更激进的设置
        model = Llama(
            model_path=model_path,
            n_ctx=2048,           # 减少上下文窗口
            n_batch=512,          # 减少批处理大小
            n_gpu_layers=n_gpu_layers,  # 强制GPU层数
            verbose=True,         # 开启详细日志查看层分配
            n_threads=1,          # 最少CPU线程
            use_mmap=True,
            use_mlock=False,
            f16_kv=True,          # 使用半精度
            logits_all=False,     # 不计算所有logits
        )
        
        logger.info("✅ 模型GPU加载成功")
        check_gpu_usage()  # 检查加载后的GPU状态
        return model, "gguf"
        
    except Exception as e:
        logger.error(f"❌ GGUF模型加载失败: {e}")
        raise

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

def clean_prompt(prompt: str) -> str:
    """清理提示词，避免重复标记"""
    # 移除可能的重复标记
    prompt = prompt.strip()
    
    # 如果已经有开始标记，直接返回
    if '<|begin_of_text|>' in prompt:
        logger.info("📝 提示词已包含格式标记，直接使用")
        return prompt
    
    # 添加标准格式
    formatted = f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
    logger.info(f"📝 格式化提示词: {formatted[:100]}...")
    return formatted

def generate_response(prompt: str, persona: str = "default") -> str:
    """生成AI响应"""
    global model
    
    if not model:
        raise Exception("模型未初始化")
    
    logger.info(f"💭 生成响应 (人格: {persona})")
    logger.info(f"📝 原始输入: '{prompt}'")
    
    # 清理提示词
    formatted_prompt = clean_prompt(prompt)
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
    global model
    
    try:
        logger.info("🎯 Handler调用")
        logger.info(f"📥 完整事件: {json.dumps(event, indent=2, ensure_ascii=False)}")
        
        # 获取输入
        input_data = event.get("input", {})
        prompt = input_data.get("prompt", "").strip()
        persona = input_data.get("persona", "default")
        
        logger.info(f"📝 提取的提示词: '{prompt}'")
        logger.info(f"👤 人格设置: '{persona}'")
        
        if not prompt:
            # RunPod格式的错误响应
            error_result = {
                "status": "FAILED",
                "error": "请提供有效的提示词",
                "output": None
            }
            logger.error(f"❌ 无效输入，返回: {json.dumps(error_result, ensure_ascii=False)}")
            return error_result
        
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