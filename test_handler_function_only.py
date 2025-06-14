#!/usr/bin/env python3
"""
测试RunPod Handler函数（不启动serverless）
"""

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

def test_handler():
    """测试handler函数"""
    try:
        # 测试数据
        test_job = {
            "id": "test-job-123",
            "input": {
                "prompt": "Hello RunPod v1.7.11!"
            }
        }
        
        print("=== 测试RunPod Handler函数 ===")
        print(f"测试输入: {test_job}")
        
        # 调用handler
        result = handler(test_job)
        
        print(f"测试结果: {result}")
        print("✅ Handler函数测试成功!")
        
        return True
        
    except Exception as e:
        print(f"❌ Handler函数测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = test_handler()
    sys.exit(0 if success else 1) 