import runpod
import json
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# 全局变量存储模型
model = None
tokenizer = None

def initialize_model():
    """初始化模型"""
    global model, tokenizer
    
    try:
        # 使用较小的模型进行测试
        model_name = "microsoft/DialoGPT-medium"
        
        print(f"Loading model: {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        
        # 设置pad_token
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
            
        print("Model loaded successfully")
        return True
    except Exception as e:
        print(f"Error loading model: {str(e)}")
        return False

def handler(event):
    """RunPod处理函数"""
    try:
        # 获取输入
        input_data = event.get("input", {})
        message = input_data.get("message", "")
        model_name = input_data.get("model", "llama3.2-1b")
        
        if not message:
            return {"error": "No message provided"}
        
        # 确保模型已加载
        global model, tokenizer
        if model is None or tokenizer is None:
            if not initialize_model():
                return {"error": "Failed to load model"}
        
        # 生成响应
        inputs = tokenizer.encode(message + tokenizer.eos_token, return_tensors="pt")
        
        with torch.no_grad():
            outputs = model.generate(
                inputs,
                max_length=inputs.shape[1] + 100,
                num_return_sequences=1,
                do_sample=True,
                temperature=0.7,
                pad_token_id=tokenizer.eos_token_id
            )
        
        response = tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
        
        return {
            "response": response.strip(),
            "model": model_name,
            "status": "success"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }

# 预加载模型
if __name__ == "__main__":
    initialize_model()

# 启动RunPod服务
runpod.serverless.start({"handler": handler}) 