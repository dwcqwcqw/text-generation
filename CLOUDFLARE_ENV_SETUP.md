# Cloudflare Pages 环境变量配置

## 重要说明

在Cloudflare Pages中，前端应用只能访问以`NEXT_PUBLIC_`开头的环境变量。

## 需要设置的环境变量

请在Cloudflare Pages的环境变量中设置以下变量：

### 1. RunPod API Key (必需)
```
变量名: NEXT_PUBLIC_RUNPOD_API_KEY
变量值: rpa_YT0BFBFZYAZM... (您的完整API Key)
```

### 2. RunPod Endpoint ID (可选，已有默认值)
```
变量名: NEXT_PUBLIC_RUNPOD_ENDPOINT_ID  
变量值: 4cx6jtjdx6hdhr
```

### 3. API Base URL (可选，已有默认值)
```
变量名: NEXT_PUBLIC_VITE_API_BASE_URL
变量值: https://api.runpod.ai/v2
```

## 当前设置检查

根据您的截图，您当前设置的是：
- ❌ `NEXT_PUBLIC_RUNPOD_API_KEY` (正确，但可能值不对)
- ❌ `RUNPOD_ENDPOINT_ID` (缺少NEXT_PUBLIC_前缀)
- ❌ `VITE_API_BASE_URL` (缺少NEXT_PUBLIC_前缀)

## 建议的修复步骤

1. **保留现有的**：
   - `NEXT_PUBLIC_RUNPOD_API_KEY` (确认值是完整的API Key)

2. **新增或修改**：
   - 将 `RUNPOD_ENDPOINT_ID` 改名为 `NEXT_PUBLIC_RUNPOD_ENDPOINT_ID`
   - 将 `VITE_API_BASE_URL` 改名为 `NEXT_PUBLIC_VITE_API_BASE_URL`

3. **最终配置应该是**：
   ```
   NEXT_PUBLIC_RUNPOD_API_KEY=rpa_YT0BFBFZYAZM...
   NEXT_PUBLIC_RUNPOD_ENDPOINT_ID=4cx6jtjdx6hdhr
   NEXT_PUBLIC_VITE_API_BASE_URL=https://api.runpod.ai/v2
   ```

## 测试方法

配置后重新部署，然后在浏览器控制台查看"Environment Variables Debug"输出，应该显示所有变量都是"SET"状态。 