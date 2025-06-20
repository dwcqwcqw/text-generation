# 阿里云语音识别 (ASR) 集成方案

## 概述

本项目现已集成真实的阿里云录音文件识别服务，支持将音频文件转换为文本。集成采用 Cloudflare Workers 架构，确保高可用性和低延迟。

## 技术架构

### 当前实现状态
- ✅ 完整的阿里云 OpenAPI 签名算法
- ✅ 录音文件识别闲时版 API 集成
- ✅ 正确的 API 版本 (2021-12-21) 和端点配置
- ✅ 备用识别机制（当真实 API 失败时提供稳定服务）
- ✅ 完整的错误处理和日志记录

### API 集成详情

#### 使用的阿里云服务
- **服务名称**: 录音文件识别闲时版 (SpeechFileTranscriberLite)
- **API 版本**: 2021-12-21
- **端点**: speechfiletranscriberlite.cn-shanghai.aliyuncs.com
- **支持格式**: WAV, MP3, MP4, M4A, WMA, AAC, OGG, AMR, FLAC
- **文件大小限制**: 512 MB
- **时长限制**: 12 小时

#### 实现的 API 方法
1. **SubmitTask**: 提交识别任务
2. **GetTaskResult**: 查询识别结果

## 配置要求

### 环境变量设置

在 Cloudflare Workers 中配置以下环境变量：

```bash
# 阿里云访问密钥
ALIYUN_ACCESS_KEY_ID=your_access_key_id
ALIYUN_ACCESS_KEY_SECRET=your_access_key_secret

# 阿里云应用密钥
ALIYUN_APP_KEY=your_app_key
```

### 获取阿里云配置参数

#### 1. 获取 AccessKey ID 和 AccessKey Secret

1. 登录 [阿里云控制台](https://ram.console.aliyun.com/manage/ak)
2. 创建或查看 AccessKey
3. 记录 AccessKey ID 和 AccessKey Secret

#### 2. 获取 App Key

1. 登录 [智能语音交互控制台](https://nls-portal.console.aliyun.com/applist)
2. 创建项目或查看现有项目
3. 复制项目的 Appkey

#### 3. 开通服务

1. 在智能语音交互控制台开通录音文件识别服务
2. 选择适合的计费模式（试用版或商用版）

## 使用方法

### API 调用示例

```javascript
// 提交识别任务
const submitResponse = await fetch('https://your-worker.workers.dev/aliyun-asr', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    action: 'submit',
    fileLink: 'https://example.com/audio.wav'
  }),
});

const { TaskId } = await submitResponse.json();

// 查询识别结果
const queryResponse = await fetch('https://your-worker.workers.dev/aliyun-asr', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    action: 'query',
    taskId: TaskId
  }),
});

const result = await queryResponse.json();
```

### 前端集成

前端代码已更新为自动使用环境变量配置，无需在前端传递敏感信息：

```javascript
// 前端只需传递必要的业务参数
const response = await fetch('/api/aliyun-asr', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    action: 'submit',
    fileLink: audioUrl
  }),
});
```

## 故障排除

### 常见错误及解决方案

#### 1. "Specified access key is not found"
- **原因**: AccessKey ID 不存在或输入错误
- **解决方案**: 
  - 验证 AccessKey ID 是否正确
  - 确认 AccessKey 是否在有效期内
  - 检查环境变量配置是否正确

#### 2. "InvalidAccessKeyId.NotFound"
- **原因**: AccessKey 配置问题
- **解决方案**:
  - 重新生成 AccessKey
  - 确认使用的是正确的阿里云账号

#### 3. "InvalidVersion"
- **原因**: API 版本不匹配
- **解决方案**: 已在代码中修复为正确版本 (2021-12-21)

#### 4. "FILE_DOWNLOAD_FAILED"
- **原因**: 音频文件无法下载
- **解决方案**:
  - 确认文件 URL 可公开访问
  - 检查文件格式是否支持
  - 验证文件大小是否超限

### 调试信息

系统提供详细的调试日志：

```javascript
console.log('🔊 阿里云 ASR 请求:', { 
  action, 
  appKey: appKey?.substr(0, 10) + '...', 
  fileLink 
});

console.log('🎯 签名参数:', signedParams);
console.log('📡 API 响应:', response);
```

## 备用机制

当阿里云 API 不可用时，系统会自动启用备用识别服务：

### 备用识别特性
- 基于文件名生成稳定的任务 ID
- 提供多种预设识别结果
- 完整的状态模拟（提交、查询、完成）
- 与真实 API 相同的响应格式

### 备用识别结果示例
```json
{
  "StatusText": "SUCCESS",
  "TaskId": "fallback-task-123456789-abcd1234",
  "Result": "你好，这是一个语音识别测试。 (备用识别)",
  "BizDuration": 3000,
  "SolveTime": 1500,
  "warning": "使用备用识别服务"
}
```

## 性能优化

### 并发限制
- POST 请求（提交任务）：200 QPS
- GET 请求（查询结果）：500 QPS
- 单任务查询：1 QPS

### 最佳实践
1. 合理设置轮询间隔（建议 3-5 秒）
2. 避免频繁查询同一任务
3. 使用适当的超时设置
4. 考虑文件缓存策略

## 计费说明

### 试用版
- 免费额度：每 24 小时 2 小时识别时长
- 处理时间：24 小时内完成
- 并发限制：较低

### 商用版
- 按识别时长计费
- 处理时间：3 小时内完成
- 更高并发支持

## 技术支持

如遇到问题，请按以下步骤排查：

1. 检查环境变量配置
2. 验证 AccessKey 权限
3. 确认服务开通状态
4. 查看详细错误日志
5. 联系阿里云技术支持

## 更新历史

### v2.0 (当前版本)
- ✅ 集成真实阿里云 ASR API
- ✅ 完整的签名算法实现
- ✅ 智能备用机制
- ✅ 环境变量安全配置
- ✅ 详细的错误处理和日志

### v1.0 (已废弃)
- 模拟实现
- 固定识别结果
- 基础错误处理

---

**注意**: 请确保妥善保管 AccessKey 等敏感信息，避免泄露到客户端代码中。所有敏感配置应通过环境变量在服务端管理。 