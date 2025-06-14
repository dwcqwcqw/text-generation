#!/usr/bin/env python3
"""
RunPod依赖安装脚本
快速安装缺失的Python包
"""

import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def install_package(package_name):
    """安装Python包"""
    try:
        logger.info(f"📦 安装 {package_name}...")
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', package_name
        ], capture_output=True, text=True, check=True)
        
        logger.info(f"✅ {package_name} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {package_name} 安装失败: {e.stderr}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始安装RunPod依赖...")
    
    # 需要安装的包列表
    packages = [
        'GPUtil',
        'runpod',
        'llama-cpp-python'
    ]
    
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
    
    logger.info(f"📊 安装完成: {success_count}/{len(packages)} 个包安装成功")
    
    if success_count == len(packages):
        logger.info("🎉 所有依赖安装成功！")
        return True
    else:
        logger.error("❌ 部分依赖安装失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 