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
from typing import Optional, Dict, Any, Tuple, List
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(filename)s :%(lineno)d  %(asctime)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 全局变量
model = None
model_type = None
model_path = None

# 强制设置CUDA环境变量
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
os.environ['GGML_CUDA'] = '1'
    # LLAMA_CUBLAS已弃用，使用GGML_CUDA
os.environ['CMAKE_CUDA_ARCHITECTURES'] = '75;80;86;89'  # 支持多种GPU架构
os.environ['FORCE_CMAKE'] = '1'
os.environ['CMAKE_ARGS'] = '-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75;80;86;89'

# 强制x86_64架构，避免ARM64问题
os.environ['ARCHFLAGS'] = '-arch x86_64'
os.environ['CFLAGS'] = '-march=x86-64'
os.environ['CXXFLAGS'] = '-march=x86-64'

try:
    from llama_cpp import Llama
    try:
        import GPUtil
    except ImportError:
        logger.warning("GPUtil未安装，使用nvidia-smi替代")
        GPUtil = None
except ImportError as e:
    logging.error(f"导入失败: {e}")
    raise

def check_gpu_usage():
    """检查GPU使用情况"""
    try:
        if GPUtil:
            # 使用GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                logger.info(f"🔥 GPU状态: 利用率{gpu.load*100:.0f}%, 显存{gpu.memoryUsed/1024:.1f}/{gpu.memoryTotal/1024:.1f}GB, 温度{gpu.temperature}°C")
                return gpu.memoryTotal / 1024, gpu.memoryUsed / 1024
            else:
                logger.warning("⚠️ 未检测到GPU")
                return None, None
        else:
            # 使用nvidia-smi替代
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
                    return mem_total, mem_used
            logger.warning("⚠️ 无法获取GPU信息")
            return None, None
    except Exception as e:
        logger.error(f"❌ GPU检查失败: {e}")
        return None, None

def find_models() -> List[Tuple[str, float]]:
    """查找可用的GGUF模型"""
    model_dir = Path("/runpod-volume/text_models")
    models = []
    
    if model_dir.exists():
        for model_file in model_dir.glob("*.gguf"):
            size_gb = model_file.stat().st_size / (1024**3)
            models.append((str(model_file), size_gb))
            logger.info(f"📁 发现模型: {model_file} ({size_gb:.1f}GB)")
    
    # 按大小排序，小模型优先
    models.sort(key=lambda x: x[1])
    return models

def load_gguf_model(model_path: str) -> Tuple[Llama, str]:
    """加载GGUF模型，强制GPU模式"""
    try:
        logger.info(f"llama-cpp-python版本: {Llama.__version__ if hasattr(Llama, '__version__') else '未知'}")
        logger.info(f"📂 强制GPU模式加载: {model_path}")
        
        # 检查GPU状态
        mem_total, mem_used = check_gpu_usage()
        
        # 强制所有层到GPU，不管GPU大小
        logger.info(f"🎯 强制所有层到GPU (n_gpu_layers=-1)")
        
        # 根据GPU显存调整配置 - 保守设置避免OOM
        if mem_total and mem_total > 40:  # RTX 4090等高端GPU
            n_ctx = 32768      # 减少上下文长度
            n_batch = 1024     # 中等批处理
        elif mem_total and mem_total > 20:  # L4 GPU等
            n_ctx = 16384      # 使用较小上下文
            n_batch = 512      # 小批处理
        else:
            n_ctx = 8192       # 使用最小上下文
            n_batch = 256      # 最小批处理
        
        logger.info(f"🔧 GPU配置: n_gpu_layers=-1 (全部), n_ctx={n_ctx}, n_batch={n_batch}")
        
        # 强制GPU模式，使用所有可用的优化
        try:
            model = Llama(
                model_path=model_path,
                n_ctx=n_ctx,              # 上下文长度
                n_batch=n_batch,          # 批处理大小
                n_gpu_layers=-1,          # 强制所有层到GPU
                verbose=True,             # 显示详细日志以查看层分配
                n_threads=1,              # 最少CPU线程，专注GPU
                use_mmap=True,            # 使用内存映射
                use_mlock=False,          # 不锁定内存
                f16_kv=True,              # 使用FP16 KV缓存节省显存
                logits_all=False,         # 不计算所有logits节省计算
                # 强制CUDA后端
                main_gpu=0,               # 使用第一个GPU
                tensor_split=None,        # 不分割张量
                rope_scaling_type=None,   # 不使用rope缩放
                rope_freq_base=0.0,       # 使用默认频率基数
                rope_freq_scale=0.0,      # 使用默认频率缩放
            )
        except Exception as gpu_error:
            # 如果GPU加载失败，尝试更保守的设置
            logger.warning(f"⚠️ GPU加载失败，尝试更保守的设置: {gpu_error}")
            logger.info("🔄 尝试减少内存使用...")
            
            model = Llama(
                model_path=model_path,
                n_ctx=4096,               # 最小上下文
                n_batch=128,              # 最小批处理
                n_gpu_layers=-1,          # 仍然尝试GPU
                verbose=True,
                n_threads=1,
                use_mmap=True,
                use_mlock=False,
                f16_kv=True,
                logits_all=False,
                main_gpu=0,
            )
        
        logger.info("✅ 模型GPU加载成功")
        check_gpu_usage()  # 显示加载后的GPU状态
        return model, "gguf"
        
    except Exception as e:
        logger.error(f"❌ GGUF模型加载失败: {e}")
        logger.error("💡 提示：如果是GPU内存不足，请尝试使用更小的模型或重启容器")
        raise e

def initialize_model():
    """初始化模型"""
    global model, model_type, model_path
    
    logger.info("🔄 开始模型初始化...")
    
    # 查找模型
    models = find_models()
    if not models:
        raise Exception("未找到任何GGUF模型文件")
    
    # 如果已经指定了模型路径，使用指定的模型
    if model_path:
        logger.info(f"🎯 使用指定的模型: {model_path}")
        # 验证指定的模型是否存在
        if not os.path.exists(model_path):
            logger.error(f"❌ 指定的模型不存在: {model_path}")
            # 回退到默认选择
            selected_model = models[0]
            model_path = selected_model[0]
            model_size = selected_model[1]
            logger.info(f"🔄 回退到默认模型: {model_path} ({model_size:.1f}GB)")
        else:
            # 获取指定模型的大小信息
            model_size = os.path.getsize(model_path) / (1024**3)  # GB
            logger.info(f"📏 指定模型大小: {model_size:.1f}GB")
            logger.info(f"✅ 确认使用指定模型: {os.path.basename(model_path)}")
    else:
        # 没有指定模型，选择最小的模型（更快加载）
        selected_model = models[0]
        model_path = selected_model[0]
        model_size = selected_model[1]
        logger.info(f"🎯 自动选择模型: {model_path} ({model_size:.1f}GB)")
    
    # 加载模型
    model, model_type = load_gguf_model(model_path)
    
    logger.info(f"✅ 模型初始化完成: {model_path}")
    return True

def format_prompt(prompt: str, persona: str = "default", history: list = None) -> str:
    """格式化提示词，避免重复BOS标记，支持对话历史"""
    
    # 清理输入提示词
    prompt = str(prompt).strip()
    if not prompt:
        prompt = "Hello"
    
    # 根据人格设置系统提示词 - 添加表情和简洁回复要求
    system_prompts = {
        "default": "You are a helpful, intelligent AI assistant for general conversations. 回复尽量的言简意赅，并且灵活的使用各种表情符号来增加亲和力。Keep responses concise and use emojis appropriately.",
        "creative": "You are a creative AI assistant specialized in creative writing, storytelling, and fiction. 回复尽量的言简意赅，并且灵活的使用各种表情符号。Be creative and expressive with emojis.",
        "professional": "You are a professional AI assistant providing formal, structured responses for business and analysis. 回复尽量的言简意赅，适当使用表情符号。Maintain professionalism while being concise.",
        "casual": "You are a friendly, relaxed AI assistant with a conversational style. 回复尽量的言简意赅，并且灵活的使用各种表情符号。Be casual and use lots of emojis!",
        "technical": "You are a technical AI assistant with expertise in programming, technology, and engineering. 回复尽量的言简意赅，并且适当使用表情符号。Be precise and use relevant emojis.",
        "chinese": "你是一个专业的中文AI助手，理解中文文化背景。回复尽量的言简意赅，并且灵活的使用各种表情符号来增加亲和力。"
    }
    
    system_prompt = system_prompts.get(persona, system_prompts["default"])
    
    # 构建对话历史
    conversation = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|>"
    
    # 添加历史对话
    if history:
        for msg in history:
            if isinstance(msg, dict):
                role = msg.get('role', 'user')
                content = str(msg.get('content', '')).strip()
                
                # 跳过空内容或无效内容
                if not content or content == '[object Object]':
                    continue
                    
                if role in ['user', 'assistant']:
                    conversation += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
    
    # 添加当前用户输入
    conversation += f"<|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
    
    return conversation

def generate_response(prompt: str, persona: str = "default", history: list = None, stream: bool = False) -> str:
    """生成AI响应，支持流式输出和对话历史"""
    global model
    
    if not model:
        raise Exception("模型未初始化")
    
    logger.info(f"💭 生成响应 (人格: {persona}, 流式: {stream})")
    logger.info(f"📝 原始输入: '{prompt}'")
    if history:
        logger.info(f"📚 历史记录数量: {len(history)}")
    
    # 清理提示词并包含历史记录
    formatted_prompt = format_prompt(prompt, persona, history)
    logger.info(f"📝 格式化后长度: {len(formatted_prompt)}")
    
    # 检查生成前GPU状态
    check_gpu_usage()
    
    start_time = time.time()
    
    try:
        # 生成响应 - 增加max_tokens以支持更完整的回复
        response = model(
            formatted_prompt,
            max_tokens=512,       # 增加token数量以支持完整回复
            temperature=0.7,
            top_p=0.9,
            top_k=40,
            repeat_penalty=1.1,
            stop=["<|eot_id|>", "<|end_of_text|>", "\n\n---", "<|start_header_id|>"],
            echo=False,           # 不回显输入
            stream=stream         # 支持流式输出
        )
        
        # 处理流式响应
        if stream:
            # 如果是流式响应，返回生成器
            def stream_generator():
                full_response = ""
                for chunk in response:
                    if isinstance(chunk, dict) and 'choices' in chunk:
                        if len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                full_response += content
                                yield content
                    else:
                        content = str(chunk).strip()
                        if content:
                            full_response += content
                            yield content
                
                # 记录完整响应
                generation_time = time.time() - start_time
                check_gpu_usage()
                logger.info(f"⚡ 流式生成完成: {generation_time:.2f}秒")
                logger.info(f"📤 完整响应: '{full_response}' (长度: {len(full_response)})")
            
            return stream_generator()
        else:
            # 非流式响应
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
                response_text = "我理解了您的问题，但目前无法提供具体回答。请尝试重新表述您的问题。😊"
                logger.warning("⚠️ 响应为空，使用默认消息")
            
            return response_text
        
    except Exception as e:
        logger.error(f"❌ 生成响应失败: {e}")
        return f"抱歉，生成响应时出现错误: {str(e)} 😔"

def handler(event):
    """RunPod处理函数 - 支持流式响应和对话历史"""
    global model, model_path
    
    try:
        logger.info("🎯 Handler调用")
        logger.info(f"📥 完整事件: {json.dumps(event, indent=2, ensure_ascii=False)}")
        
        # 获取输入
        input_data = event.get("input", {})
        prompt = input_data.get("prompt", "").strip()
        persona = input_data.get("system_template", input_data.get("persona", "default"))
        requested_model_path = input_data.get("model_path", "")  # 前端指定的模型路径
        history = input_data.get("history", [])  # 对话历史
        stream = input_data.get("stream", False)  # 是否启用流式响应
        
        logger.info(f"📝 提取的提示词: '{prompt}'")
        logger.info(f"👤 人格设置: '{persona}'")
        logger.info(f"🎯 请求的模型: '{requested_model_path}'")
        logger.info(f"🌊 流式响应: {stream}")
        
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
        
        # 生成响应，包含历史记录
        response = generate_response(prompt, persona, history, stream)
        
        # 处理流式响应
        if stream and hasattr(response, '__iter__'):
            # 对于流式响应，我们需要收集所有chunks并返回完整响应
            # 因为RunPod serverless不直接支持流式响应
            full_response = ""
            for chunk in response:
                full_response += chunk
            response = full_response
        
        # 返回RunPod标准格式
        result = {
            "status": "COMPLETED",  # 前端期望的状态
            "output": response,     # 前端期望的输出字段
            "model_info": f"模型: {os.path.basename(model_path) if model_path else 'unknown'}",
            "stream": stream        # 标记是否为流式响应
        }
        
        logger.info(f"✅ 最终返回结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Handler错误: {e}")
        # RunPod格式的错误响应
        error_result = {
            "status": "FAILED",
            "error": f"处理请求时出现错误: {str(e)} 😔",
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