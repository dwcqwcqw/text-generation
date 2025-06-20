# 语音功能使用指南

本项目已集成语音转文字（STT）和文字转语音（TTS）功能，提供完整的语音交互体验。

## 🎤 语音转文字（Speech to Text）

### 技术架构
- **模型**: Whisper-large-v3-turbo
- **提供商**: RunPod Serverless
- **模型位置**: `/runpod-volume/voice/whisper-large-v3-turbo`
- **支持格式**: WebM, MP3, WAV 等
- **语言支持**: 自动检测多语言

### 使用方法
1. 点击输入框右侧的麦克风图标开始录音
2. 录音过程中按钮变红，显示"正在录音"提示
3. 再次点击停止录音，系统自动处理语音
4. 转录完成后文本自动填入输入框

### 技术特性
- **降噪处理**: 启用回声消除和噪音抑制
- **采样率**: 16kHz 优化语音识别
- **实时反馈**: 录音状态实时显示
- **自动填充**: 转录结果直接填入输入框

## 🔊 文字转语音（Text to Speech）

### 技术架构
- **API提供商**: MiniMax
- **模型**: speech-02-turbo
- **音频格式**: MP3
- **采样率**: 32kHz
- **比特率**: 128kbps

### 使用方法
1. AI回复完成后，消息框下方出现语音播放按钮
2. 点击播放按钮开始语音播放
3. 播放过程中可点击停止按钮终止播放
4. 支持多条消息的独立语音播放

### 语音配置
- **默认音色**: female-shaonv（少女音）
- **语速**: 1.0（正常速度）
- **音量**: 1.0（正常音量）
- **音调**: 0（标准音调）

## 📱 前端界面功能

### 录音界面
- **麦克风按钮**: 位于输入框右侧
- **状态指示**: 录音时显示红色，处理时显示加载动画
- **实时提示**: 显示"正在录音"和"正在处理语音"状态

### 播放界面
- **语音按钮**: 位于AI消息下方
- **播放状态**: 播放时图标变为停止图标
- **状态文字**: "语音播放" 或 "正在播放..."

## 🔧 技术配置

### 后端API配置
```bash
# MiniMax配置
MINIMAX_API_KEY=your_api_key_here
MINIMAX_GROUP_ID=your_group_id_here

# RunPod配置
RUNPOD_API_KEY=your_runpod_key
RUNPOD_ENDPOINT=https://api.runpod.ai/v2/your_endpoint/runsync
```

### API接口

#### 语音转文字
```
POST /speech/stt
Content-Type: application/json

{
  "audio_data": "base64_encoded_audio",
  "format": "webm"
}
```

#### 文字转语音
```
POST /speech/tts
Content-Type: application/json

{
  "text": "要转换的文本",
  "voice_id": "female-shaonv",
  "speed": 1.0,
  "volume": 1.0,
  "pitch": 0
}
```

## 🧪 测试方法

### 运行测试脚本
```bash
python test_voice_api.py
```

测试脚本会验证：
- 后端服务状态
- MiniMax API连接
- TTS功能完整性
- 音频文件生成

### 手动测试
1. **STT测试**: 在前端点击麦克风，说话后检查文本是否正确填入
2. **TTS测试**: 发送消息后点击语音播放按钮，检查音频是否正常播放

## 🛠️ 依赖安装

### 后端依赖
```bash
pip install openai-whisper ffmpeg-python pydub
```

### 系统依赖
```bash
# macOS
brew install ffmpeg

# Ubuntu
apt-get install ffmpeg

# CentOS
yum install ffmpeg
```

## 🚀 部署注意事项

### RunPod部署
1. 确保Whisper模型已下载到 `/runpod-volume/voice/whisper-large-v3-turbo`
2. 安装必要的音频处理库
3. 配置正确的RUNPOD_API_KEY

### 前端部署
1. 确保HTTPS环境（麦克风权限要求）
2. 配置正确的后端API地址
3. 测试浏览器兼容性

### 浏览器兼容性
- **Chrome**: 完整支持
- **Safari**: 支持，需用户授权
- **Firefox**: 支持
- **Edge**: 支持

## 🐛 故障排除

### 常见问题

#### 录音无法启动
- 检查麦克风权限
- 确保HTTPS环境
- 检查浏览器兼容性

#### 语音识别失败
- 检查RunPod服务状态
- 确认Whisper模型已加载
- 检查音频格式支持

#### 语音播放失败
- 检查MiniMax API Key
- 确认网络连接
- 检查音频格式支持

#### 后端连接失败
- 确认后端服务运行
- 检查API地址配置
- 查看CORS设置

### 日志调试
- 前端：打开浏览器开发者工具查看控制台
- 后端：查看FastAPI服务日志
- RunPod：查看RunPod实例日志

## 📈 性能优化

### 语音识别优化
- 使用合适的采样率（16kHz）
- 启用降噪功能
- 控制录音时长（建议30秒以内）

### 语音合成优化
- 控制文本长度
- 选择合适的音色
- 合理设置音频质量

### 网络优化
- 使用CDN加速
- 启用Gzip压缩
- 优化音频文件大小

## 🔮 未来扩展

### 功能扩展
- [ ] 支持更多语言模型
- [ ] 增加语音克隆功能
- [ ] 实时语音对话
- [ ] 语音情感识别

### 技术升级
- [ ] WebRTC实时通信
- [ ] 边缘计算加速
- [ ] 本地模型部署
- [ ] 多模态交互

---

**注意**: 确保所有API密钥和配置信息的安全性，不要在公共代码库中暴露敏感信息。 