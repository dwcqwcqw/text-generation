#!/usr/bin/env python3
"""
快速修复GPUtil导入错误
"""

import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """快速修复GPUtil问题"""
    logger.info("🔧 快速修复GPUtil导入错误...")
    
    try:
        # 安装GPUtil
        logger.info("📦 安装GPUtil...")
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', 'GPUtil'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ GPUtil安装成功")
        else:
            logger.error(f"❌ GPUtil安装失败: {result.stderr}")
            return False
        
        # 测试导入
        logger.info("🧪 测试GPUtil导入...")
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            logger.info(f"✅ GPUtil导入成功，检测到 {len(gpus)} 个GPU")
            
            if gpus:
                gpu = gpus[0]
                logger.info(f"🔥 GPU信息: {gpu.name}, 显存: {gpu.memoryTotal}MB")
            
            return True
        except Exception as e:
            logger.error(f"❌ GPUtil导入测试失败: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 修复过程异常: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("🎉 GPUtil修复完成！现在可以重启handler了")
    else:
        logger.error("❌ GPUtil修复失败")
    sys.exit(0 if success else 1) 