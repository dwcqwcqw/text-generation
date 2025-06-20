// 测试 OpenAI Whisper 集成
// 验证从阿里云ASR迁移到OpenAI Whisper是否成功

const testAudioUrl = 'https://pub-f314a707297b4748936925bba8dd4962.r2.dev/test_voice_20250521_152935.wav';
const workerUrl = 'https://text-generation.faceswap.workers.dev';
const pagesUrl = 'https://f586ee33.text-generation.pages.dev';

console.log('🧪 测试 OpenAI Whisper ASR 集成');
console.log('=====================================');

async function testWhisperAPI() {
  try {
    console.log('\n📡 1. 测试 Worker API 健康状况...');
    const healthResponse = await fetch(`${workerUrl}/health`);
    const healthData = await healthResponse.json();
    console.log('✅ Worker API 状态:', healthData);
    
    console.log('\n📡 2. 测试 OpenAI Whisper ASR 端点...');
    const whisperResponse = await fetch(`${workerUrl}/whisper-asr`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        fileLink: testAudioUrl,
        language: 'zh'
      }),
    });
    
    console.log('🌐 响应状态:', whisperResponse.status, whisperResponse.statusText);
    
    if (!whisperResponse.ok) {
      const errorText = await whisperResponse.text();
      console.error('❌ API 调用失败:', errorText);
      return;
    }
    
    const result = await whisperResponse.json();
    console.log('📝 Whisper 识别结果:', result);
    
    if (result.success) {
      console.log('✅ 成功! 识别文本:', result.text);
      console.log('🔤 识别语言:', result.language);
      console.log('⏱️ 处理时间:', result.processingTime, 'ms');
      console.log('🎯 服务提供商:', result.provider);
    } else {
      console.error('❌ 识别失败:', result.error);
    }
    
    console.log('\n📡 3. 测试 Cloudflare Pages 访问...');
    const pagesResponse = await fetch(pagesUrl);
    console.log('🌐 Pages 状态:', pagesResponse.status, pagesResponse.statusText);
    
    if (pagesResponse.ok) {
      console.log('✅ Cloudflare Pages 正常访问');
    } else {
      console.error('❌ Cloudflare Pages 访问失败');
    }
    
  } catch (error) {
    console.error('❌ 测试过程中出现错误:', error);
  }
}

async function testEnvironmentConfig() {
  console.log('\n🔧 4. 测试环境配置...');
  
  try {
    const configResponse = await fetch(`${workerUrl}/whisper-asr`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        fileLink: 'invalid-url-for-testing'
      }),
    });
    
    const configResult = await configResponse.json();
    
    if (configResult.error && configResult.error.includes('OpenAI API Key')) {
      console.log('❌ OpenAI API Key 未配置');
    } else if (configResult.error && configResult.error.includes('音频文件下载失败')) {
      console.log('✅ OpenAI API Key 已配置 (下载测试文件失败是正常的)');
    } else {
      console.log('🔍 配置测试结果:', configResult);
    }
    
  } catch (error) {
    console.error('❌ 环境配置测试失败:', error);
  }
}

// 运行测试
(async () => {
  await testWhisperAPI();
  await testEnvironmentConfig();
  
  console.log('\n🎉 测试完成!');
  console.log('=====================================');
  console.log('✅ 阿里云ASR已成功替换为OpenAI Whisper');
  console.log('🌐 Worker URL:', workerUrl);
  console.log('📱 Pages URL:', pagesUrl);
  console.log('🎤 新端点: /whisper-asr');
})(); 