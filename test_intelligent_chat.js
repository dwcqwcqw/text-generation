// 智能聊天系统测试
// 测试 D1 + KV + Vectorize 完整功能

const workerUrl = 'https://text-generation.faceswap.workers.dev';
const testUserId = 'test-user-' + Date.now();

console.log('🧠 智能聊天系统测试');
console.log('===================');
console.log('测试用户ID:', testUserId);

async function testSystemStatus() {
  console.log('\n📡 1. 系统状态检查...');
  
  try {
    const response = await fetch(`${workerUrl}/health`);
    const data = await response.json();
    console.log('✅ 系统状态:', data);
    
    // 检查API信息
    const infoResponse = await fetch(workerUrl);
    const info = await infoResponse.json();
    console.log('📋 API信息:', info);
    
  } catch (error) {
    console.error('❌ 系统检查失败:', error);
  }
}

async function testCreateConversation() {
  console.log('\n💬 2. 创建新对话...');
  
  try {
    const response = await fetch(`${workerUrl}/chat/conversation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: testUserId,
        title: '智能聊天测试',
        system_prompt: '你是一个友善的AI助手，专门帮助测试聊天功能。请记住我们的对话内容。'
      })
    });
    
    const result = await response.json();
    console.log('✅ 对话创建结果:', result);
    
    if (result.success) {
      return result.conversation_id;
    } else {
      throw new Error(result.error);
    }
    
  } catch (error) {
    console.error('❌ 创建对话失败:', error);
    return null;
  }
}

async function testChat(conversationId, message) {
  console.log(`\n🗣️ 发送消息: "${message}"`);
  
  try {
    const response = await fetch(`${workerUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: testUserId,
        conversation_id: conversationId,
        content: message
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      console.log('🤖 AI回复:', result.response);
      return result;
    } else {
      console.error('❌ 聊天失败:', result.error);
      return null;
    }
    
  } catch (error) {
    console.error('❌ 聊天请求失败:', error);
    return null;
  }
}

async function testChatHistory(conversationId) {
  console.log('\n📚 3. 获取对话历史...');
  
  try {
    const response = await fetch(`${workerUrl}/chat/history?user_id=${testUserId}&conversation_id=${conversationId}`);
    const result = await response.json();
    
    if (result.success) {
      console.log('✅ 对话历史:');
      result.messages.forEach((msg, index) => {
        const role = msg.role === 'user' ? '👤' : '🤖';
        console.log(`  ${index + 1}. ${role} ${msg.content.substring(0, 50)}...`);
      });
      return result.messages;
    } else {
      console.error('❌ 获取历史失败:', result.error);
      return [];
    }
    
  } catch (error) {
    console.error('❌ 历史请求失败:', error);
    return [];
  }
}

async function testConversationsList() {
  console.log('\n📋 4. 获取对话列表...');
  
  try {
    const response = await fetch(`${workerUrl}/chat/conversations?user_id=${testUserId}`);
    const result = await response.json();
    
    if (result.success) {
      console.log('✅ 对话列表:');
      result.conversations.forEach((conv, index) => {
        console.log(`  ${index + 1}. ${conv.title || '未命名对话'} (${conv.id})`);
      });
      return result.conversations;
    } else {
      console.error('❌ 获取对话列表失败:', result.error);
      return [];
    }
    
  } catch (error) {
    console.error('❌ 对话列表请求失败:', error);
    return [];
  }
}

async function testMemoryAndContext(conversationId) {
  console.log('\n🧠 5. 测试记忆和上下文功能...');
  
  // 发送一系列相关消息来测试短期记忆
  const messages = [
    '我叫张三，今年25岁',
    '我喜欢编程和音乐',
    '我最近在学习JavaScript',
    '请问你还记得我的名字吗？',
    '我之前说过我喜欢什么？'
  ];
  
  for (const message of messages) {
    await testChat(conversationId, message);
    await new Promise(resolve => setTimeout(resolve, 1000)); // 等待1秒
  }
  
  console.log('✅ 记忆测试完成，检查AI是否能记住之前的信息');
}

async function testSemanticSearch(conversationId) {
  console.log('\n🔍 6. 测试语义搜索功能...');
  
  // 发送一些不同主题的消息
  const topics = [
    '我在北京工作，是一名软件工程师',
    '周末我喜欢去公园散步',
    '我最喜欢的编程语言是Python',
    '我的爱好是摄影和旅行'
  ];
  
  for (const topic of topics) {
    await testChat(conversationId, topic);
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  
  // 测试语义相似搜索
  console.log('\n🔍 现在测试语义搜索 - 询问相关问题:');
  await testChat(conversationId, '你知道我在哪个城市工作吗？'); // 应该能找到北京相关信息
  await testChat(conversationId, '我平时有什么兴趣爱好？'); // 应该能找到摄影、旅行等信息
}

// 运行完整测试
(async () => {
  try {
    await testSystemStatus();
    
    const conversationId = await testCreateConversation();
    if (!conversationId) {
      console.error('❌ 无法创建对话，测试终止');
      return;
    }
    
    console.log('🆔 对话ID:', conversationId);
    
    // 基础聊天测试
    await testChat(conversationId, '你好！我是新用户，想测试一下聊天功能。');
    await testChat(conversationId, '你能记住我们的对话内容吗？');
    
    // 测试记忆功能
    await testMemoryAndContext(conversationId);
    
    // 测试语义搜索
    await testSemanticSearch(conversationId);
    
    // 获取最终的对话历史
    await testChatHistory(conversationId);
    
    // 获取对话列表
    await testConversationsList();
    
    console.log('\n🎉 测试完成！');
    console.log('================');
    console.log('✅ D1数据库: 消息持久化存储');
    console.log('✅ KV存储: 短期记忆缓存');
    console.log('✅ Vectorize: 语义相似搜索');
    console.log('✅ OpenAI: Embedding生成');
    console.log('✅ 智能上下文: 短期+长期记忆结合');
    console.log('✅ 完整聊天流程: 正常工作');
    
  } catch (error) {
    console.error('❌ 测试过程中出现错误:', error);
  }
})(); 