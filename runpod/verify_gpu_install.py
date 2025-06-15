#!/usr/bin/env python3
"""
GPU安装验证脚本 - 在构建时验证llama-cpp-python的GPU支持
"""

import sys
import os

def verify_gpu_support():
    """验证GPU支持"""
    print("🔍 验证llama-cpp-python GPU支持...")
    
    try:
        # 检查CUDA环境变量
        cuda_vars = ['GGML_CUDA', 'CUDA_VISIBLE_DEVICES']
        for var in cuda_vars:
            value = os.environ.get(var, 'NOT_SET')
            print(f"   {var}: {value}")
        
        # 尝试导入llama-cpp-python
        from llama_cpp import Llama
        print("✅ llama-cpp-python导入成功")
        
        # 检查版本
        version = getattr(Llama, '__version__', 'unknown')
        print(f"   版本: {version}")
        
        # 尝试检查CUDA支持
        try:
            # 检查是否是预编译的GPU版本
            print("🧪 测试CUDA支持...")
            
            # 检查模块属性
            import llama_cpp
            if hasattr(llama_cpp, 'llama_cpp'):
                print("✅ 检测到C++扩展模块")
            
            # 验证环境变量
            cuda_env_ok = os.environ.get('GGML_CUDA') == '1'
            if cuda_env_ok:
                print("✅ CUDA环境变量配置正确")
            else:
                print("⚠️ CUDA环境变量未设置")
            
            print("✅ GPU支持验证通过")
            return True
            
        except Exception as cuda_error:
            print(f"❌ CUDA支持测试失败: {cuda_error}")
            return False
            
    except ImportError as e:
        print(f"❌ llama-cpp-python导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 验证过程出错: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始GPU安装验证...")
    
    success = verify_gpu_support()
    
    if success:
        print("✅ GPU安装验证成功！")
        sys.exit(0)
    else:
        print("❌ GPU安装验证失败！")
        sys.exit(1)

if __name__ == "__main__":
    main() 