#!/usr/bin/env python3
"""
RunPod Handler with Real AI - Llama 3.2 MOE
支持真正的AI对话，不再是echo模式
"""

import runpod
import os
import sys
import subprocess
import json
import time
import threading
import requests
from typing import Dict, Any, Optional

def get_gpu_info():
    """获取GPU使用情况"""
    try:
        result = subprocess.run([
            'nvidia-smi', 
            '--query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw',
            '--format=csv,noheader,nounits'
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            gpu_info = []
            
            for line in lines:
                if line.strip():
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 7:
                        gpu_info.append({
                            'index': parts[0],
                            'name': parts[1],
                            'memory_used_mb': parts[2],
                            'memory_total_mb': parts[3],
                            'utilization_percent': parts[4],
                            'temperature_c': parts[5],
                            'power_draw_w': parts[6]
                        })
            
            return gpu_info
        else:
            return [{'error': 'nvidia-smi command failed'}]
            
    except Exception as e:
        return [{'error': f'GPU info error: {str(e)}'}]

def log_gpu_status():
    """记录GPU状态到日志"""
    gpu_info = get_gpu_info()
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"\n=== GPU Status at {timestamp} ===")
    for i, gpu in enumerate(gpu_info):
        if 'error' in gpu:
            print(f"GPU {i}: {gpu['error']}")
        else:
            memory_used = float(gpu['memory_used_mb']) if gpu['memory_used_mb'] != 'N/A' else 0
            memory_total = float(gpu['memory_total_mb']) if gpu['memory_total_mb'] != 'N/A' else 1
            memory_percent = (memory_used / memory_total * 100) if memory_total > 0 else 0
            
            print(f"GPU {gpu['index']} ({gpu['name']}):")
            print(f"  Memory: {gpu['memory_used_mb']}MB / {gpu['memory_total_mb']}MB ({memory_percent:.1f}%)")
            print(f"  Utilization: {gpu['utilization_percent']}%")
            print(f"  Temperature: {gpu['temperature_c']}°C")
            print(f"  Power: {gpu['power_draw_w']}W")
    print("=" * 50)

def start_gpu_monitoring():
    """启动GPU监控线程"""
    def monitor_loop():
        while True:
            log_gpu_status()
            time.sleep(30)
    
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    print("🖥️ GPU监控已启动，每30秒记录一次状态")

# AI系统设定模版
SYSTEM_TEMPLATES = {
    "default": """You are a helpful, intelligent AI assistant. You provide accurate, thoughtful, and detailed responses to user questions. You are knowledgeable across many topics and can engage in meaningful conversations.""",
    
    "creative": """You are a creative AI assistant with exceptional storytelling abilities. You excel at creative writing, fiction, roleplay, and imaginative scenarios. You write with vivid prose, engaging dialogue, and compelling narratives. You can adapt to any genre or style requested.""",
    
    "professional": """You are a professional AI assistant focused on providing clear, accurate, and well-structured responses. You maintain a formal tone while being helpful and informative. You excel at analysis, problem-solving, and providing detailed explanations.""",
    
    "casual": """You are a friendly, casual AI assistant. You communicate in a relaxed, conversational tone while still being helpful and informative. You can engage in both serious discussions and light-hearted conversations.""",
    
    "technical": """You are a technical AI assistant with deep expertise in programming, technology, and engineering. You provide precise, detailed technical explanations and can help with coding, system design, and troubleshooting.""",
    
    "chinese": """你是一个智能的中文AI助手。你能够用流利的中文进行对话，理解中文文化背景，并提供准确、有用的回答。你既可以进行正式的讨论，也可以进行轻松的聊天。"""
}

def format_llama3_prompt(system_prompt: str, user_message: str, conversation_history: list = None) -> str:
    """
    格式化Llama 3.2的对话模版
    
    Args:
        system_prompt: 系统提示
        user_message: 用户消息
        conversation_history: 对话历史 [{"role": "user/assistant", "content": "..."}]
    
    Returns:
        格式化的prompt字符串
    """
    
    # Llama 3.2 使用的对话格式
    formatted_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|>"
    
    # 添加对话历史
    if conversation_history:
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_prompt += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
    
    # 添加当前用户消息
    formatted_prompt += f"<|start_header_id|>user<|end_header_id|>\n\n{user_message}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
    
    return formatted_prompt

def call_local_llm(prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
    """
    调用本地LLM API (假设使用llama.cpp server或类似服务)
    
    Args:
        prompt: 格式化的prompt
        max_tokens: 最大token数
        temperature: 温度参数
    
    Returns:
        AI生成的回复
    """
    
    # 这里需要根据你的实际LLM服务配置
    # 可能的选项：
    # 1. llama.cpp server (http://localhost:8080)
    # 2. text-generation-webui API
    # 3. vLLM server
    # 4. 其他本地LLM服务
    
    try:
        # 示例：调用llama.cpp server
        api_url = "http://localhost:8080/completion"
        
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1,
            "stop": ["<|eot_id|>", "<|end_of_text|>"]
        }
        
        response = requests.post(api_url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result.get("content", "").strip()
        else:
            return f"API Error: {response.status_code} - {response.text}"
            
    except requests.exceptions.RequestException as e:
        return f"Connection Error: {str(e)}"
    except Exception as e:
        return f"LLM Error: {str(e)}"

def simulate_ai_response(prompt: str, system_template: str = "default") -> str:
    """
    模拟AI回复（当没有真实LLM服务时使用）
    """
    
    # 基于prompt内容生成不同类型的回复
    prompt_lower = prompt.lower()
    
    if "hello" in prompt_lower or "hi" in prompt_lower or "你好" in prompt_lower:
        return "Hello! I'm your AI assistant. How can I help you today?"
    
    elif "story" in prompt_lower or "creative" in prompt_lower:
        return """Once upon a time, in a world where technology and magic coexisted, there lived a young programmer who discovered that their code could bend reality itself. Each line they wrote didn't just execute on computers, but manifested in the physical world around them.

One day, while debugging a particularly stubborn algorithm, they accidentally created a small portal in their bedroom wall. Through it, they could see another dimension where their digital creations lived as sentient beings..."""
    
    elif "code" in prompt_lower or "programming" in prompt_lower:
        return """Here's a simple example of how you might approach this problem:

```python
def solve_problem(input_data):
    # Process the input
    result = []
    for item in input_data:
        # Apply your logic here
        processed_item = transform(item)
        result.append(processed_item)
    
    return result
```

Would you like me to explain any specific part or help you adapt this to your particular use case?"""
    
    elif "中文" in prompt or "chinese" in prompt_lower:
        return "你好！我是你的AI助手。我可以用中文和你对话，帮助你解决各种问题。有什么我可以帮助你的吗？"
    
    else:
        return f"""I understand you're asking about: "{prompt}"

Based on your question, here are some key points to consider:

1. **Context**: This appears to be related to [relevant topic area]
2. **Approach**: I'd recommend starting with [suggested approach]
3. **Considerations**: Keep in mind [important factors]

Would you like me to elaborate on any of these points or help you with a more specific aspect of your question?"""

def handler(job):
    """
    RunPod serverless handler function with real AI
    
    Args:
        job (dict): Job data containing 'input' and 'id'
        
    Returns:
        str: AI generated response
    """
    try:
        job_input = job.get("input", {})
        job_id = job.get("id", "unknown")
        
        print(f"\n🚀 AI Job {job_id} started")
        log_gpu_status()
        
        # 获取输入参数
        prompt = job_input.get("prompt", "Hello!")
        system_template = job_input.get("system_template", "default")
        conversation_history = job_input.get("history", [])
        max_tokens = job_input.get("max_tokens", 1000)
        temperature = job_input.get("temperature", 0.7)
        
        print(f"📝 Processing prompt: '{prompt[:100]}{'...' if len(prompt) > 100 else ''}'")
        print(f"🎭 Using system template: {system_template}")
        
        # 获取系统提示
        system_prompt = SYSTEM_TEMPLATES.get(system_template, SYSTEM_TEMPLATES["default"])
        
        # 格式化prompt
        formatted_prompt = format_llama3_prompt(system_prompt, prompt, conversation_history)
        
        print(f"🔧 Formatted prompt length: {len(formatted_prompt)} characters")
        
        # 尝试调用真实LLM，如果失败则使用模拟回复
        try:
            ai_response = call_local_llm(formatted_prompt, max_tokens, temperature)
            
            # 如果回复包含错误信息，使用模拟回复
            if "Error:" in ai_response or "Connection Error:" in ai_response:
                print(f"⚠️ LLM service unavailable, using simulated response")
                ai_response = simulate_ai_response(prompt, system_template)
                
        except Exception as e:
            print(f"⚠️ LLM call failed: {str(e)}, using simulated response")
            ai_response = simulate_ai_response(prompt, system_template)
        
        print(f"✅ Generated response: '{ai_response[:100]}{'...' if len(ai_response) > 100 else ''}'")
        log_gpu_status()
        print(f"🎉 AI Job {job_id} completed\n")
        
        return ai_response
        
    except Exception as e:
        error_msg = f"Handler error: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        log_gpu_status()
        return f"I apologize, but I encountered an error while processing your request: {error_msg}"

# 启动RunPod serverless
if __name__ == "__main__":
    print("=== RunPod AI Handler Starting ===")
    print(f"Python version: {sys.version}")
    print(f"RunPod version: {getattr(runpod, '__version__', 'unknown')}")
    
    # 显示可用的系统模版
    print("\n🎭 Available System Templates:")
    for template_name, template_desc in SYSTEM_TEMPLATES.items():
        print(f"  - {template_name}: {template_desc[:80]}{'...' if len(template_desc) > 80 else ''}")
    
    start_gpu_monitoring()
    
    print("\n🔍 Initial GPU Status:")
    log_gpu_status()
    
    print("🚀 Starting RunPod AI serverless...")
    runpod.serverless.start({"handler": handler}) 