#!/usr/bin/env python3
"""
RTX 4090专用CUDA修复脚本
解决Ada Lovelace架构(计算能力8.9)的编译问题
"""

import os
import sys
import subprocess
import platform

def run_command(cmd, description=""):
    """执行命令并检查结果"""
    print(f"\n{'='*60}")
    print(f"执行: {description}")
    print(f"命令: {cmd}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode != 0:
            print(f"❌ 命令执行失败，返回码: {result.returncode}")
            return False
        else:
            print("✅ 命令执行成功")
            return True
    except subprocess.TimeoutExpired:
        print("❌ 命令执行超时")
        return False
    except Exception as e:
        print(f"❌ 命令执行出错: {e}")
        return False

def check_gpu():
    """检查GPU类型和CUDA环境"""
    print("\n🔍 检查GPU和CUDA环境...")
    
    # 检查nvidia-smi
    if not run_command("nvidia-smi", "检查NVIDIA驱动"):
        print("❌ NVIDIA驱动未正确安装")
        return False
    
    # 检查GPU型号
    gpu_check = subprocess.run("nvidia-smi --query-gpu=name --format=csv,noheader,nounits", 
                              shell=True, capture_output=True, text=True)
    if gpu_check.returncode == 0:
        gpu_name = gpu_check.stdout.strip()
        print(f"🎯 检测到GPU: {gpu_name}")
        
        if "4090" in gpu_name:
            print("✅ 确认为RTX 4090，计算能力8.9")
            return True
        else:
            print("⚠️  非RTX 4090，但仍可使用此脚本")
            return True
    
    return False

def setup_rtx4090_environment():
    """设置RTX 4090专用环境变量"""
    print("\n🔧 设置RTX 4090专用环境变量...")
    
    # RTX 4090 Ada Lovelace架构的计算能力是8.9
    env_vars = {
        'GGML_CUDA': '1',
        'CUDA_VISIBLE_DEVICES': '0',
        'CUDA_LAUNCH_BLOCKING': '1',
        'CMAKE_ARGS': '-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=89 -DCMAKE_CUDA_COMPILER_FORCED=ON',
        'FORCE_CMAKE': '1',
        'CMAKE_CUDA_ARCHITECTURES': '89',  # RTX 4090专用
        'NVCC_APPEND_FLAGS': '--allow-unsupported-compiler',
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"✅ 设置 {key}={value}")
    
    return True

def uninstall_llama_cpp():
    """卸载现有的llama-cpp-python"""
    print("\n🗑️  卸载现有的llama-cpp-python...")
    
    commands = [
        "pip uninstall llama-cpp-python -y",
        "pip cache purge"
    ]
    
    for cmd in commands:
        run_command(cmd, f"执行: {cmd}")

def install_rtx4090_optimized():
    """安装RTX 4090优化版本的llama-cpp-python"""
    print("\n📦 安装RTX 4090优化版本的llama-cpp-python...")
    
    # 使用显式的计算能力参数
    install_cmd = '''CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=89 -DCMAKE_CUDA_COMPILER_FORCED=ON" FORCE_CMAKE=1 pip install llama-cpp-python --no-cache-dir --verbose'''
    
    if not run_command(install_cmd, "安装RTX 4090优化版本"):
        print("❌ 第一次安装失败，尝试备用方案...")
        
        # 备用方案：使用更保守的设置
        backup_cmd = '''CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=89;86;80;75" FORCE_CMAKE=1 pip install llama-cpp-python --no-cache-dir'''
        
        if not run_command(backup_cmd, "备用安装方案"):
            print("❌ 所有安装方案都失败了")
            return False
    
    return True

def verify_rtx4090_installation():
    """验证RTX 4090的安装"""
    print("\n🧪 验证RTX 4090安装...")
    
    test_script = '''
import sys
print("Python路径:", sys.executable)

try:
    import llama_cpp
    print("✅ llama_cpp导入成功")
    print(f"版本: {llama_cpp.__version__}")
    
    # 检查CUDA支持
    model_path = "/runpod-volume/text_models/L3.2-8X3B.gguf"
    
    try:
        llama = llama_cpp.Llama(
            model_path=model_path,
            n_gpu_layers=1,  # 只测试1层
            verbose=True,
            n_ctx=512  # 小上下文测试
        )
        print("✅ RTX 4090 GPU加载测试成功！")
        print(f"GPU层数: {llama.n_gpu_layers}")
        
        # 释放资源
        del llama
        
    except Exception as e:
        print(f"❌ GPU测试失败: {e}")
        
        # 尝试CPU模式验证安装
        try:
            llama_cpu = llama_cpp.Llama(
                model_path=model_path,
                n_gpu_layers=0,
                verbose=True,
                n_ctx=512
            )
            print("✅ CPU模式工作正常，但GPU加载失败")
            del llama_cpu
        except Exception as e2:
            print(f"❌ 连CPU模式都失败: {e2}")

except ImportError as e:
    print(f"❌ llama_cpp导入失败: {e}")
except Exception as e:
    print(f"❌ 其他错误: {e}")
'''
    
    return run_command(f'python3 -c "{test_script}"', "验证RTX 4090安装")

def main():
    """主函数"""
    print("🚀 RTX 4090专用CUDA修复脚本启动")
    print("目标：解决Ada Lovelace架构(计算能力8.9)的编译问题")
    
    # 检查GPU
    if not check_gpu():
        print("❌ GPU检查失败")
        return False
    
    # 设置环境
    if not setup_rtx4090_environment():
        print("❌ 环境设置失败")
        return False
    
    # 卸载旧版本
    uninstall_llama_cpp()
    
    # 安装RTX 4090优化版本
    if not install_rtx4090_optimized():
        print("❌ RTX 4090优化安装失败")
        return False
    
    # 验证安装
    if not verify_rtx4090_installation():
        print("❌ RTX 4090安装验证失败")
        return False
    
    print("\n🎉 RTX 4090 CUDA修复完成！")
    print("现在应该能正确使用GPU加速了")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 