#!/usr/bin/env python3
"""
本地测试RunPod handler
"""

# 模拟RunPod环境
import sys
import os
sys.path.insert(0, 'runpod')

# 直接定义handler函数进行测试
def handler(job):
    try:
        job_input = job["input"]
        prompt = job_input.get("prompt", "Hello World")
        result = f"Echo from RunPod: {prompt}"
        return result
    except Exception as e:
        return {"error": str(e)}

def test_handler():
    """测试handler函数"""
    print("🧪 测试RunPod Handler...")
    
    # 模拟RunPod job格式
    test_job = {
        "id": "test-job-123",
        "input": {
            "prompt": "Hello from local test!"
        }
    }
    
    print(f"📥 输入: {test_job}")
    
    try:
        result = handler(test_job)
        print(f"📤 输出: {result}")
        print("✅ Handler测试成功!")
        return True
    except Exception as e:
        print(f"❌ Handler测试失败: {e}")
        return False

if __name__ == "__main__":
    test_handler() 