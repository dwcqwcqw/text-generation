#!/usr/bin/env python3
"""
测试语音API功能
"""
import requests
import base64
import json
import sys
import os

# API配置
BACKEND_URL = "http://localhost:8000"
MINIMAX_API_KEY = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiJCRUkgTEkiLCJVc2VyTmFtZSI6IkJFSSBMSSIsIkFjY291bnQiOiIiLCJTdWJqZWN0SUQiOiIxOTI1MDI1MzAyNDAwOTk1NjQ0IiwiUGhvbmUiOiIiLCJHcm91cElEIjoiMTkyNTAyNTMwMjM5MjYwNzAzNiIsIlBhZ2VOYW1lIjoiIiwiTWFpbCI6ImJhaWxleWxpYmVpQGdtYWlsLmNvbSIsIkNyZWF0ZVRpbWUiOiIyMDI1LTA1LTIxIDEyOjIyOjI4IiwiVG9rZW5UeXBlIjoxLCJpc3MiOiJtaW5pbWF4In0.cMEP1g8YBLysihnD5RfmqtxGAGfR3XYxdXOAHurxoV5u92-ze8j5Iv1hc7O9qgFAoZyi2-eKRl6iRF3JM_IE1RQ6GXmfQnpr4a0VINu7c2GDW-x_4I-7CTHQTAmXfZOp6bVMbFvZqQDS9mzMexYDcFOghwJm1jFKhisU3J4996BqxC6R_u1J15yWkAb0Y5SX18hlYBEuO8MYPjAECSAcSthXIPxo4KQmd1LPuC2URnlhHBa6kvV0pZGp9tggSUlabyQaliCky8fxfOgyJc1YThQybg3iJ2VlYNnIhSj73SZ3pl6nB1unoiCsusAY0_mbzgcAiTd2rpKTh9xmUtcIxw"

def test_tts_api():
    """测试文字转语音API"""
    print("🔊 测试文字转语音API...")
    
    test_text = "你好，这是一个测试语音合成的文本。我们正在测试MiniMax的语音合成功能。"
    
    payload = {
        "text": test_text,
        "voice_id": "female-shaonv",
        "speed": 1.0,
        "volume": 1.0,
        "pitch": 0
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/speech/tts",
            json=payload,
            timeout=30
        )
        
        print(f"📡 响应状态: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ TTS测试成功")
            print(f"📄 响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get("success") and result.get("audio_data"):
                # 保存音频文件测试
                audio_bytes = base64.b64decode(result["audio_data"])
                with open("test_output.mp3", "wb") as f:
                    f.write(audio_bytes)
                print(f"🎵 音频文件已保存到 test_output.mp3 ({len(audio_bytes)} bytes)")
                return True
            else:
                print(f"❌ TTS失败: {result}")
                return False
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"📄 错误响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ TTS测试异常: {e}")
        return False

def test_minimax_direct():
    """直接测试MiniMax API"""
    print("🚀 直接测试MiniMax API...")
    
    url = "https://api.minimax.io/v1/t2a_v2?GroupId=1925025302392607036"
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {MINIMAX_API_KEY}"
    }
    
    payload = {
        "model": "speech-02-turbo",
        "text": "Hello, this is a test message for MiniMax TTS API.",
        "stream": False,
        "voice_setting": {
            "voice_id": "female-shaonv",
            "speed": 1.0,
            "vol": 1.0,
            "pitch": 0
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"📡 MiniMax响应状态: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ MiniMax API测试成功")
            print(f"📄 响应结构: {list(result.keys())}")
            
            if "data" in result and "audio" in result["data"]:
                hex_audio = result["data"]["audio"]
                audio_bytes = bytes.fromhex(hex_audio)
                with open("minimax_direct_test.mp3", "wb") as f:
                    f.write(audio_bytes)
                print(f"🎵 MiniMax音频文件已保存到 minimax_direct_test.mp3 ({len(audio_bytes)} bytes)")
                return True
            else:
                print(f"❌ MiniMax响应格式异常: {result}")
                return False
        else:
            print(f"❌ MiniMax HTTP错误: {response.status_code}")
            print(f"📄 错误响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ MiniMax测试异常: {e}")
        return False

def test_backend_health():
    """测试后端健康状态"""
    print("🏥 测试后端健康状态...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=5)
        print(f"📡 后端响应状态: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 后端服务正常")
            return True
        else:
            print(f"❌ 后端服务异常: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 后端连接失败: {e}")
        print("💡 请确保后端服务正在运行: cd backend && python main.py")
        return False

def main():
    """主测试流程"""
    print("🧪 开始语音API测试")
    print("=" * 50)
    
    # 测试后端健康状态
    if not test_backend_health():
        print("❌ 后端服务不可用，无法继续测试")
        return
    
    print()
    
    # 测试MiniMax直接API
    minimax_success = test_minimax_direct()
    print()
    
    # 测试后端TTS API
    tts_success = test_tts_api()
    print()
    
    # 汇总结果
    print("📊 测试结果汇总")
    print("=" * 50)
    print(f"MiniMax直接API: {'✅ 通过' if minimax_success else '❌ 失败'}")
    print(f"后端TTS API: {'✅ 通过' if tts_success else '❌ 失败'}")
    
    if minimax_success and tts_success:
        print("🎉 所有测试通过！语音功能已就绪")
        print("💡 请注意：")
        print("   1. STT功能需要RunPod服务器运行")
        print("   2. 前端需要麦克风权限才能录音")
        print("   3. 音频文件已保存到当前目录供测试")
    else:
        print("⚠️ 部分测试失败，请检查配置")

if __name__ == "__main__":
    main() 