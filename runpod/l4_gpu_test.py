#!/usr/bin/env python3
"""
L4 GPU 测试脚本
专门测试NVIDIA L4 GPU上的模型加载问题
"""

import os
import sys
import time
import logging
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_gpu_detection():
    """测试GPU检测"""
    logger.info("=== 测试1: GPU检测 ===")
    
    try:
        # 测试nvidia-smi
        import subprocess
        logger.info("运行 nvidia-smi...")
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ nvidia-smi 成功")
            logger.info(f"GPU信息:\n{result.stdout[:500]}...")
        else:
            logger.error(f"❌ nvidia-smi 失败: {result.stderr}")
    except Exception as e:
        logger.error(f"❌ nvidia-smi 异常: {e}")
    
    # 测试PyTorch
    try:
        logger.info("检查PyTorch CUDA支持...")
        import torch
        logger.info(f"PyTorch版本: {torch.__version__}")
        logger.info(f"CUDA可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            logger.info(f"GPU数量: {device_count}")
            for i in range(device_count):
                logger.info(f"GPU {i}: {torch.cuda.get_device_name(i)}")
                logger.info(f"GPU {i} 内存: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.1f} GB")
            
            # 测试GPU分配
            logger.info("测试GPU内存分配...")
            try:
                x = torch.rand(1000, 1000).cuda()
                logger.info(f"✅ 成功分配GPU张量，形状: {x.shape}")
                del x
                torch.cuda.empty_cache()
            except Exception as e:
                logger.error(f"❌ GPU分配失败: {e}")
        else:
            logger.warning("⚠️ PyTorch CUDA不可用")
    except Exception as e:
        logger.error(f"❌ PyTorch测试失败: {e}")

def test_llama_cpp_import():
    """测试llama-cpp-python导入"""
    logger.info("\n=== 测试2: llama-cpp-python导入 ===")
    
    try:
        from llama_cpp import Llama
        import llama_cpp
        logger.info(f"✅ 成功导入llama-cpp-python，版本: {llama_cpp.__version__}")
        
        # 检查CUDA支持
        has_cuda = getattr(llama_cpp, "_LLAMA_CUDA", False)
        logger.info(f"llama-cpp CUDA支持: {has_cuda}")
        
        # 检查环境变量
        env_vars = {
            'CUDA_VISIBLE_DEVICES': os.environ.get('CUDA_VISIBLE_DEVICES', 'Not set'),
            'LLAMA_CUBLAS': os.environ.get('LLAMA_CUBLAS', 'Not set'),
            'CMAKE_ARGS': os.environ.get('CMAKE_ARGS', 'Not set'),
        }
        logger.info(f"环境变量: {env_vars}")
        
        return True
    except Exception as e:
        logger.error(f"❌ llama-cpp-python导入失败: {e}")
        return False

def test_model_files():
    """测试模型文件"""
    logger.info("\n=== 测试3: 模型文件检查 ===")
    
    model_paths = [
        "/runpod-volume/text_models/L3.2-8X4B.gguf",  # 较小的模型
        "/runpod-volume/text_models/L3.2-8X3B.gguf"   # 较大的模型
    ]
    
    available_models = []
    for path in model_paths:
        if os.path.exists(path):
            try:
                size = os.path.getsize(path) / (1024**3)  # 大小(GB)
                available_models.append((path, size))
                logger.info(f"✅ 发现模型: {path} ({size:.1f}GB)")
                
                # 检查文件权限
                import stat
                st = os.stat(path)
                perms = stat.filemode(st.st_mode)
                logger.info(f"文件权限: {perms}, 所有者: {st.st_uid}, 组: {st.st_gid}")
                
                # 尝试读取文件前几个字节
                try:
                    with open(path, 'rb') as f:
                        header = f.read(16)
                    logger.info(f"文件头16字节: {header.hex()}")
                except Exception as e:
                    logger.error(f"❌ 读取文件头失败: {e}")
            except Exception as e:
                logger.error(f"❌ 检查模型文件失败: {e}")
        else:
            logger.warning(f"⚠️ 模型未找到: {path}")
    
    return available_models

def test_minimal_load():
    """尝试最小化加载模型"""
    logger.info("\n=== 测试4: 最小化模型加载 ===")
    
    # 先检查模型文件
    available_models = test_model_files()
    if not available_models:
        logger.error("❌ 没有可用的模型文件")
        return False
    
    # 按大小排序，先尝试较小的模型
    available_models.sort(key=lambda x: x[1])
    model_path, size = available_models[0]
    
    logger.info(f"尝试加载模型: {model_path} ({size:.1f}GB)")
    
    try:
        # 设置环境变量
        os.environ['CUDA_VISIBLE_DEVICES'] = '0'
        os.environ['LLAMA_CUBLAS'] = '1'
        
        from llama_cpp import Llama
        
        # 记录开始时间
        start_time = time.time()
        logger.info("开始加载模型...")
        
        # 使用最小化参数
        model = Llama(
            model_path=model_path,
            n_ctx=32,            # 极小的上下文窗口
            n_batch=1,           # 最小批处理大小
            n_gpu_layers=0,      # 先用CPU模式
            verbose=True,        # 详细日志
            n_threads=1,         # 单线程
            use_mmap=False,      # 禁用mmap
            use_mlock=False,     # 禁用mlock
        )
        
        elapsed = time.time() - start_time
        logger.info(f"✅ 模型成功加载! 耗时: {elapsed:.2f}秒")
        
        # 尝试简单推理
        logger.info("测试简单推理...")
        output = model("Hello", max_tokens=1)
        logger.info(f"推理结果: {output}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 模型加载失败: {e}")
        logger.error(f"异常堆栈: {traceback.format_exc()}")
        return False

def test_gpu_load():
    """尝试GPU加载模型"""
    logger.info("\n=== 测试5: GPU模型加载 ===")
    
    # 先检查模型文件
    available_models = test_model_files()
    if not available_models:
        logger.error("❌ 没有可用的模型文件")
        return False
    
    # 按大小排序，先尝试较小的模型
    available_models.sort(key=lambda x: x[1])
    model_path, size = available_models[0]
    
    logger.info(f"尝试GPU加载模型: {model_path} ({size:.1f}GB)")
    
    try:
        # 设置环境变量
        os.environ['CUDA_VISIBLE_DEVICES'] = '0'
        os.environ['LLAMA_CUBLAS'] = '1'
        
        from llama_cpp import Llama
        
        # 记录开始时间
        start_time = time.time()
        logger.info("开始GPU加载模型...")
        
        # 使用1个GPU层测试
        model = Llama(
            model_path=model_path,
            n_ctx=32,            # 极小的上下文窗口
            n_batch=1,           # 最小批处理大小
            n_gpu_layers=1,      # 仅使用1个GPU层
            verbose=True,        # 详细日志
            n_threads=1,         # 单线程
            use_mmap=False,      # 禁用mmap
            use_mlock=False,     # 禁用mlock
        )
        
        elapsed = time.time() - start_time
        logger.info(f"✅ 模型成功在GPU上加载! 耗时: {elapsed:.2f}秒")
        
        # 尝试简单推理
        logger.info("测试简单推理...")
        output = model("Hello", max_tokens=1)
        logger.info(f"推理结果: {output}")
        
        return True
    except Exception as e:
        logger.error(f"❌ GPU模型加载失败: {e}")
        logger.error(f"异常堆栈: {traceback.format_exc()}")
        return False

def main():
    """主函数"""
    logger.info("==== L4 GPU 测试脚本 ====")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"当前工作目录: {os.getcwd()}")
    
    # 测试GPU检测
    test_gpu_detection()
    
    # 测试llama-cpp-python导入
    if not test_llama_cpp_import():
        logger.error("llama-cpp-python导入失败，终止测试")
        return
    
    # 测试最小化加载
    if test_minimal_load():
        # 如果CPU加载成功，尝试GPU加载
        test_gpu_load()
    
    logger.info("\n==== 测试完成 ====")

if __name__ == "__main__":
    main() 