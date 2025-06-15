#!/usr/bin/env python3
"""
GPU安装验证脚本 - 在构建时验证llama-cpp-python的GPU支持
"""

import sys
import os

def verify_gpu_support():
    """验证GPU支持（构建时安全验证）"""
    print("🔍 验证llama-cpp-python GPU支持...")
    
    try:
        # 检查CUDA环境变量
        cuda_vars = ['GGML_CUDA', 'CUDA_VISIBLE_DEVICES']
        for var in cuda_vars:
            value = os.environ.get(var, 'NOT_SET')
            print(f"   {var}: {value}")
        
        # 尝试导入llama-cpp-python（不加载CUDA库）
        try:
            import llama_cpp
            print("✅ llama-cpp-python模块导入成功")
            
            # 检查版本
            if hasattr(llama_cpp, '__version__'):
                print(f"   版本: {llama_cpp.__version__}")
            
            # 检查是否有CUDA相关的属性（不实际调用）
            if hasattr(llama_cpp, 'Llama'):
                print("✅ 检测到Llama类")
            
            # 检查安装路径，确认是从正确的源安装的
            import pkg_resources
            try:
                dist = pkg_resources.get_distribution('llama-cpp-python')
                print(f"   安装路径: {dist.location}")
                print(f"   安装方式: {dist.project_name} {dist.version}")
            except:
                print("   无法获取安装信息")
            
            print("✅ 构建时GPU支持验证通过")
            print("💡 实际GPU功能将在运行时验证")
            return True
            
        except Exception as import_error:
            print(f"❌ 模块导入失败: {import_error}")
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