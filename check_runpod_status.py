#!/usr/bin/env python3
import requests
import json

# 测试RunPod endpoint状态
api_key = 'rpa_YT0BFBFZYAZMQHR231H4DOKQEOAJXSMVIBDYN4ZQ1tdxlb'
endpoint_id = '4cx6jtjdx6hdhr'

# 检查endpoint状态
status_url = f'https://api.runpod.ai/v2/{endpoint_id}/status'
health_url = f'https://api.runpod.ai/v2/{endpoint_id}/health'

headers = {'Authorization': f'Bearer {api_key}'}

print('=== 检查Endpoint状态 ===')
try:
    response = requests.get(status_url, headers=headers, timeout=10)
    print(f'Status URL: {status_url}')
    print(f'Status Code: {response.status_code}')
    print(f'Response: {response.text}')
except Exception as e:
    print(f'Status检查失败: {e}')

print('\n=== 检查Endpoint健康 ===')
try:
    response = requests.get(health_url, headers=headers, timeout=10)
    print(f'Health URL: {health_url}')
    print(f'Health Code: {response.status_code}')
    print(f'Response: {response.text}')
except Exception as e:
    print(f'Health检查失败: {e}')

print('\n=== 尝试简单API调用 ===')
try:
    api_url = f'https://api.runpod.ai/v2/{endpoint_id}/runsync'
    payload = {"input": {"prompt": "Hello"}}
    response = requests.post(api_url, headers=headers, json=payload, timeout=30)
    print(f'API URL: {api_url}')
    print(f'API Code: {response.status_code}')
    print(f'API Response: {response.text}')
except Exception as e:
    print(f'API调用失败: {e}') 