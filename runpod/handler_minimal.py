#!/usr/bin/env python3
"""
最简化的RunPod Handler
解决 "No module named runpod.serverless.start" 问题
"""

import runpod

def handler(job):
    """最简单的处理函数"""
    try:
        # 获取输入
        job_input = job.get("input", {})
        prompt = job_input.get("prompt", "Hello World")
        
        # 返回简单响应
        return {
            "output": f"Echo from RunPod: {prompt}",
            "status": "success"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }

# 使用最简单的启动方式
runpod.serverless.start({"handler": handler}) 