#!/usr/bin/env python3
"""
简化的RunPod Handler - 修复模块导入问题
专门处理 "No module named runpod.serverless.start" 错误
"""

import os
import sys
import json
import logging

# 首先尝试导入RunPod
try:
    import runpod
    print("✅ RunPod模块导入成功")
except ImportError as e:
    print(f"❌ RunPod导入失败: {e}")
    sys.exit(1)

# 检查RunPod版本和可用属性
print(f"RunPod版本: {getattr(runpod, '__version__', 'unknown')}")
print(f"RunPod属性: {dir(runpod)}")

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(event):
    """简化的处理函数"""
    try:
        logger.info(f"收到事件: {event}")
        
        # 获取输入
        input_data = event.get("input", {})
        prompt = input_data.get("prompt", "Hello")
        
        # 简单响应
        response = {
            "output": f"Echo: {prompt}",
            "status": "success",
            "debug_info": {
                "runpod_version": getattr(runpod, '__version__', 'unknown'),
                "python_version": sys.version,
                "available_modules": dir(runpod)
            }
        }
        
        logger.info(f"返回响应: {response}")
        return response
        
    except Exception as e:
        logger.error(f"处理错误: {e}")
        return {
            "error": str(e),
            "status": "error"
        }

def main():
    """主启动函数"""
    logger.info("🚀 启动RunPod handler...")
    
    # 检查RunPod可用的启动方法
    available_methods = []
    
    if hasattr(runpod, 'serverless'):
        if hasattr(runpod.serverless, 'start'):
            available_methods.append("runpod.serverless.start")
        available_methods.append("runpod.serverless")
    
    if hasattr(runpod, 'start'):
        available_methods.append("runpod.start")
    
    logger.info(f"可用的启动方法: {available_methods}")
    
    # 尝试不同的启动方法
    startup_success = False
    
    # 方法1: 标准方式
    if not startup_success:
        try:
            logger.info("尝试方法1: runpod.serverless.start()")
            runpod.serverless.start({"handler": handler})
            startup_success = True
            logger.info("✅ 方法1成功")
        except Exception as e:
            logger.warning(f"方法1失败: {e}")
    
    # 方法2: 直接导入serverless
    if not startup_success:
        try:
            logger.info("尝试方法2: 直接导入serverless")
            from runpod import serverless
            serverless.start({"handler": handler})
            startup_success = True
            logger.info("✅ 方法2成功")
        except Exception as e:
            logger.warning(f"方法2失败: {e}")
    
    # 方法3: 简单启动
    if not startup_success:
        try:
            logger.info("尝试方法3: runpod.start()")
            runpod.start({"handler": handler})
            startup_success = True
            logger.info("✅ 方法3成功")
        except Exception as e:
            logger.warning(f"方法3失败: {e}")
    
    # 方法4: 最简单的方式
    if not startup_success:
        try:
            logger.info("尝试方法4: 最简单方式")
            runpod.start(handler)
            startup_success = True
            logger.info("✅ 方法4成功")
        except Exception as e:
            logger.warning(f"方法4失败: {e}")
    
    if not startup_success:
        logger.error("❌ 所有启动方法都失败了")
        print("可用的RunPod属性:")
        for attr in dir(runpod):
            if not attr.startswith('_'):
                print(f"  - {attr}: {type(getattr(runpod, attr))}")

if __name__ == "__main__":
    # 测试模式
    test_event = {"input": {"prompt": "测试消息"}}
    result = handler(test_event)
    print("测试结果:", json.dumps(result, indent=2, ensure_ascii=False))
else:
    # 启动服务
    main() 