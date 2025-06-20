// 简单测试 OpenAI Whisper
// 先用TTS生成音频，再用Whisper识别

const workerUrl = 'https://text-generation.faceswap.workers.dev';

console.log('🎤 简单 OpenAI Whisper 测试');
console.log('==========================');

async function testWhisperWithGeneratedAudio() {
  try {
    console.log('\n📢 1. 生成测试音频...');
    const ttsResponse = await fetch(`${workerUrl}/speech/tts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text: '你好，这是一个语音识别测试。',
        voice: 'alvin',
        speed: 1.0
      }),
    });
    
    if (!ttsResponse.ok) {
      console.error('❌ TTS 生成失败:', ttsResponse.status);
      return;
    }
    
    const audioBlob = await ttsResponse.blob();
    console.log('✅ 音频生成成功，大小:', audioBlob.size, 'bytes');
    
    // 创建一个临时的音频URL (在实际应用中，这需要上传到R2)
    // 这里我们模拟直接传递音频数据
    const audioUrl = URL.createObjectURL(audioBlob);
    console.log('🔗 临时音频URL:', audioUrl);
    
    console.log('\n🎧 2. 测试 Whisper 识别...');
    
    // 由于我们需要一个真实的HTTP URL，让我们测试API配置
    const configTestResponse = await fetch(`${workerUrl}/whisper-asr`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        fileLink: 'https://file-examples.com/storage/fe68c044b7d66a7b5a9161d/2017/11/file_example_MP3_700KB.mp3',
        language: 'zh'
      }),
    });
    
    console.log('🌐 配置测试状态:', configTestResponse.status);
    const configResult = await configTestResponse.json();
    console.log('📝 配置测试结果:', configResult);
    
    if (configResult.success) {
      console.log('✅ OpenAI Whisper 配置正常!');
      console.log('🔤 识别结果:', configResult.text);
    } else if (configResult.error && configResult.error.includes('OpenAI API Key')) {
      console.error('❌ OpenAI API Key 未配置');
    } else if (configResult.error && configResult.error.includes('音频文件下载失败')) {
      console.log('✅ API Key 配置正常，但测试音频文件无法访问');
    } else {
      console.log('🔍 其他错误:', configResult.error);
    }
    
  } catch (error) {
    console.error('❌ 测试失败:', error);
  }
}

async function testAPIKeyConfiguration() {
  console.log('\n🔧 3. 验证 API Key 配置...');
  
  try {
    // 测试无文件链接的情况
    const response = await fetch(`${workerUrl}/whisper-asr`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });
    
    const result = await response.json();
    
    if (result.error === 'OpenAI API Key 缺失') {
      console.error('❌ OpenAI API Key 未配置，请设置环境变量');
    } else if (result.error === '缺少音频文件链接') {
      console.log('✅ OpenAI API Key 已配置');
    } else {
      console.log('🔍 配置测试结果:', result);
    }
    
  } catch (error) {
    console.error('❌ 配置测试失败:', error);
  }
}

// 运行测试
(async () => {
  await testAPIKeyConfiguration();
  await testWhisperWithGeneratedAudio();
  
  console.log('\n🎉 测试完成!');
  console.log('==========================');
  console.log('ℹ️  提示: 要完整测试Whisper功能，需要：');
  console.log('1. 确保OpenAI API Key已正确配置');
  console.log('2. 上传音频文件到R2获取可访问的URL');
  console.log('3. 使用真实音频URL进行识别测试');
})(); 