# RunPod 配置说明

## 前端配置 (已更新)

前端现在已经配置为直接调用RunPod Serverless API，无需本地后端服务。

### API配置详情：

- **RunPod Endpoint**: `https://api.runpod.ai/v2/4cx6jtjdx6hdhr/runsync`
- **支持的模型**:
  - `L3.2-8X3B`: `/runpod-volume/text_models/L3.2-8X3B.gguf` (Llama-3.2-8X3B, 18.4B parameters)
  - `L3.2-8X4B`: `/runpod-volume/text_models/L3.2-8X4B.gguf` (Llama-3.2-8X4B, 21B parameters)

### 配置RunPod API Key

为了使用RunPod API，您需要设置API Key：

#### 方法1: 环境变量 (推荐用于生产环境)
在Cloudflare Pages的环境变量中设置：
```
NEXT_PUBLIC_RUNPOD_API_KEY=your_actual_runpod_api_key_here
```

#### 方法2: 本地开发环境
在 `frontend/.env.local` 文件中添加：
```
NEXT_PUBLIC_RUNPOD_API_KEY=your_actual_runpod_api_key_here
```

#### 方法3: 直接修改代码 (仅用于测试)
在 `frontend/src/app/page.tsx` 第172行左右，将：
```typescript
const RUNPOD_API_KEY = process.env.NEXT_PUBLIC_RUNPOD_API_KEY || ''
```
修改为：
```typescript
const RUNPOD_API_KEY = 'your_actual_runpod_api_key_here'
```

### 功能特性

1. **智能回退**: 如果RunPod API不可用或未配置API Key，系统会自动使用模拟回复
2. **Llama格式支持**: 自动使用正确的Llama-3.2 prompt格式
3. **模型选择**: 用户可以在界面中选择不同的模型
4. **错误处理**: 完善的错误处理和日志记录

### API请求格式

前端发送给RunPod的请求格式：
```json
{
  "input": {
    "model_path": "/runpod-volume/text_models/L3.2-8X3B.gguf",
    "prompt": "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nYou are a helpful, harmless, and honest assistant.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n用户输入<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
    "max_tokens": 150,
    "temperature": 0.7,
    "top_p": 0.9,
    "repeat_penalty": 1.05,
    "stop": ["<|eot_id|>", "<|end_of_text|>", "<|start_header_id|>"],
    "stream": false
  }
}
```

### 部署状态

- ✅ 前端已配置为直接调用RunPod API
- ✅ 支持多模型选择
- ✅ 智能回退机制
- ✅ 静态文件部署到Cloudflare Pages
- ⚠️ 需要配置RunPod API Key才能使用真实AI功能

### 下一步

1. 获取您的RunPod API Key
2. 在Cloudflare Pages环境变量中配置API Key
3. 重新部署前端应用
4. 测试AI聊天功能 