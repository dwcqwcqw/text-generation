#!/usr/bin/env python3
"""
RunPod 环境设置和修复脚本
解决 "No module named runpod.serverless.start" 错误
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} 成功")
            if result.stdout.strip():
                print(f"输出: {result.stdout.strip()}")
        else:
            print(f"❌ {description} 失败")
            print(f"错误: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ {description} 异常: {e}")
        return False

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    print(f"🐍 Python版本: {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("⚠️ 警告: Python版本可能过低，建议使用Python 3.8+")

def check_runpod_installation():
    """检查RunPod安装状态"""
    print("\n📦 检查RunPod包安装状态...")
    
    try:
        import runpod
        print(f"✅ runpod 已安装，版本: {runpod.__version__}")
        
        # 检查serverless模块
        try:
            from runpod.serverless import start
            print("✅ runpod.serverless.start 可用")
            return True
        except ImportError as e:
            print(f"❌ runpod.serverless.start 不可用: {e}")
            return False
            
    except ImportError:
        print("❌ runpod 包未安装")
        return False

def fix_runpod_installation():
    """修复RunPod安装"""
    print("\n🔨 开始修复RunPod安装...")
    
    # 卸载旧版本
    run_command("pip uninstall runpod -y", "卸载旧版本runpod")
    
    # 清除pip缓存
    run_command("pip cache purge", "清除pip缓存")
    
    # 升级pip
    run_command("pip install --upgrade pip", "升级pip")
    
    # 安装最新版本的runpod
    success = run_command("pip install runpod>=1.5.1", "安装最新版runpod")
    
    if not success:
        # 尝试从git安装
        print("📥 尝试从git安装最新版本...")
        run_command("pip install git+https://github.com/runpod/runpod-python.git", "从git安装runpod")
    
    return check_runpod_installation()

def create_handler_template():
    """创建RunPod handler模板"""
    handler_code = '''
import runpod
import json
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(event):
    """
    RunPod handler函数
    处理来自前端的请求
    """
    try:
        # 获取输入参数
        input_data = event.get("input", {})
        prompt = input_data.get("prompt", "Hello, how are you?")
        max_tokens = input_data.get("max_tokens", 100)
        model_path = input_data.get("model_path", "/runpod-volume/text_models/L3.2-8X3B.gguf")
        
        logger.info(f"收到请求 - prompt: {prompt[:50]}..., model: {model_path}")
        
        # 检查模型文件是否存在
        import os
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        # 这里应该是你的模型推理代码
        # 目前返回一个示例响应
        response_text = f"这是对 '{prompt}' 的回复 (使用模型: {model_path})"
        
        return {
            "text": response_text,
            "model_used": model_path,
            "tokens_generated": len(response_text.split())
        }
        
    except Exception as e:
        logger.error(f"处理请求时出错: {e}")
        return {"error": str(e)}

# 启动RunPod serverless
if __name__ == "__main__":
    logger.info("🚀 启动RunPod serverless handler...")
    runpod.serverless.start({"handler": handler})
'''
    
    # 写入handler文件
    with open("runpod_handler.py", "w", encoding="utf-8") as f:
        f.write(handler_code.strip())
    
    print("✅ 创建了RunPod handler模板: runpod_handler.py")

def main():
    print("🚀 RunPod 环境诊断和修复工具")
    print("=" * 50)
    
    # 检查Python版本
    check_python_version()
    
    # 检查当前安装状态
    if check_runpod_installation():
        print("\n✅ RunPod环境正常，无需修复")
    else:
        print("\n🔧 检测到问题，开始修复...")
        if fix_runpod_installation():
            print("\n✅ RunPod环境修复成功！")
        else:
            print("\n❌ RunPod环境修复失败")
            print("💡 建议手动操作:")
            print("   1. pip uninstall runpod")
            print("   2. pip install runpod>=1.5.1")
            print("   3. 或者使用: pip install git+https://github.com/runpod/runpod-python.git")
    
    # 创建handler模板
    create_handler_template()
    
    print("\n🎯 接下来的步骤:")
    print("1. 确保你的RunPod环境中有正确的handler代码")
    print("2. 检查模型文件路径是否正确")
    print("3. 在RunPod控制台查看实时日志")

if __name__ == "__main__":
    main() 