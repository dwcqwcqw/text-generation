#!/usr/bin/env python3
"""
RunPod Handler for Llama GGUF Models
修复 "No module named runpod.serverless.start" 问题
支持 L3.2-8X3B 和 L3.2-8X4B 模型
"""

import runpod
import json
import logging
import os
from llama_cpp import Llama

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局变量存储模型
loaded_models = {}
current_model_path = None

def load_model(model_path: str):
    """加载Llama模型"""
    global loaded_models, current_model_path
    
    try:
        logger.info(f"尝试加载模型: {model_path}")
        
        # 检查文件是否存在
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        # 检查文件大小
        file_size = os.path.getsize(model_path) / (1024**3)  # GB
        logger.info(f"模型文件大小: {file_size:.2f} GB")
        
        # 如果模型已加载，直接返回
        if model_path in loaded_models:
            logger.info("模型已在缓存中，直接使用")
            current_model_path = model_path
            return loaded_models[model_path]
        
        # 加载模型
        logger.info("开始加载模型...")
        model = Llama(
            model_path=model_path,
            n_ctx=2048,  # 上下文长度
            n_batch=512,  # 批处理大小
            n_gpu_layers=-1,  # 使用GPU加速（如果可用）
            verbose=False
        )
        
        # 缓存模型
        loaded_models[model_path] = model
        current_model_path = model_path
        
        logger.info("模型加载成功")
        return model
        
    except Exception as e:
        logger.error(f"加载模型失败: {e}")
        raise e

def generate_text(model, prompt: str, max_tokens: int = 150, temperature: float = 0.7, 
                 top_p: float = 0.9, repeat_penalty: float = 1.05, stop_tokens: list = None):
    """生成文本"""
    try:
        logger.info(f"生成文本 - prompt长度: {len(prompt)}, max_tokens: {max_tokens}")
        
        # 默认停止词
        if stop_tokens is None:
            stop_tokens = ["<|eot_id|>", "<|end_of_text|>", "<|start_header_id|>"]
        
        # 生成文本
        output = model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            repeat_penalty=repeat_penalty,
            stop=stop_tokens,
            echo=False  # 不回显输入
        )
        
        generated_text = output['choices'][0]['text']
        logger.info(f"生成完成 - 输出长度: {len(generated_text)}")
        
        return generated_text.strip()
        
    except Exception as e:
        logger.error(f"生成文本失败: {e}")
        raise e

def handler(event):
    """RunPod处理函数"""
    try:
        logger.info(f"收到请求: {json.dumps(event, indent=2)}")
        
        # 解析输入
        input_data = event.get("input", {})
        
        # 获取参数
        prompt = input_data.get("prompt", "")
        model_path = input_data.get("model_path", "/runpod-volume/text_models/L3.2-8X3B.gguf")
        max_tokens = input_data.get("max_tokens", 150)
        temperature = input_data.get("temperature", 0.7)
        top_p = input_data.get("top_p", 0.9)
        repeat_penalty = input_data.get("repeat_penalty", 1.05)
        stop_tokens = input_data.get("stop", ["<|eot_id|>", "<|end_of_text|>", "<|start_header_id|>"])
        stream = input_data.get("stream", False)
        
        # 验证输入
        if not prompt:
            return {
                "error": "未提供prompt",
                "status": "FAILED"
            }
        
        # 验证模型路径
        allowed_models = {
            "/runpod-volume/text_models/L3.2-8X3B.gguf": "Llama-3.2-8X3B (18.4B)",
            "/runpod-volume/text_models/L3.2-8X4B.gguf": "Llama-3.2-8X4B (21B)"
        }
        
        if model_path not in allowed_models:
            return {
                "error": f"不支持的模型路径: {model_path}。支持的模型: {list(allowed_models.keys())}",
                "status": "FAILED"
            }
        
        # 加载模型
        try:
            model = load_model(model_path)
        except FileNotFoundError as e:
            return {
                "error": str(e),
                "status": "FAILED",
                "suggestion": "请检查模型文件是否存在于指定路径"
            }
        except Exception as e:
            return {
                "error": f"模型加载失败: {str(e)}",
                "status": "FAILED",
                "suggestion": "请检查模型文件格式和系统内存"
            }
        
        # 生成文本
        try:
            generated_text = generate_text(
                model=model,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                repeat_penalty=repeat_penalty,
                stop_tokens=stop_tokens
            )
            
            return {
                "text": generated_text,
                "status": "COMPLETED",
                "model_used": model_path,
                "model_name": allowed_models[model_path],
                "metadata": {
                    "prompt_length": len(prompt),
                    "response_length": len(generated_text),
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "repeat_penalty": repeat_penalty
                }
            }
            
        except Exception as e:
            return {
                "error": f"文本生成失败: {str(e)}",
                "status": "FAILED",
                "suggestion": "请检查输入参数和模型状态"
            }
        
    except Exception as e:
        logger.error(f"Handler错误: {str(e)}")
        return {
            "error": f"处理请求时出错: {str(e)}",
            "status": "FAILED"
        }

def test_handler():
    """测试handler函数"""
    logger.info("开始测试handler...")
    
    test_event = {
        "input": {
            "prompt": "Hello, how are you today?",
            "model_path": "/runpod-volume/text_models/L3.2-8X3B.gguf",
            "max_tokens": 50,
            "temperature": 0.7
        }
    }
    
    result = handler(test_event)
    print("测试结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    # 测试模式
    test_handler()
else:
    # 启动RunPod serverless - 兼容多种版本
    logger.info("🚀 启动RunPod serverless handler...")
    try:
        # 新版本方式
        runpod.serverless.start({"handler": handler})
    except AttributeError:
        try:
            # 备用方式1
            import runpod.serverless as serverless
            serverless.start(handler)
        except Exception:
            try:
                # 备用方式2 - 直接启动
                runpod.start({"handler": handler})
            except Exception as e:
                logger.error(f"无法启动RunPod serverless: {e}")
                # 最简单的方式
                runpod.start(handler) 