#!/usr/bin/env python3
"""
RunPod 快速诊断和修复脚本
用于检查和修复常见的RunPod部署问题
"""

import requests
import json
import time

# RunPod 配置
RUNPOD_API_KEY = "rpa_YT0BFBFZYAZMQHR231H4DOKQEOAJXSMVIBDYN4ZQ1tdxlb"
ENDPOINT_ID = "4cx6jtjdx6hdhr"
ENDPOINT_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"

def test_endpoint():
    """测试RunPod endpoint"""
    print("🔍 Testing RunPod Endpoint...")
    
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 简单的测试payload
    payload = {
        "input": {
            "prompt": "Hello",
            "model": "L3.2-8X3B",
            "max_tokens": 10,
            "temperature": 0.7
        }
    }
    
    try:
        print(f"📡 Sending request to: {ENDPOINT_URL}")
        print(f"📦 Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            ENDPOINT_URL, 
            headers=headers, 
            json=payload,
            timeout=30
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out - worker可能正在启动或处理失败")
        return False
    except Exception as e:
        print(f"💥 Exception: {str(e)}")
        return False

def check_health():
    """检查endpoint健康状态"""
    print("\n🏥 Checking Endpoint Health...")
    
    health_url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/health"
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    
    try:
        response = requests.get(health_url, headers=headers, timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health Check: {json.dumps(health_data, indent=2)}")
            return health_data
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"💥 Health check error: {str(e)}")
        return None

def diagnose_issue(health_data):
    """诊断常见问题"""
    print("\n🔧 Diagnosing Issues...")
    
    if not health_data:
        print("❌ 无法获取health数据")
        return
    
    jobs = health_data.get("jobs", {})
    
    print(f"📊 Worker状态:")
    print(f"  - Initializing: {jobs.get('initializing', 0)}")
    print(f"  - Ready: {jobs.get('ready', 0)}")  
    print(f"  - Running: {jobs.get('running', 0)}")
    print(f"  - Throttled: {jobs.get('throttled', 0)}")
    print(f"  - Unhealthy: {jobs.get('unhealthy', 0)}")
    
    if jobs.get('ready', 0) > 0:
        print("✅ 有ready的workers，但API调用失败")
        print("🔍 可能的问题:")
        print("  1. Handler代码错误（最可能）")
        print("  2. 模型文件路径错误")
        print("  3. 依赖项版本不兼容")
        print("  4. GPU内存不足")
    elif jobs.get('initializing', 0) > 0:
        print("⏳ Workers正在初始化中...")
    elif jobs.get('unhealthy', 0) > 0:
        print("❌ 有不健康的workers，需要检查logs")
    else:
        print("❌ 没有可用的workers")

def main():
    """主函数"""
    print("🚀 RunPod 诊断工具")
    print("=" * 50)
    
    # 检查健康状态
    health_data = check_health()
    
    # 诊断问题
    diagnose_issue(health_data)
    
    # 测试endpoint
    print("\n" + "=" * 50)
    success = test_endpoint()
    
    print("\n" + "=" * 50)
    print("📋 总结:")
    if success:
        print("✅ RunPod endpoint工作正常！")
    else:
        print("❌ RunPod endpoint有问题")
        print("\n🔧 建议的修复步骤:")
        print("1. 登录RunPod控制台")
        print("2. 找到endpoint 4cx6jtjdx6hdhr")
        print("3. 上传新的handler_llama.py文件")
        print("4. 确保requirements.txt包含正确的依赖项")
        print("5. 重新部署function")
        print("6. 验证模型文件路径存在")

if __name__ == "__main__":
    main() 