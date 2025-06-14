#!/usr/bin/env python3
"""
RunPod Handler Debug Version
输出详细的环境和版本信息
"""

import sys
import os

print("=== Python环境信息 ===")
print(f"Python版本: {sys.version}")
print(f"Python路径: {sys.executable}")
print(f"当前工作目录: {os.getcwd()}")

print("\n=== 尝试导入RunPod ===")
try:
    import runpod
    print(f"✅ RunPod导入成功")
    print(f"RunPod版本: {getattr(runpod, '__version__', 'unknown')}")
    print(f"RunPod路径: {runpod.__file__}")
    print(f"RunPod属性: {[attr for attr in dir(runpod) if not attr.startswith('_')]}")
    
    # 检查serverless模块
    if hasattr(runpod, 'serverless'):
        print(f"✅ runpod.serverless存在")
        print(f"serverless属性: {[attr for attr in dir(runpod.serverless) if not attr.startswith('_')]}")
        
        if hasattr(runpod.serverless, 'start'):
            print(f"✅ runpod.serverless.start存在")
        else:
            print(f"❌ runpod.serverless.start不存在")
    else:
        print(f"❌ runpod.serverless不存在")
        
except ImportError as e:
    print(f"❌ RunPod导入失败: {e}")
    sys.exit(1)

print("\n=== 定义Handler ===")
def handler(job):
    """简单的handler函数"""
    try:
        print(f"Handler收到job: {job}")
        job_input = job.get("input", {})
        prompt = job_input.get("prompt", "Hello")
        result = f"Debug Echo: {prompt}"
        print(f"Handler返回: {result}")
        return result
    except Exception as e:
        error_msg = f"Handler错误: {e}"
        print(error_msg)
        return {"error": error_msg}

print("✅ Handler定义完成")

print("\n=== 尝试启动RunPod Serverless ===")
try:
    print("调用 runpod.serverless.start...")
    runpod.serverless.start({"handler": handler})
    print("✅ RunPod serverless启动成功")
except Exception as e:
    print(f"❌ RunPod serverless启动失败: {e}")
    print(f"错误类型: {type(e)}")
    import traceback
    traceback.print_exc() 