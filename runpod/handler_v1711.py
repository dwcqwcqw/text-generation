#!/usr/bin/env python3
"""
RunPod Handler for version 1.7.11
基于最新的RunPod Python SDK
包含GPU监控功能
"""

import runpod
import os
import sys
import subprocess
import json
import time
import threading

def get_gpu_info():
    """获取GPU使用情况"""
    try:
        # 使用nvidia-smi获取GPU信息
        result = subprocess.run([
            'nvidia-smi', 
            '--query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw',
            '--format=csv,noheader,nounits'
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            gpu_info = []
            
            for line in lines:
                if line.strip():
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 7:
                        gpu_info.append({
                            'index': parts[0],
                            'name': parts[1],
                            'memory_used_mb': parts[2],
                            'memory_total_mb': parts[3],
                            'utilization_percent': parts[4],
                            'temperature_c': parts[5],
                            'power_draw_w': parts[6]
                        })
            
            return gpu_info
        else:
            return [{'error': 'nvidia-smi command failed'}]
            
    except subprocess.TimeoutExpired:
        return [{'error': 'nvidia-smi timeout'}]
    except FileNotFoundError:
        return [{'error': 'nvidia-smi not found'}]
    except Exception as e:
        return [{'error': f'GPU info error: {str(e)}'}]

def log_gpu_status():
    """记录GPU状态到日志"""
    gpu_info = get_gpu_info()
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"\n=== GPU Status at {timestamp} ===")
    for i, gpu in enumerate(gpu_info):
        if 'error' in gpu:
            print(f"GPU {i}: {gpu['error']}")
        else:
            memory_used = float(gpu['memory_used_mb']) if gpu['memory_used_mb'] != 'N/A' else 0
            memory_total = float(gpu['memory_total_mb']) if gpu['memory_total_mb'] != 'N/A' else 1
            memory_percent = (memory_used / memory_total * 100) if memory_total > 0 else 0
            
            print(f"GPU {gpu['index']} ({gpu['name']}):")
            print(f"  Memory: {gpu['memory_used_mb']}MB / {gpu['memory_total_mb']}MB ({memory_percent:.1f}%)")
            print(f"  Utilization: {gpu['utilization_percent']}%")
            print(f"  Temperature: {gpu['temperature_c']}°C")
            print(f"  Power: {gpu['power_draw_w']}W")
    print("=" * 50)

def start_gpu_monitoring():
    """启动GPU监控线程"""
    def monitor_loop():
        while True:
            log_gpu_status()
            time.sleep(30)  # 每30秒记录一次
    
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    print("🖥️ GPU监控已启动，每30秒记录一次状态")

def handler(job):
    """
    RunPod serverless handler function
    
    Args:
        job (dict): Job data containing 'input' and 'id'
        
    Returns:
        Any: The result to be returned to the client
    """
    try:
        # 获取job输入
        job_input = job.get("input", {})
        job_id = job.get("id", "unknown")
        
        # 记录任务开始时的GPU状态
        print(f"\n🚀 Job {job_id} started")
        log_gpu_status()
        
        # 获取prompt
        prompt = job_input.get("prompt", "Hello from RunPod!")
        
        # 模拟一些处理时间以观察GPU使用变化
        print(f"Job {job_id}: Processing prompt '{prompt}'")
        time.sleep(1)  # 模拟处理时间
        
        # 简单的echo响应
        response = f"RunPod Echo (v1.7.11): {prompt}"
        
        # 记录任务完成时的GPU状态
        print(f"Job {job_id}: Returning response '{response}'")
        log_gpu_status()
        print(f"✅ Job {job_id} completed\n")
        
        # 直接返回字符串，RunPod会自动包装
        return response
        
    except Exception as e:
        error_msg = f"Handler error: {str(e)}"
        print(f"ERROR: {error_msg}")
        log_gpu_status()  # 错误时也记录GPU状态
        return {"error": error_msg}

# 启动RunPod serverless
if __name__ == "__main__":
    print("=== RunPod Handler v1.7.11 Starting ===")
    print(f"Python version: {sys.version}")
    print(f"RunPod version: {getattr(runpod, '__version__', 'unknown')}")
    
    # 启动GPU监控
    start_gpu_monitoring()
    
    # 记录初始GPU状态
    print("\n🔍 Initial GPU Status:")
    log_gpu_status()
    
    print("🚀 Starting RunPod serverless...")
    # 启动serverless
    runpod.serverless.start({"handler": handler}) 