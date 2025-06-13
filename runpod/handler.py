import runpod
import os
import json
from llama_cpp import Llama
from typing import Dict, Any

# 全局变量存储模型实例
models = {}

def load_model(model_path: str) -> Llama:
    """加载模型，如果已加载则返回缓存的模型"""
    if model_path not in models:
        print(f"Loading model: {model_path}")
        models[model_path] = Llama(
            model_path=model_path,
            n_ctx=4096,  # 上下文长度
            n_threads=8,  # CPU线程数
            n_gpu_layers=-1,  # 使用GPU
            verbose=False
        )
        print(f"Model loaded: {model_path}")
    return models[model_path]

def generate_text(
    prompt: str,
    model_path: str,
    max_tokens: int = 1000,
    temperature: float = 0.7,
    top_p: float = 0.9,
    repeat_penalty: float = 1.1,
    stop: list = None
) -> str:
    """生成文本响应"""
    try:
        # 加载模型
        llm = load_model(model_path)
        
        # 设置停止词
        if stop is None:
            stop = ["User:", "Human:", "\n\n"]
        
        # 生成文本
        response = llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            repeat_penalty=repeat_penalty,
            stop=stop,
            echo=False
        )
        
        # 提取生成的文本
        generated_text = response['choices'][0]['text'].strip()
        
        return generated_text
        
    except Exception as e:
        print(f"Generation error: {e}")
        return f"Error generating response: {str(e)}"

def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """RunPod处理函数"""
    try:
        # 获取输入参数
        job_input = event.get("input", {})
        
        prompt = job_input.get("prompt", "")
        model_path = job_input.get("model_path", "/runpod-volume/text_models/L3.2-8X3B.gguf")
        max_tokens = job_input.get("max_tokens", 1000)
        temperature = job_input.get("temperature", 0.7)
        top_p = job_input.get("top_p", 0.9)
        repeat_penalty = job_input.get("repeat_penalty", 1.1)
        stop = job_input.get("stop", ["User:", "Human:", "\n\n"])
        
        if not prompt:
            return {"error": "No prompt provided"}
        
        # 检查模型文件是否存在
        if not os.path.exists(model_path):
            return {"error": f"Model file not found: {model_path}"}
        
        # 生成响应
        generated_text = generate_text(
            prompt=prompt,
            model_path=model_path,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            repeat_penalty=repeat_penalty,
            stop=stop
        )
        
        return {
            "text": generated_text,
            "model_path": model_path,
            "prompt_length": len(prompt),
            "response_length": len(generated_text)
        }
        
    except Exception as e:
        print(f"Handler error: {e}")
        return {"error": str(e)}

# 启动RunPod serverless
if __name__ == "__main__":
    runpod.serverless.start({"handler": handler}) 