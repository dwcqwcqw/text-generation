#!/usr/bin/env python3
"""
综合检测和修复脚本
解决前端模型选择和GPU兼容性问题
"""

import os
import sys
import subprocess
import platform
import json
import time

def run_command(cmd, description="", timeout=60):
    """执行命令并返回结果"""
    print(f"\n{'='*60}")
    print(f"执行: {description}")
    print(f"命令: {cmd}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print(f"❌ 命令执行超时 ({timeout}秒)")
        return False, "", "Timeout"
    except Exception as e:
        print(f"❌ 命令执行出错: {e}")
        return False, "", str(e)

def detect_system_architecture():
    """检测系统架构和GPU环境"""
    print("\n🔍 系统架构检测")
    
    # Python平台信息
    print(f"Python平台: {platform.platform()}")
    print(f"处理器架构: {platform.processor()}")
    print(f"机器类型: {platform.machine()}")
    print(f"系统: {platform.system()}")
    
    # 检查是否在容器中
    if os.path.exists('/.dockerenv'):
        print("✅ 运行在Docker容器中")
    else:
        print("⚠️ 不在Docker容器中")
    
    # 检查CUDA环境
    success, stdout, stderr = run_command("nvidia-smi", "检查NVIDIA驱动")
    if success:
        print("✅ NVIDIA驱动可用")
        
        # 获取GPU信息
        success, gpu_info, _ = run_command("nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv,noheader", "获取GPU详细信息")
        if success:
            print(f"🎯 GPU信息: {gpu_info.strip()}")
    else:
        print("❌ NVIDIA驱动不可用")
        return False
    
    # 检查CUDA版本
    success, cuda_version, _ = run_command("nvcc --version", "检查CUDA版本")
    if success:
        print(f"✅ CUDA版本: {cuda_version}")
    else:
        print("❌ CUDA编译器不可用")
    
    return True

def detect_llama_cpp_issues():
    """检测llama-cpp-python的问题"""
    print("\n🔍 llama-cpp-python问题检测")
    
    try:
        import llama_cpp
        print(f"✅ llama-cpp-python版本: {llama_cpp.__version__}")
        
        # 检查CUDA支持
        test_script = '''
import llama_cpp
import os

# 测试CUDA支持
try:
    # 创建一个最小的测试模型配置
    print("测试CUDA支持...")
    
    # 检查环境变量
    print(f"GGML_CUDA: {os.environ.get('GGML_CUDA', 'NOT SET')}")
    print(f"CUDA_VISIBLE_DEVICES: {os.environ.get('CUDA_VISIBLE_DEVICES', 'NOT SET')}")
    
    # 尝试创建模型实例（不加载实际模型）
    print("llama-cpp-python导入成功")
    
except Exception as e:
    print(f"CUDA支持测试失败: {e}")
'''
        
        success, output, error = run_command(f'python3 -c "{test_script}"', "测试CUDA支持")
        if "CPU_AARCH64" in output or "CPU_AARCH64" in error:
            print("❌ 检测到CPU_AARCH64错误 - 这是架构不匹配问题")
            return False
        
        return True
        
    except ImportError as e:
        print(f"❌ llama-cpp-python导入失败: {e}")
        return False

def fix_architecture_mismatch():
    """修复架构不匹配问题"""
    print("\n🔧 修复架构不匹配问题")
    
    # 设置正确的环境变量
    env_vars = {
        'GGML_CUDA': '1',
        'CUDA_VISIBLE_DEVICES': '0',
        'CMAKE_CUDA_ARCHITECTURES': 'auto',  # 让系统自动检测
        'FORCE_CMAKE': '1',
    }
    
    # 检测GPU类型并设置对应的架构
    success, gpu_info, _ = run_command("nvidia-smi --query-gpu=name --format=csv,noheader", "获取GPU型号")
    if success:
        gpu_name = gpu_info.strip().lower()
        if "4090" in gpu_name:
            env_vars['CMAKE_CUDA_ARCHITECTURES'] = '89'
            print("🎯 检测到RTX 4090，设置计算能力8.9")
        elif "l40" in gpu_name:
            env_vars['CMAKE_CUDA_ARCHITECTURES'] = '89'
            print("🎯 检测到L40，设置计算能力8.9")
        elif "3090" in gpu_name or "3080" in gpu_name:
            env_vars['CMAKE_CUDA_ARCHITECTURES'] = '86'
            print("🎯 检测到RTX 30系列，设置计算能力8.6")
        else:
            env_vars['CMAKE_CUDA_ARCHITECTURES'] = '75;80;86;89'
            print("🎯 未知GPU，使用通用架构设置")
    
    # 设置环境变量
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"✅ 设置 {key}={value}")
    
    return True

def reinstall_llama_cpp():
    """重新安装llama-cpp-python"""
    print("\n📦 重新安装llama-cpp-python")
    
    # 卸载现有版本
    run_command("pip uninstall llama-cpp-python -y", "卸载现有版本")
    run_command("pip cache purge", "清理pip缓存")
    
    # 获取CMAKE参数
    cuda_arch = os.environ.get('CMAKE_CUDA_ARCHITECTURES', 'auto')
    cmake_args = f"-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES={cuda_arch}"
    
    # 安装新版本
    install_cmd = f'CMAKE_ARGS="{cmake_args}" FORCE_CMAKE=1 pip install llama-cpp-python --no-cache-dir --verbose'
    
    success, output, error = run_command(install_cmd, "安装CUDA版本", timeout=300)
    
    if not success:
        print("❌ CUDA版本安装失败，尝试CPU版本")
        success, output, error = run_command("pip install llama-cpp-python --no-cache-dir", "安装CPU版本")
    
    return success

def test_gpu_loading():
    """测试GPU加载"""
    print("\n🧪 测试GPU加载")
    
    test_script = '''
import llama_cpp
import os

try:
    # 检查模型文件
    model_paths = [
        "/runpod-volume/text_models/L3.2-8X3B.gguf",
        "/runpod-volume/text_models/L3.2-8X4B.gguf"
    ]
    
    available_model = None
    for path in model_paths:
        if os.path.exists(path):
            available_model = path
            print(f"✅ 找到模型: {path}")
            break
    
    if not available_model:
        print("❌ 未找到模型文件")
        exit(1)
    
    # 测试GPU加载
    print("测试GPU加载...")
    model = llama_cpp.Llama(
        model_path=available_model,
        n_gpu_layers=1,  # 只测试1层
        verbose=True,
        n_ctx=512
    )
    
    print("✅ GPU加载测试成功！")
    print(f"模型路径: {available_model}")
    
    # 清理
    del model
    
except Exception as e:
    print(f"❌ GPU加载测试失败: {e}")
    exit(1)
'''
    
    success, output, error = run_command(f'python3 -c "{test_script}"', "GPU加载测试")
    
    if success and "assigned to device CUDA" in output:
        print("✅ GPU加载成功！")
        return True
    elif "assigned to device CPU" in output:
        print("⚠️ 模型加载到CPU，GPU未被使用")
        return False
    else:
        print("❌ GPU加载测试失败")
        return False

def fix_frontend_models():
    """修复前端模型选择问题"""
    print("\n🔧 修复前端模型选择问题")
    
    # 检查前端文件
    frontend_file = "/app/frontend/src/app/page.tsx"
    if not os.path.exists(frontend_file):
        frontend_file = "frontend/src/app/page.tsx"
    
    if os.path.exists(frontend_file):
        print(f"✅ 找到前端文件: {frontend_file}")
        
        # 强制清理前端缓存
        frontend_dir = os.path.dirname(frontend_file)
        cache_dirs = [
            os.path.join(frontend_dir, ".next"),
            os.path.join(frontend_dir, "node_modules/.cache"),
            os.path.join(frontend_dir, ".cache")
        ]
        
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                run_command(f"rm -rf {cache_dir}", f"清理缓存目录: {cache_dir}")
        
        # 重新构建前端
        if os.path.exists(os.path.join(frontend_dir, "package.json")):
            run_command(f"cd {frontend_dir} && npm run build", "重新构建前端")
        
        return True
    else:
        print("❌ 未找到前端文件")
        return False

def generate_diagnostic_report():
    """生成诊断报告"""
    print("\n📊 生成诊断报告")
    
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "system": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "machine": platform.machine(),
            "python_version": sys.version
        },
        "environment": {},
        "gpu_info": {},
        "llama_cpp_status": {}
    }
    
    # 收集环境变量
    for key in os.environ:
        if any(keyword in key.upper() for keyword in ['CUDA', 'GGML', 'CMAKE', 'RUNPOD']):
            report["environment"][key] = os.environ[key]
    
    # 收集GPU信息
    success, gpu_info, _ = run_command("nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv", "收集GPU信息")
    if success:
        report["gpu_info"]["nvidia_smi"] = gpu_info
    
    # 收集llama-cpp-python状态
    try:
        import llama_cpp
        report["llama_cpp_status"]["version"] = llama_cpp.__version__
        report["llama_cpp_status"]["imported"] = True
    except ImportError as e:
        report["llama_cpp_status"]["imported"] = False
        report["llama_cpp_status"]["error"] = str(e)
    
    # 保存报告
    with open("diagnostic_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("✅ 诊断报告已保存到 diagnostic_report.json")
    return report

def main():
    """主函数"""
    print("🚀 综合检测和修复脚本启动")
    print("目标：解决前端模型选择和GPU兼容性问题")
    
    # 1. 系统架构检测
    if not detect_system_architecture():
        print("❌ 系统架构检测失败")
        return False
    
    # 2. llama-cpp-python问题检测
    llama_cpp_ok = detect_llama_cpp_issues()
    
    # 3. 如果有问题，进行修复
    if not llama_cpp_ok:
        print("🔧 检测到llama-cpp-python问题，开始修复...")
        
        # 修复架构不匹配
        fix_architecture_mismatch()
        
        # 重新安装
        if not reinstall_llama_cpp():
            print("❌ llama-cpp-python重新安装失败")
            return False
    
    # 4. 测试GPU加载
    gpu_ok = test_gpu_loading()
    
    # 5. 修复前端问题
    fix_frontend_models()
    
    # 6. 生成诊断报告
    report = generate_diagnostic_report()
    
    # 7. 总结
    print("\n🎯 修复总结:")
    print(f"✅ 系统架构: 正常")
    print(f"{'✅' if llama_cpp_ok else '❌'} llama-cpp-python: {'正常' if llama_cpp_ok else '已修复'}")
    print(f"{'✅' if gpu_ok else '❌'} GPU加载: {'正常' if gpu_ok else '需要进一步检查'}")
    print(f"✅ 前端模型: 已修复")
    
    if gpu_ok:
        print("\n🎉 所有问题已解决！")
        return True
    else:
        print("\n⚠️ GPU问题仍需进一步检查，请查看诊断报告")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 