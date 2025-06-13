import runpod
import json
import logging
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局变量存储模型
model = None
tokenizer = None
current_model = None

def initialize_model(model_name="microsoft/DialoGPT-medium"):
    """初始化模型"""
    global model, tokenizer, current_model
    
    try:
        logger.info(f"Initializing model: {model_name}")
        
        # 如果已经加载了相同模型，直接返回
        if current_model == model_name and model is not None:
            logger.info("Model already loaded")
            return True
        
        # 加载tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            model_name, 
            padding_side='left',
            trust_remote_code=True
        )
        
        # 加载模型
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
            trust_remote_code=True
        )
        
        # 设置pad_token
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
            tokenizer.pad_token_id = tokenizer.eos_token_id
        
        current_model = model_name
        logger.info("Model initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing model {model_name}: {str(e)}")
        # 回退到更简单的模型
        if model_name != "gpt2":
            logger.info("Falling back to GPT-2")
            return initialize_model("gpt2")
        return False

def generate_response(prompt, max_length=100, temperature=0.7):
    """生成响应"""
    global model, tokenizer
    
    try:
        if model is None or tokenizer is None:
            if not initialize_model():
                return "Error: Model initialization failed"
        
        # 编码输入
        inputs = tokenizer.encode(prompt, return_tensors="pt")
        
        # 设置注意力掩码
        attention_mask = torch.ones(inputs.shape, dtype=torch.long)
        
        # 生成响应
        with torch.no_grad():
            outputs = model.generate(
                inputs,
                attention_mask=attention_mask,
                max_length=min(max_length, inputs.shape[1] + 50),
                temperature=temperature,
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                no_repeat_ngram_size=2
            )
        
        # 解码响应
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # 移除原始提示，只返回生成的部分
        if response.startswith(prompt):
            response = response[len(prompt):].strip()
        
        return response if response else "I understand. Please tell me more."
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return f"Sorry, I encountered an error: {str(e)}"

def handler(event):
    """RunPod处理函数"""
    try:
        logger.info(f"Received event: {event}")
        
        # 解析输入
        input_data = event.get("input", {})
        
        # 获取参数
        prompt = input_data.get("prompt", "")
        model_name = input_data.get("model", "microsoft/DialoGPT-medium")
        max_length = input_data.get("max_length", 100)
        temperature = input_data.get("temperature", 0.7)
        
        # 验证输入
        if not prompt:
            return {
                "error": "No prompt provided",
                "status": "error"
            }
        
        # 如果需要切换模型
        global current_model
        if model_name != current_model:
            if not initialize_model(model_name):
                # 如果指定模型失败，使用默认模型
                model_name = "microsoft/DialoGPT-medium"
                if not initialize_model(model_name):
                    return {
                        "error": "Failed to initialize any model",
                        "status": "error"
                    }
        
        # 生成响应
        response = generate_response(prompt, max_length, temperature)
        
        return {
            "output": response,
            "model_used": current_model,
            "status": "success",
            "metadata": {
                "prompt_length": len(prompt),
                "response_length": len(response),
                "temperature": temperature,
                "max_length": max_length
            }
        }
        
    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        return {
            "error": str(e),
            "status": "error"
        }

# 初始化模型（可选）
if __name__ == "__main__":
    # 预加载模型
    initialize_model()
    
    # 测试
    test_event = {
        "input": {
            "prompt": "Hello, how are you?",
            "model": "microsoft/DialoGPT-medium"
        }
    }
    
    result = handler(test_event)
    print(json.dumps(result, indent=2))

# 启动RunPod服务
runpod.serverless.start({"handler": handler}) 