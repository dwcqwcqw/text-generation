#!/usr/bin/env python3
import requests
import json
import time

api_key = 'rpa_YT0BFBFZYAZMQHR231H4DOKQEOAJXSMVIBDYN4ZQ1tdxlb'
endpoint_id = '4cx6jtjdx6hdhr'
headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

def test_async_call():
    """测试异步调用"""
    print('=== 测试异步API调用 ===')
    
    # 使用run而不是runsync
    api_url = f'https://api.runpod.ai/v2/{endpoint_id}/run'
    payload = {"input": {"prompt": "Hello from async test"}}
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        print(f'异步调用状态: {response.status_code}')
        print(f'异步调用响应: {response.text}')
        
        if response.status_code == 200:
            data = response.json()
            job_id = data.get('id')
            if job_id:
                print(f'任务ID: {job_id}')
                
                # 轮询结果
                for i in range(10):
                    time.sleep(2)
                    status_url = f'https://api.runpod.ai/v2/{endpoint_id}/status/{job_id}'
                    status_response = requests.get(status_url, headers=headers, timeout=10)
                    print(f'轮询 {i+1}: {status_response.status_code} - {status_response.text}')
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        if status_data.get('status') in ['COMPLETED', 'FAILED']:
                            break
                            
    except Exception as e:
        print(f'异步调用失败: {e}')

def test_sync_with_shorter_timeout():
    """测试同步调用，使用更短的超时"""
    print('\n=== 测试同步API调用（短超时）===')
    
    api_url = f'https://api.runpod.ai/v2/{endpoint_id}/runsync'
    payload = {"input": {"prompt": "Hello sync"}}
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        print(f'同步调用状态: {response.status_code}')
        print(f'同步调用响应: {response.text}')
    except requests.exceptions.Timeout:
        print('同步调用超时（10秒）')
    except Exception as e:
        print(f'同步调用失败: {e}')

def check_logs():
    """检查日志"""
    print('\n=== 检查日志 ===')
    
    logs_url = f'https://api.runpod.ai/v2/{endpoint_id}/logs'
    
    try:
        response = requests.get(logs_url, headers=headers, timeout=10)
        print(f'日志状态: {response.status_code}')
        print(f'日志内容: {response.text}')
    except Exception as e:
        print(f'获取日志失败: {e}')

if __name__ == "__main__":
    test_async_call()
    test_sync_with_shorter_timeout()
    check_logs() 