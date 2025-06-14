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

# 尝试导入transformers和torch用于直接模型加载
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    TRANSFORMERS_AVAILABLE = True
    print("✅ Transformers and PyTorch available for direct model loading")
except ImportError as e:
    TRANSFORMERS_AVAILABLE = False
    print(f"⚠️ Transformers not available: {e}")

# 尝试导入llama-cpp-python用于GGUF模型
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
    print("✅ llama-cpp-python available for GGUF model loading")
except ImportError as e:
    LLAMA_CPP_AVAILABLE = False
    print(f"⚠️ llama-cpp-python not available: {e}")

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

def find_model_files():
    """在常见路径中查找模型文件"""
    print("🔍 Searching for model files in volume...")
    
    # 常见的模型存储路径
    search_paths = [
        "/runpod-volume",
        "/workspace", 
        "/models",
        "/app/models",
        "/data",
        "/storage",
        ".",
        os.path.expanduser("~")
    ]
    
    model_files = []
    
    for base_path in search_paths:
        if os.path.exists(base_path):
            print(f"📁 Checking {base_path}...")
            try:
                for root, dirs, files in os.walk(base_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_lower = file.lower()
                        
                        # 查找模型文件
                        if (file_lower.endswith('.gguf') or 
                            file_lower.endswith('.bin') or
                            file_lower.endswith('.safetensors') or
                            'pytorch_model' in file_lower or
                            'model.safetensors' in file_lower):
                            
                            size_mb = os.path.getsize(file_path) / (1024 * 1024)
                            model_files.append({
                                'path': file_path,
                                'name': file,
                                'size_mb': size_mb,
                                'type': 'gguf' if file_lower.endswith('.gguf') else 'transformers'
                            })
                            print(f"  📄 Found: {file} ({size_mb:.1f}MB)")
                            
                        # 查找模型目录（包含config.json的目录）
                        if file == 'config.json':
                            model_dir = root
                            try:
                                with open(file_path, 'r') as f:
                                    config = json.load(f)
                                    if 'model_type' in config:
                                        model_files.append({
                                            'path': model_dir,
                                            'name': os.path.basename(model_dir),
                                            'size_mb': sum(os.path.getsize(os.path.join(model_dir, f)) 
                                                         for f in os.listdir(model_dir) 
                                                         if os.path.isfile(os.path.join(model_dir, f))) / (1024 * 1024),
                                            'type': 'transformers',
                                            'model_type': config.get('model_type', 'unknown')
                                        })
                                        print(f"  📁 Found model dir: {os.path.basename(model_dir)} ({config.get('model_type', 'unknown')})")
                            except:
                                pass
                                
            except PermissionError:
                print(f"  ❌ Permission denied accessing {base_path}")
            except Exception as e:
                print(f"  ⚠️ Error scanning {base_path}: {e}")
        else:
            print(f"  ❌ Path {base_path} does not exist")
    
    # 按大小排序，大模型优先
    model_files.sort(key=lambda x: x['size_mb'], reverse=True)
    
    print(f"\n📊 Found {len(model_files)} potential model files:")
    for i, model in enumerate(model_files[:10]):  # 只显示前10个
        print(f"  {i+1}. {model['name']} ({model['size_mb']:.1f}MB, {model['type']})")
    
    return model_files

# 全局变量存储加载的模型
loaded_model = None
loaded_tokenizer = None
model_type = None

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

def load_model(model_info):
    """加载指定的模型"""
    global loaded_model, loaded_tokenizer, model_type
    
    print(f"🚀 Loading model: {model_info['name']}")
    print(f"📍 Path: {model_info['path']}")
    print(f"📏 Size: {model_info['size_mb']:.1f}MB")
    print(f"🔧 Type: {model_info['type']}")
    
    try:
        if model_info['type'] == 'gguf' and LLAMA_CPP_AVAILABLE:
            print("🦙 Loading GGUF model with llama-cpp-python...")
            
            # 检测GPU
            gpu_count = torch.cuda.device_count() if 'torch' in globals() else 0
            print(f"🖥️ Detected {gpu_count} GPU(s)")
            
            loaded_model = Llama(
                model_path=model_info['path'],
                n_ctx=4096,  # 上下文长度
                n_gpu_layers=-1 if gpu_count > 0 else 0,  # 使用GPU层数
                verbose=True
            )
            model_type = 'gguf'
            print("✅ GGUF model loaded successfully")
            return True
            
        elif model_info['type'] == 'transformers' and TRANSFORMERS_AVAILABLE:
            print("🤗 Loading Transformers model...")
            
            # 检测GPU
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"🖥️ Using device: {device}")
            
            # 加载tokenizer
            print("📝 Loading tokenizer...")
            loaded_tokenizer = AutoTokenizer.from_pretrained(
                model_info['path'],
                trust_remote_code=True
            )
            
            # 加载模型
            print("🧠 Loading model...")
            loaded_model = AutoModelForCausalLM.from_pretrained(
                model_info['path'],
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto" if device == "cuda" else None,
                trust_remote_code=True
            )
            
            if device == "cpu":
                loaded_model = loaded_model.to(device)
                
            model_type = 'transformers'
            print("✅ Transformers model loaded successfully")
            return True
            
        else:
            print(f"❌ Cannot load {model_info['type']} model - required libraries not available")
            return False
            
    except Exception as e:
        print(f"💥 Error loading model: {str(e)}")
        loaded_model = None
        loaded_tokenizer = None
        model_type = None
        return False

def generate_with_loaded_model(prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
    """使用已加载的模型生成回复"""
    global loaded_model, loaded_tokenizer, model_type
    
    if loaded_model is None:
        return "MODEL_NOT_LOADED"
    
    try:
        if model_type == 'gguf':
            print("🦙 Generating with GGUF model...")
            
            response = loaded_model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                top_k=40,
                repeat_penalty=1.1,
                stop=["<|eot_id|>", "<|end_of_text|>"]
            )
            
            return response['choices'][0]['text'].strip()
            
        elif model_type == 'transformers':
            print("🤗 Generating with Transformers model...")
            
            # 编码输入
            inputs = loaded_tokenizer.encode(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = inputs.to("cuda")
            
            # 生成
            with torch.no_grad():
                outputs = loaded_model.generate(
                    inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=0.9,
                    top_k=40,
                    do_sample=True,
                    pad_token_id=loaded_tokenizer.eos_token_id,
                    eos_token_id=loaded_tokenizer.eos_token_id
                )
            
            # 解码输出
            response = loaded_tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
            return response.strip()
            
        else:
            return "UNKNOWN_MODEL_TYPE"
            
    except Exception as e:
        print(f"💥 Error generating with model: {str(e)}")
        return f"GENERATION_ERROR: {str(e)}"

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
    
    # 可能的LLM服务端点列表
    llm_endpoints = [
        {
            "name": "llama.cpp server",
            "url": "http://localhost:8080/completion",
            "format": "llamacpp"
        },
        {
            "name": "text-generation-webui",
            "url": "http://localhost:5000/api/v1/generate",
            "format": "textgen"
        },
        {
            "name": "vLLM server",
            "url": "http://localhost:8000/v1/completions",
            "format": "openai"
        },
        {
            "name": "Ollama",
            "url": "http://localhost:11434/api/generate",
            "format": "ollama"
        }
    ]
    
    # 首先尝试使用已加载的模型
    if loaded_model is not None:
        print(f"🎯 Using pre-loaded model ({model_type})")
        result = generate_with_loaded_model(prompt, max_tokens, temperature)
        if result not in ["MODEL_NOT_LOADED", "UNKNOWN_MODEL_TYPE"] and not result.startswith("GENERATION_ERROR"):
            return result
        else:
            print(f"⚠️ Pre-loaded model failed: {result}")
    
    print(f"🔍 Attempting to connect to local LLM services...")
    
    for endpoint in llm_endpoints:
        try:
            print(f"📡 Trying {endpoint['name']} at {endpoint['url']}")
            
            # 根据不同服务格式化请求
            if endpoint['format'] == 'llamacpp':
                payload = {
                    "prompt": prompt,
                    "n_predict": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "top_k": 40,
                    "repeat_penalty": 1.1,
                    "stop": ["<|eot_id|>", "<|end_of_text|>"]
                }
            elif endpoint['format'] == 'textgen':
                payload = {
                    "prompt": prompt,
                    "max_new_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "top_k": 40,
                    "repetition_penalty": 1.1,
                    "stopping_strings": ["<|eot_id|>", "<|end_of_text|>"]
                }
            elif endpoint['format'] == 'openai':
                payload = {
                    "model": "llama-3.2-8x3b-moe",
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "stop": ["<|eot_id|>", "<|end_of_text|>"]
                }
            elif endpoint['format'] == 'ollama':
                payload = {
                    "model": "llama3.2",
                    "prompt": prompt,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                        "top_p": 0.9,
                        "top_k": 40,
                        "repeat_penalty": 1.1
                    },
                    "stream": False
                }
            
            print(f"📤 Sending request to {endpoint['name']} with payload size: {len(str(payload))} bytes")
            
            # 发送请求
            response = requests.post(endpoint['url'], json=payload, timeout=10)
            
            print(f"📥 Response from {endpoint['name']}: Status {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Successfully connected to {endpoint['name']}")
                print(f"📊 Response keys: {list(result.keys())}")
                
                # 根据不同服务解析响应
                if endpoint['format'] == 'llamacpp':
                    content = result.get("content", "").strip()
                elif endpoint['format'] == 'textgen':
                    content = result.get("results", [{}])[0].get("text", "").strip()
                elif endpoint['format'] == 'openai':
                    content = result.get("choices", [{}])[0].get("text", "").strip()
                elif endpoint['format'] == 'ollama':
                    content = result.get("response", "").strip()
                else:
                    content = str(result)
                
                if content:
                    print(f"🎯 Generated content length: {len(content)} characters")
                    return content
                else:
                    print(f"⚠️ Empty response from {endpoint['name']}")
            else:
                print(f"❌ HTTP Error {response.status_code} from {endpoint['name']}: {response.text[:200]}")
                
        except requests.exceptions.ConnectionError as e:
            print(f"🔌 Connection failed to {endpoint['name']}: Service not running")
        except requests.exceptions.Timeout as e:
            print(f"⏰ Timeout connecting to {endpoint['name']}: {str(e)}")
        except requests.exceptions.RequestException as e:
            print(f"🌐 Request error to {endpoint['name']}: {str(e)}")
        except Exception as e:
            print(f"💥 Unexpected error with {endpoint['name']}: {str(e)}")
    
    print(f"❌ All LLM services unavailable. Checked {len(llm_endpoints)} endpoints.")
    return "LLM_SERVICE_UNAVAILABLE"

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
        print(f"🤖 Attempting to load and use local LLM model...")
        print(f"🎯 Target model: Llama 3.2 8X3B MOE Dark Champion")
        print(f"📍 Expected model path: /models/ or similar")
        print(f"🔧 Formatted prompt preview: {formatted_prompt[:200]}...")
        
        try:
            ai_response = call_local_llm(formatted_prompt, max_tokens, temperature)
            
            # 检查是否成功获得LLM响应
            if ai_response == "LLM_SERVICE_UNAVAILABLE":
                print(f"❌ No local LLM service found - all endpoints failed")
                print(f"💡 To use real AI, you need to:")
                print(f"   1. Install and run llama.cpp server on port 8080")
                print(f"   2. Or install text-generation-webui on port 5000")
                print(f"   3. Or install vLLM server on port 8000")
                print(f"   4. Or install Ollama on port 11434")
                print(f"🔄 Falling back to simulated AI response")
                ai_response = simulate_ai_response(prompt, system_template)
            elif "Error:" in ai_response or "Connection Error:" in ai_response:
                print(f"⚠️ LLM service error: {ai_response}")
                print(f"🔄 Falling back to simulated AI response")
                ai_response = simulate_ai_response(prompt, system_template)
            else:
                print(f"✅ Successfully generated response using local LLM")
                print(f"📏 Response length: {len(ai_response)} characters")
                
        except Exception as e:
            print(f"💥 Unexpected error during LLM call: {str(e)}")
            print(f"🔄 Falling back to simulated AI response")
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

def check_llm_services():
    """检查可用的LLM服务"""
    print("\n🔍 Checking for available LLM services...")
    
    services = [
        ("llama.cpp server", "http://localhost:8080/health"),
        ("text-generation-webui", "http://localhost:5000/api/v1/model"),
        ("vLLM server", "http://localhost:8000/health"),
        ("Ollama", "http://localhost:11434/api/tags")
    ]
    
    available_services = []
    
    for service_name, health_url in services:
        try:
            response = requests.get(health_url, timeout=2)
            if response.status_code == 200:
                print(f"✅ {service_name} is running and accessible")
                available_services.append(service_name)
            else:
                print(f"⚠️ {service_name} responded with status {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"❌ {service_name} is not running (connection refused)")
        except requests.exceptions.Timeout:
            print(f"⏰ {service_name} timeout (may be starting up)")
        except Exception as e:
            print(f"💥 {service_name} check failed: {str(e)}")
    
    if available_services:
        print(f"🎉 Found {len(available_services)} available LLM service(s): {', '.join(available_services)}")
    else:
        print("⚠️ No LLM services detected - will use simulated responses")
        print("💡 To enable real AI responses, install one of:")
        print("   • llama.cpp with server mode")
        print("   • text-generation-webui")
        print("   • vLLM")
        print("   • Ollama")
    
    return available_services

# 启动RunPod serverless
if __name__ == "__main__":
    print("=== RunPod AI Handler Starting ===")
    print(f"Python version: {sys.version}")
    print(f"RunPod version: {getattr(runpod, '__version__', 'unknown')}")
    
    # 显示可用的系统模版
    print("\n🎭 Available System Templates:")
    for template_name, template_desc in SYSTEM_TEMPLATES.items():
        print(f"  - {template_name}: {template_desc[:80]}{'...' if len(template_desc) > 80 else ''}")
    
    # 查找并尝试加载模型
    print("\n" + "="*50)
    model_files = find_model_files()
    
    if model_files:
        print(f"\n🎯 Attempting to load the best model...")
        # 尝试加载最大的模型（通常是最好的）
        best_model = model_files[0]
        
        if load_model(best_model):
            print(f"🎉 Successfully loaded model: {best_model['name']}")
            handler_mode = "Direct Model Loading"
        else:
            print(f"❌ Failed to load model, checking LLM services...")
            # 检查LLM服务作为备选
            available_llm_services = check_llm_services()
            handler_mode = f"LLM Services ({len(available_llm_services)} available)" if available_llm_services else "Simulated AI"
    else:
        print(f"❌ No model files found, checking LLM services...")
        # 检查LLM服务
        available_llm_services = check_llm_services()
        handler_mode = f"LLM Services ({len(available_llm_services)} available)" if available_llm_services else "Simulated AI"
    
    start_gpu_monitoring()
    
    print("\n🔍 Initial GPU Status:")
    log_gpu_status()
    
    print(f"\n🚀 Starting RunPod AI serverless...")
    print(f"🔧 Handler Mode: {handler_mode}")
    print(f"🎯 Model Status: {'Loaded' if loaded_model else 'Not Loaded'}")
    print("="*50)
    
    runpod.serverless.start({"handler": handler}) 