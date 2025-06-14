#!/usr/bin/env python3
"""
测试RunPod Handler v1.7.11
"""

import sys
import os

# 添加runpod目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'runpod'))

def test_handler():
    """测试handler函数"""
    try:
        # 导入handler
        from handler_v1711 import handler
        
        # 测试数据
        test_job = {
            "id": "test-job-123",
            "input": {
                "prompt": "Hello RunPod v1.7.11!"
            }
        }
        
        print("=== 测试RunPod Handler v1.7.11 ===")
        print(f"测试输入: {test_job}")
        
        # 调用handler
        result = handler(test_job)
        
        print(f"测试结果: {result}")
        print("✅ Handler测试成功!")
        
        return True
        
    except Exception as e:
        print(f"❌ Handler测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_handler()
    sys.exit(0 if success else 1) 