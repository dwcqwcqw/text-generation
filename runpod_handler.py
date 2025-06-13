import runpod
import json
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(event):
    """
    RunPod handler函数
    处理来自前端的请求
    """
    try:
        # 获取输入参数
        input_data = event.get("input", {})
        prompt = input_data.get("prompt", "Hello, how are you?")
        max_tokens = input_data.get("max_tokens", 100)
        model_path = input_data.get("model_path", "/runpod-volume/text_models/L3.2-8X3B.gguf")
        
        logger.info(f"收到请求 - prompt: {prompt[:50]}..., model: {model_path}")
        
        # 检查模型文件是否存在
        import os
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        # 这里应该是你的模型推理代码
        # 目前返回一个示例响应
        response_text = f"这是对 '{prompt}' 的回复 (使用模型: {model_path})"
        
        return {
            "text": response_text,
            "model_used": model_path,
            "tokens_generated": len(response_text.split())
        }
        
    except Exception as e:
        logger.error(f"处理请求时出错: {e}")
        return {"error": str(e)}

# 启动RunPod serverless
if __name__ == "__main__":
    logger.info("🚀 启动RunPod serverless handler...")
    runpod.serverless.start({"handler": handler})