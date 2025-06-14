import os
import gc
import json
import runpod
import psutil
from typing import Optional, Dict, Any
import time

# RTX 4090专用配置
RTX4090_VRAM_GB = 24  # RTX 4090有24GB显存
RTX4090_COMPUTE_CAPABILITY = 8.9

# 设置RTX 4090专用环境变量
os.environ.update({
    'GGML_CUDA': '1',
    'CUDA_VISIBLE_DEVICES': '0',
    'CUDA_LAUNCH_BLOCKING': '1',
    'CMAKE_CUDA_ARCHITECTURES': '89',  # RTX 4090的计算能力
})

try:
    import llama_cpp
    LLAMA_CPP_AVAILABLE = True
    print(f"✅ llama_cpp version: {llama_cpp.__version__}")
except ImportError as e:
    LLAMA_CPP_AVAILABLE = False
    print(f"❌ Failed to import llama_cpp: {e}")

class RTX4090ModelManager:
    """RTX 4090专用模型管理器"""
    
    def __init__(self):
        self.current_model = None
        self.current_model_path = None
        self.rtx4090_config = {
            'n_gpu_layers': 60,  # RTX 4090可以处理更多层
            'n_ctx': 32768,      # RTX 4090的大显存支持更大上下文
            'verbose': True,
            'use_mmap': True,
            'use_mlock': False,
            'low_vram': False,   # RTX 4090不需要低显存模式
        }
        
    def get_rtx4090_config(self, model_path: str) -> Dict[str, Any]:
        """根据模型大小调整RTX 4090配置"""
        config = self.rtx4090_config.copy()
        config['model_path'] = model_path
        
        # 根据文件名调整配置
        if "8X3B" in model_path:
            # 较大模型，保守一点
            config['n_gpu_layers'] = 50
            config['n_ctx'] = 16384
        elif "8X4B" in model_path:
            # 更大模型，需要更保守
            config['n_gpu_layers'] = 45
            config['n_ctx'] = 8192
        else:
            # 默认配置适合RTX 4090
            config['n_gpu_layers'] = 55
            config['n_ctx'] = 16384
            
        print(f"🎯 RTX 4090配置: {config}")
        return config
        
    def load_model(self, model_path: str) -> bool:
        """加载模型到RTX 4090"""
        if not LLAMA_CPP_AVAILABLE:
            print("❌ llama_cpp未安装")
            return False
            
        # 如果已经加载了相同模型，直接返回
        if self.current_model and self.current_model_path == model_path:
            print(f"✅ 模型已加载: {model_path}")
            return True
            
        # 清理旧模型
        if self.current_model:
            print("🗑️ 清理旧模型...")
            del self.current_model
            gc.collect()
            
        try:
            print(f"🚀 加载模型到RTX 4090: {model_path}")
            config = self.get_rtx4090_config(model_path)
            
            # 检查文件是否存在
            if not os.path.exists(model_path):
                print(f"❌ 模型文件不存在: {model_path}")
                return False
                
            start_time = time.time()
            self.current_model = llama_cpp.Llama(**config)
            load_time = time.time() - start_time
            
            self.current_model_path = model_path
            print(f"✅ RTX 4090模型加载成功，耗时: {load_time:.2f}秒")
            print(f"📊 GPU层数: {config['n_gpu_layers']}")
            print(f"📊 上下文长度: {config['n_ctx']}")
            
            return True
            
        except Exception as e:
            print(f"❌ RTX 4090模型加载失败: {e}")
            self.current_model = None
            self.current_model_path = None
            return False
            
    def generate_response(self, prompt: str, max_tokens: int = 2048) -> str:
        """使用RTX 4090生成回复"""
        if not self.current_model:
            return "❌ 模型未加载"
            
        try:
            # 清理提示词中的重复BOS标记
            prompt = prompt.replace("<|begin_of_text|><|begin_of_text|>", "<|begin_of_text|>")
            prompt = prompt.replace("<|begin_of_text|>", "")
            
            # 格式化提示词
            formatted_prompt = f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
            
            print(f"🎯 RTX 4090生成开始，最大tokens: {max_tokens}")
            start_time = time.time()
            
            response = self.current_model(
                formatted_prompt,
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9,
                stop=["<|eot_id|>", "<|end_of_text|>"],
                echo=False
            )
            
            generation_time = time.time() - start_time
            
            if response and 'choices' in response and len(response['choices']) > 0:
                text = response['choices'][0]['text'].strip()
                tokens_generated = response['usage']['completion_tokens']
                
                print(f"✅ RTX 4090生成完成")
                print(f"📊 生成时间: {generation_time:.2f}秒")
                print(f"📊 生成tokens: {tokens_generated}")
                print(f"📊 速度: {tokens_generated/generation_time:.2f} tokens/秒")
                
                return text
            else:
                return "❌ RTX 4090生成失败：无有效回复"
                
        except Exception as e:
            print(f"❌ RTX 4090生成错误: {e}")
            return f"❌ 生成错误: {str(e)}"

# 全局RTX 4090模型管理器
rtx4090_manager = RTX4090ModelManager()

def handler(job):
    """RunPod RTX 4090专用处理函数"""
    print("🚀 RTX 4090 Handler启动")
    
    try:
        # 获取输入参数
        job_input = job.get("input", {})
        prompt = job_input.get("prompt", "")
        model_path = job_input.get("model_path", "/runpod-volume/text_models/L3.2-8X3B.gguf")
        max_tokens = job_input.get("max_tokens", 2048)
        
        if not prompt.strip():
            return {
                "status": "FAILED",
                "error": "空提示词"
            }
        
        print(f"📝 提示词: {prompt[:100]}...")
        print(f"📁 模型路径: {model_path}")
        print(f"🎯 最大tokens: {max_tokens}")
        
        # 加载模型到RTX 4090
        if not rtx4090_manager.load_model(model_path):
            return {
                "status": "FAILED",
                "error": "RTX 4090模型加载失败"
            }
        
        # 使用RTX 4090生成回复
        response = rtx4090_manager.generate_response(prompt, max_tokens)
        
        if response.startswith("❌"):
            return {
                "status": "FAILED",
                "error": response
            }
        
        # 获取系统信息
        memory_info = psutil.virtual_memory()
        
        return {
            "status": "COMPLETED",
            "output": {
                "response": response,
                "model_used": model_path,
                "gpu_type": "RTX 4090",
                "system_info": {
                    "memory_usage_percent": memory_info.percent,
                    "available_memory_gb": round(memory_info.available / (1024**3), 2)
                }
            }
        }
        
    except Exception as e:
        print(f"❌ RTX 4090 Handler错误: {e}")
        return {
            "status": "FAILED",
            "error": f"处理错误: {str(e)}"
        }

if __name__ == "__main__":
    print("🚀 启动RTX 4090 RunPod服务器")
    print(f"📊 RTX 4090显存: {RTX4090_VRAM_GB}GB")
    print(f"📊 计算能力: {RTX4090_COMPUTE_CAPABILITY}")
    
    runpod.serverless.start({"handler": handler}) 