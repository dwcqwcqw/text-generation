#!/usr/bin/env python3
"""
RunPod Handler for version 1.7.11
基于最新的RunPod Python SDK
"""

import runpod
import os
import sys

def handler(job):
    """
    RunPod serverless handler function
    
    Args:
        job (dict): Job data containing 'input' and 'id'
        
    Returns:
        Any: The result to be returned to the client
    """
    try:
        # 获取job输入
        job_input = job.get("input", {})
        job_id = job.get("id", "unknown")
        
        # 获取prompt
        prompt = job_input.get("prompt", "Hello from RunPod!")
        
        # 简单的echo响应
        response = f"RunPod Echo (v1.7.11): {prompt}"
        
        # 记录日志
        print(f"Job {job_id}: Processing prompt '{prompt}'")
        print(f"Job {job_id}: Returning response '{response}'")
        
        # 直接返回字符串，RunPod会自动包装
        return response
        
    except Exception as e:
        error_msg = f"Handler error: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {"error": error_msg}

# 启动RunPod serverless
if __name__ == "__main__":
    print("=== RunPod Handler v1.7.11 Starting ===")
    print(f"Python version: {sys.version}")
    print(f"RunPod version: {getattr(runpod, '__version__', 'unknown')}")
    
    # 启动serverless
    runpod.serverless.start({"handler": handler}) 