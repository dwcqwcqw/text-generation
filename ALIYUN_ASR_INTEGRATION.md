# 阿里云语音识别 (ASR) 集成指南

## 当前状态

目前的实现使用**模拟数据**来保证语音功能的基本可用性。这是因为在 Cloudflare Workers 环境中实现完整的阿里云 API 签名比较复杂。

## 模拟功能

- ✅ 语音文件上传到 R2 存储
- ✅ 模拟任务提交和查询
- ✅ 返回预设的识别结果
- ✅ 完整的错误处理和日志

## 真实 API 集成方案

### 方案 1: 使用专门的后端服务

推荐在独立的 Node.js/Python 后端中集成阿里云官方 SDK：

```javascript
// Node.js 示例
const Client = require('@alicloud/nls20180518');

const client = new Client({
  accessKeyId: process.env.ALIYUN_ACCESS_KEY_ID,
  accessKeySecret: process.env.ALIYUN_ACCESS_KEY_SECRET,
  endpoint: 'https://nls-meta.cn-shanghai.aliyuncs.com'
});

// 提交识别任务
const submitTask = async (fileUrl, appKey) => {
  const request = {
    appKey: appKey,
    fileLink: fileUrl,
    version: '4.0',
    enableWords: false
  };
  
  const response = await client.createAsyncPredictTask(request);
  return response.body;
};

// 查询结果
const queryResult = async (taskId) => {
  const response = await client.getAsyncPredictResult({ taskId });
  return response.body;
};
```

### 方案 2: 在 Cloudflare Workers 中实现完整签名

需要实现阿里云的 OpenAPI 签名算法：

```javascript
async function generateAliyunSignature(params, secret, method = 'POST') {
  // 1. 规范化参数
  const sortedParams = Object.keys(params)
    .sort()
    .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
    .join('&');
  
  // 2. 构造待签名字符串
  const stringToSign = `${method}&${encodeURIComponent('/')}&${encodeURIComponent(sortedParams)}`;
  
  // 3. 计算签名
  const signature = await crypto.subtle.sign(
    'HMAC',
    await crypto.subtle.importKey('raw', new TextEncoder().encode(secret + '&'), { name: 'HMAC', hash: 'SHA-1' }, false, ['sign']),
    new TextEncoder().encode(stringToSign)
  );
  
  return btoa(String.fromCharCode(...new Uint8Array(signature)));
}
```

## 配置说明

需要配置的阿里云参数：

- **AccessKey ID**: 在环境变量中配置 `NEXT_PUBLIC_ALIYUN_ACCESS_KEY_ID`
- **AccessKey Secret**: 在环境变量中配置 `NEXT_PUBLIC_ALIYUN_ACCESS_KEY_SECRET`
- **App Key**: 在环境变量中配置 `NEXT_PUBLIC_ALIYUN_APP_KEY`

## 模拟结果类型

系统会根据任务ID返回以下随机结果之一：

1. "你好，这是一个语音识别测试。"
2. "请问有什么可以帮助您的吗？"
3. "今天天气真不错呢。"
4. "语音识别功能正在正常工作。"
5. "感谢您使用我们的服务。"

## 升级建议

1. **短期**: 继续使用当前的模拟实现，确保用户体验
2. **中期**: 部署专门的后端服务处理阿里云 API
3. **长期**: 考虑使用更简单的语音识别服务（如 OpenAI Whisper）

## 测试方法

1. 录制语音 → 上传到 R2
2. 提交识别任务 → 获得任务ID
3. 查询结果 → 获得模拟识别文本
4. 查看控制台日志了解详细过程

## 注意事项

- 文件必须成功上传到 R2 才能提交识别任务
- 模拟结果基于任务ID生成，保证一致性
- 所有操作都有完整的日志记录便于调试 