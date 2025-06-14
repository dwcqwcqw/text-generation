#!/usr/bin/env python3
"""
RunPod Handler - 使用最新的API格式
基于官方文档: https://docs.runpod.io/serverless/workers/handler-functions
"""

import runpod

def handler(job):
    """
    RunPod serverless handler function
    参数 job 包含: {"id": "job_id", "input": {...}}
    """
    try:
        # 获取输入数据
        job_input = job["input"]
        prompt = job_input.get("prompt", "Hello World")
        
        # 处理请求并返回结果
        result = f"Echo from RunPod: {prompt}"
        
        # 直接返回结果，RunPod会自动包装
        return result
        
    except Exception as e:
        # 返回错误信息
        return {"error": str(e)}

# 启动RunPod serverless
runpod.serverless.start({"handler": handler}) 