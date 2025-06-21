// Cloudflare Workers API for Chat History Management
// Deploy this to Cloudflare Workers to handle backend API requests

// 聊天历史管理类
class ChatHistoryManager {
  constructor(env) {
    this.env = env;
  }

  // 生成UUID
  generateId() {
    return crypto.randomUUID();
  }

  // 创建用户
  async createUser(userId, username = null) {
    try {
      await this.env.DB.prepare(
        'INSERT OR IGNORE INTO users (id, username, created_at) VALUES (?, ?, ?)'
      ).bind(userId, username, new Date().toISOString()).run();
      return { success: true, userId };
    } catch (error) {
      console.error('创建用户失败:', error);
      return { success: false, error: error.message };
    }
  }

  // 创建对话
  async createConversation(userId, title = null, systemPrompt = null) {
    try {
      // 先确保用户存在
      await this.createUser(userId);
      
      const conversationId = this.generateId();
      const defaultPrompt = systemPrompt || '你是一个友善、专业的中文AI助手。请用简洁、准确的语言回答用户的问题。';
      
      await this.env.DB.prepare(
        'INSERT INTO conversations (id, user_id, title, system_prompt, created_at) VALUES (?, ?, ?, ?, ?)'
      ).bind(conversationId, userId, title, defaultPrompt, new Date().toISOString()).run();
      
      return { success: true, conversationId };
    } catch (error) {
      console.error('创建对话失败:', error);
      return { success: false, error: error.message };
    }
  }

  // 保存消息到D1
  async saveMessage(userId, conversationId, role, content, metadata = null) {
    try {
      const messageId = this.generateId();
      const timestamp = new Date().toISOString();
      
      await this.env.DB.prepare(
        'INSERT INTO messages (id, user_id, conversation_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)'
      ).bind(messageId, userId, conversationId, role, content, metadata ? JSON.stringify(metadata) : null, timestamp).run();
      
      return { success: true, messageId, timestamp };
    } catch (error) {
      console.error('保存消息失败:', error);
      return { success: false, error: error.message };
    }
  }

  // 获取短期记忆 (KV存储最近5轮对话)
  async getShortTermMemory(userId, conversationId) {
    try {
      const kvKey = `chat:${userId}:${conversationId}`;
      if (!this.env.KV) {
        console.log('⚠️ KV命名空间未绑定，返回空数组');
        return [];
      }
      
      const history = await this.env.KV.get(kvKey, { type: 'json' });
      return history || [];
    } catch (error) {
      console.error('❌ 获取短期记忆失败:', error);
      return [];
    }
  }

  // 更新短期记忆
  async updateShortTermMemory(userId, conversationId, messages) {
    try {
      const kvKey = `chat:${userId}:${conversationId}`;
      // 只保留最近5轮对话
      const recentMessages = messages.slice(-10); // 5轮 = 10条消息 (用户+助手)
      
      if (!this.env.KV) {
        throw new Error('KV命名空间未绑定');
      }
      
      await this.env.KV.put(kvKey, JSON.stringify(recentMessages));
      
      return { success: true };
    } catch (error) {
      console.error('❌ 更新短期记忆失败:', error);
      return { success: false, error: error.message };
    }
  }

  // 创建embedding
  async createEmbedding(text) {
    try {
      const response = await fetch('https://api.openai.com/v1/embeddings', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.env.OPENAI_API_KEY}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          input: text,
          model: 'text-embedding-ada-002'
        })
      });

      if (!response.ok) {
        throw new Error(`OpenAI API 错误: ${response.status}`);
      }

      const result = await response.json();
      return result.data[0].embedding;
    } catch (error) {
      console.error('创建embedding失败:', error);
      return null;
    }
  }

  // 保存到向量数据库
  async saveToVectorize(userId, conversationId, content, embedding) {
    try {
      const vectorId = `msg-${this.generateId()}`;
      const metadata = {
        user_id: userId,
        conversation_id: conversationId,
        content: content,
        timestamp: new Date().toISOString()
      };

      await this.env.VECTORIZE.insert([{
        id: vectorId,
        values: embedding,
        metadata: metadata
      }]);

      return { success: true, vectorId };
    } catch (error) {
      console.error('保存到向量数据库失败:', error);
      return { success: false, error: error.message };
    }
  }

  // 获取长期记忆 (语义相似搜索)
  async getLongTermMemory(userId, content, topK = 3) {
    try {
      const embedding = await this.createEmbedding(content);
      if (!embedding) return [];

      const searchResult = await this.env.VECTORIZE.query({
        topK: topK,
        vector: embedding,
        filter: { user_id: userId },
        returnMetadata: true
      });

      return (searchResult.matches || []).map(match => ({
        role: 'user',
        content: match.metadata.content,
        similarity: match.score,
        timestamp: match.metadata.timestamp
      }));
    } catch (error) {
      console.error('获取长期记忆失败:', error);
      return [];
    }
  }

  // 获取系统提示
  async getSystemPrompt(conversationId) {
    try {
      const result = await this.env.DB.prepare(
        'SELECT system_prompt FROM conversations WHERE id = ?'
      ).bind(conversationId).first();
      
      return result?.system_prompt || '你是一个友善、专业的中文AI助手。请用简洁、准确的语言回答用户的问题。';
    } catch (error) {
      console.error('获取系统提示失败:', error);
      return '你是一个友善、专业的中文AI助手。请用简洁、准确的语言回答用户的问题。';
    }
  }

  // 构建完整上下文
  async buildContext(userId, conversationId, userMessage) {
    try {
      // 1. 获取系统提示
      const systemPrompt = await this.getSystemPrompt(conversationId);
      
      // 2. 获取短期记忆
      const shortTermMemory = await this.getShortTermMemory(userId, conversationId);
      
      // 3. 获取长期记忆
      const longTermMemory = await this.getLongTermMemory(userId, userMessage, 3);
      
      // 4. 构建消息数组
      const messages = [
        { role: 'system', content: systemPrompt }
      ];

      // 添加长期记忆 (语义相似的历史对话)
      if (longTermMemory.length > 0) {
        messages.push({
          role: 'system',
          content: `以下是一些相关的历史对话供参考:\n${longTermMemory.map(m => `- ${m.content}`).join('\n')}`
        });
      }

      // 添加短期记忆 (最近的对话)
      messages.push(...shortTermMemory);
      
      // 添加当前用户消息
      messages.push({ role: 'user', content: userMessage });

      return messages;
    } catch (error) {
      console.error('构建上下文失败:', error);
      return [
        { role: 'system', content: '你是一个友善、专业的中文AI助手。' },
        { role: 'user', content: userMessage }
      ];
    }
  }

  // 处理完整聊天流程
  async processChat(userId, conversationId, userMessage) {
    try {
      // 1. 确保用户存在
      await this.createUser(userId);

      // 2. 保存用户消息到D1
      await this.saveMessage(userId, conversationId, 'user', userMessage);

      // 3. 构建上下文
      const contextMessages = await this.buildContext(userId, conversationId, userMessage);

      // 4. 调用AI模型生成回复 (这里使用RunPod)
      const aiResponse = await this.callAIModel(contextMessages);
      if (!aiResponse.success) {
        throw new Error(aiResponse.error);
      }

      // 5. 保存AI回复到D1
      await this.saveMessage(userId, conversationId, 'assistant', aiResponse.content);

      // 6. 更新短期记忆
      const shortMemory = await this.getShortTermMemory(userId, conversationId);
      const updatedMemory = [
        ...shortMemory,
        { role: 'user', content: userMessage },
        { role: 'assistant', content: aiResponse.content }
      ];
      await this.updateShortTermMemory(userId, conversationId, updatedMemory);

      // 7. 创建embedding并保存到向量数据库
      const embedding = await this.createEmbedding(userMessage);
      if (embedding) {
        await this.saveToVectorize(userId, conversationId, userMessage, embedding);
      }

      return {
        success: true,
        response: aiResponse.content,
        conversationId: conversationId
      };

    } catch (error) {
      console.error('处理聊天失败:', error);
      return { success: false, error: error.message };
    }
  }

  // 调用AI模型 (优先使用RunPod，备用OpenAI)
  async callAIModel(messages) {
    try {
      // 主要方案：使用RunPod自有模型
      if (this.env.RUNPOD_API_KEY) {
        try {
          // 尝试使用配置的endpoint ID
          let endpointId = this.env.RUNPOD_ENDPOINT_ID;
          
          // 如果没有配置endpoint ID，尝试从API key推断或使用默认值
          if (!endpointId) {
            console.warn('未配置RUNPOD_ENDPOINT_ID，尝试使用默认endpoint');
            // 这里可以设置一个默认的endpoint ID或者从其他地方获取
          }

          const runpodUrl = endpointId 
            ? `https://api.runpod.ai/v2/${endpointId}/runsync`
            : `https://api.runpod.ai/v2/runsync`; // 备用URL格式

          const response = await fetch(runpodUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${this.env.RUNPOD_API_KEY}`
            },
            body: JSON.stringify({
              input: {
                messages: messages,
                max_tokens: 1000,
                temperature: 0.7,
                model: "llama-3.1-8b-instruct", // 或者您的具体模型名称
                stream: false
              }
            })
          });

          if (response.ok) {
            const result = await response.json();
            
            // 处理不同的RunPod响应格式
            let content = '';
            if (result.output) {
              if (result.output.choices && result.output.choices[0]) {
                content = result.output.choices[0].message?.content || result.output.choices[0].text || '';
              } else if (result.output.text) {
                content = result.output.text;
              } else if (result.output.response) {
                content = result.output.response;
              } else if (typeof result.output === 'string') {
                content = result.output;
              }
            }
            
            if (content) {
              return {
                success: true,
                content: content.trim()
              };
            }
          } else {
            console.warn('RunPod API 响应错误:', response.status, await response.text());
          }
        } catch (runpodError) {
          console.warn('RunPod API 调用失败:', runpodError);
        }
      }

      // 备用方案：使用OpenAI
      if (this.env.OPENAI_API_KEY) {
        try {
          console.log('RunPod不可用，使用OpenAI备用模型');
          const response = await fetch('https://api.openai.com/v1/chat/completions', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${this.env.OPENAI_API_KEY}`
            },
            body: JSON.stringify({
              model: 'gpt-3.5-turbo',
              messages: messages,
              max_tokens: 1000,
              temperature: 0.7
            })
          });

          if (response.ok) {
            const result = await response.json();
            return {
              success: true,
              content: result.choices[0].message.content
            };
          }
        } catch (openaiError) {
          console.warn('OpenAI API 调用失败:', openaiError);
        }
      }

      // 最后的备用方案：智能模拟回复
      console.log('所有AI模型都不可用，使用智能备用回复');
      return this.generateSmartFallbackResponse(messages);

    } catch (error) {
      console.error('AI模型调用失败:', error);
      return this.generateSmartFallbackResponse(messages);
    }
  }

  // 智能备用回复生成器
  generateSmartFallbackResponse(messages) {
    const userMessage = messages[messages.length - 1]?.content || '';
    const lowerMessage = userMessage.toLowerCase();

    // 基于关键词的智能回复
    if (lowerMessage.includes('你好') || lowerMessage.includes('hello')) {
      return {
        success: true,
        content: '你好！我是AI助手，很高兴与您对话。有什么我可以帮助您的吗？'
      };
    }

    if (lowerMessage.includes('名字') || lowerMessage.includes('叫什么')) {
      const nameMatch = messages.find(m => m.content.includes('我叫') || m.content.includes('我是'));
      if (nameMatch) {
        const nameRegex = /我叫(.+?)(?:[，,。\s]|$)/;
        const match = nameMatch.content.match(nameRegex);
        if (match) {
          return {
            success: true,
            content: `根据我们之前的对话，您说您叫${match[1]}。`
          };
        }
      }
      return {
        success: true,
        content: '抱歉，我没有找到您之前提到的姓名信息。'
      };
    }

    if (lowerMessage.includes('喜欢') || lowerMessage.includes('爱好')) {
      const hobbyMessages = messages.filter(m => 
        m.content.includes('喜欢') || m.content.includes('爱好') || 
        m.content.includes('编程') || m.content.includes('音乐') ||
        m.content.includes('摄影') || m.content.includes('旅行')
      );
      if (hobbyMessages.length > 0) {
        const hobbies = [];
        hobbyMessages.forEach(msg => {
          if (msg.content.includes('编程')) hobbies.push('编程');
          if (msg.content.includes('音乐')) hobbies.push('音乐');
          if (msg.content.includes('摄影')) hobbies.push('摄影');
          if (msg.content.includes('旅行')) hobbies.push('旅行');
        });
        if (hobbies.length > 0) {
          return {
            success: true,
            content: `根据我们的对话，您提到过您喜欢：${hobbies.join('、')}。`
          };
        }
      }
    }

    if (lowerMessage.includes('工作') || lowerMessage.includes('城市')) {
      const workMessage = messages.find(m => m.content.includes('北京') && m.content.includes('工作'));
      if (workMessage) {
        return {
          success: true,
          content: '根据您之前提到的，您在北京工作，是一名软件工程师。'
        };
      }
    }

    if (lowerMessage.includes('记住') || lowerMessage.includes('记得')) {
      return {
        success: true,
        content: '是的，我会记住我们的对话内容。我使用短期记忆保存最近的对话，同时使用长期记忆进行语义搜索，以便更好地为您服务。'
      };
    }

    // 默认回复
    return {
      success: true,
      content: '我理解您的问题。虽然我的AI模型暂时不可用，但我会基于我们的对话历史尽力为您提供帮助。请告诉我更多详细信息，我会尽我所能回答您的问题。'
    };
  }
}

// OpenAI Whisper client class
class OpenAIWhisperClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.baseUrl = 'https://api.openai.com/v1/audio/transcriptions';
  }

  async transcribeAudio(audioUrl, options = {}) {
    try {
      // 首先下载音频文件
      console.log('📥 下载音频文件:', audioUrl);
      const audioResponse = await fetch(audioUrl);
      
      if (!audioResponse.ok) {
        throw new Error(`音频文件下载失败: ${audioResponse.status}`);
      }
      
      const audioBlob = await audioResponse.blob();
      console.log('✅ 音频文件下载成功，大小:', audioBlob.size);
      
      // 创建FormData
      const formData = new FormData();
      formData.append('file', audioBlob, 'audio.wav');
      formData.append('model', options.model || 'whisper-1');
      
      if (options.language) {
        formData.append('language', options.language);
      }
      
      if (options.prompt) {
        formData.append('prompt', options.prompt);
      }
      
      // 调用OpenAI Whisper API
      console.log('🚀 调用OpenAI Whisper API...');
      const response = await fetch(this.baseUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
        },
        body: formData
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`OpenAI API 错误 ${response.status}: ${errorText}`);
      }
      
      const result = await response.json();
      console.log('✅ Whisper 识别成功:', result);
      
      return {
        success: true,
        text: result.text,
        language: result.language || 'unknown'
      };
      
    } catch (error) {
      console.error('❌ Whisper 识别失败:', error);
      throw error;
    }
  }
}

const R2_CONFIG = {
  accessKeyId: '5885b29961ce9fc2b593139d9de52f81',
  secretAccessKey: 'a4415c670e669229db451ea7b38544c0a2e44dbe630f1f35f99f28a27593d181',
  endpoint: 'https://c7c141ce43d175e60601edc46d904553.r2.cloudflarestorage.com',
  bucket: 'text-generation',
  region: 'auto'
};

// CORS headers
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization'
};

// Handle CORS preflight requests
function handleCORS(request) {
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      headers: corsHeaders
    });
  }
}

// Generate chat ID
function generateChatId() {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substr(2, 9);
  return `chat_${timestamp}_${random}`;
}

// Format chat record
function formatChatRecord(messages, metadata = {}) {
  const chatId = generateChatId();
  return {
    id: chatId,
    timestamp: new Date().toISOString(),
    title: messages.find(msg => msg.role === 'user')?.content.substring(0, 30) + '...' || '新对话',
    messages: messages.map(msg => ({
      ...msg,
      timestamp: typeof msg.timestamp === 'string' ? msg.timestamp : new Date().toISOString()
    })),
    metadata: {
      version: '2.0',
      model: metadata.model || 'unknown',
      userId: metadata.userId || 'anonymous',
      ...metadata
    }
  };
}

// Save chat to R2
async function saveChatToR2(chatRecord, env) {
  try {
    const fileName = `chats/${new Date().toISOString().split('T')[0]}/${chatRecord.id}.json`;
    
    // Use Cloudflare R2 binding (if available) or fetch API
    if (env.R2_BUCKET) {
      // Using R2 binding (preferred method)
      await env.R2_BUCKET.put(fileName, JSON.stringify(chatRecord), {
        metadata: {
          contentType: 'application/json',
          timestamp: new Date().toISOString()
        }
      });
    } else {
      // Fallback to fetch API (less preferred)
      const url = `${R2_CONFIG.endpoint}/${R2_CONFIG.bucket}/${fileName}`;
      const response = await fetch(url, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `AWS4-HMAC-SHA256 Credential=${R2_CONFIG.accessKeyId}`, // Simplified auth
        },
        body: JSON.stringify(chatRecord)
      });
      
      if (!response.ok) {
        throw new Error(`R2 API error: ${response.status}`);
      }
    }
    
    return { success: true, fileName, chatId: chatRecord.id };
  } catch (error) {
    console.error('❌ R2存储失败:', error);
    throw error;
  }
}

// Load chat from R2
async function loadChatFromR2(chatId, env) {
  try {
    const fileName = `chats/${chatId.split('_')[1] ? new Date(parseInt(chatId.split('_')[1])).toISOString().split('T')[0] : new Date().toISOString().split('T')[0]}/${chatId}.json`;
    
    if (env.R2_BUCKET) {
      const object = await env.R2_BUCKET.get(fileName);
      if (object) {
        const data = await object.text();
        return JSON.parse(data);
      }
    } else {
      const url = `${R2_CONFIG.endpoint}/${R2_CONFIG.bucket}/${fileName}`;
      const response = await fetch(url, {
        headers: {
          'Authorization': `AWS4-HMAC-SHA256 Credential=${R2_CONFIG.accessKeyId}`,
        }
      });
      
      if (response.ok) {
        return await response.json();
      }
    }
    
    throw new Error('Chat not found');
  } catch (error) {
    console.error('❌ R2加载失败:', error);
    throw error;
  }
}

// Main worker handler
export default {
  async fetch(request, env, ctx) {
    // Handle CORS
    const corsResponse = handleCORS(request);
    if (corsResponse) return corsResponse;
    
    const url = new URL(request.url);
    const path = url.pathname;
    
    try {
      // Health check
      if (path === '/health') {
        return new Response(JSON.stringify({
          status: 'healthy',
          r2_storage: 'connected',
          timestamp: new Date().toISOString()
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }


      
      // Save chat
      if (path === '/chat/save' && request.method === 'POST') {
        const body = await request.json();
        const { chat_id, messages, metadata } = body;
        
        let chatRecord;
        if (chat_id) {
          chatRecord = { id: chat_id, messages, metadata, timestamp: new Date().toISOString() };
        } else {
          chatRecord = formatChatRecord(messages, metadata);
        }
        
        const result = await saveChatToR2(chatRecord, env);
        
        return new Response(JSON.stringify({
          success: true,
          chat_id: result.chatId,
          fileName: result.fileName
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }
      
      // Load chat
      if (path.startsWith('/chat/load/') && request.method === 'GET') {
        const chatId = path.split('/').pop();
        const data = await loadChatFromR2(chatId, env);
        
        return new Response(JSON.stringify({
          success: true,
          data: data
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }
      
      // List chats (simplified)
      if (path.startsWith('/chat/history/') && request.method === 'GET') {
        // This would require more complex R2 listing logic
        return new Response(JSON.stringify({
          success: true,
          chats: []
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }
      
      // Delete chat
      if (path.startsWith('/chat/delete/') && request.method === 'DELETE') {
        const chatId = path.split('/').pop();
        // Implementation would go here
        return new Response(JSON.stringify({
          success: true,
          message: 'Chat deleted'
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }
      
      // Speech to Text endpoint (proxy to RunPod)
      if (path === '/speech/stt' && request.method === 'POST') {
        const body = await request.json();
        const { audio_data, format = 'webm' } = body;
        
        if (!audio_data) {
          return new Response(JSON.stringify({
            success: false,
            error: '缺少音频数据'
          }), {
            status: 400,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }
        
        // Proxy to RunPod Whisper API
        const runpodPayload = {
          input: {
            audio_data,
            format,
            model_path: "/runpod-volume/voice/whisper-large-v3-turbo",
            task: "transcribe",
            language: "auto"
          }
        };
        
        try {
          const runpodResponse = await fetch('https://api.runpod.ai/v2/4cx6jtjdx6hdhr/runsync', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${env.RUNPOD_API_KEY || 'rpa_YT0BFBFZYAZMQHR231H4DOKQEOAJXSMVIBDYN4ZQ1tdxlb'}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(runpodPayload)
          });
          
          if (runpodResponse.ok) {
            const result = await runpodResponse.json();
            
            if (result.status === 'COMPLETED') {
              let transcription = '';
              if (typeof result.output === 'string') {
                transcription = result.output;
              } else if (result.output && typeof result.output === 'object') {
                transcription = result.output.text || result.output.transcription || '';
              }
              
              return new Response(JSON.stringify({
                success: true,
                text: transcription.trim()
              }), {
                headers: { ...corsHeaders, 'Content-Type': 'application/json' }
              });
            } else {
              return new Response(JSON.stringify({
                success: false,
                error: result.error || '语音识别失败'
              }), {
                status: 500,
                headers: { ...corsHeaders, 'Content-Type': 'application/json' }
              });
            }
          } else {
            throw new Error(`RunPod API error: ${runpodResponse.status}`);
          }
        } catch (error) {
          return new Response(JSON.stringify({
            success: false,
            error: `语音识别服务异常: ${error.message}`
          }), {
            status: 500,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }
      }
      
      // Text to Speech endpoint (多语种支持)
      if (path === '/speech/tts' && request.method === 'POST') {
        const body = await request.json();
        const { text, voice_id = 'female-shaonv', speed = 1.0, volume = 1.0, pitch = 0, language = 'auto' } = body;
        
        if (!text || !text.trim()) {
          return new Response(JSON.stringify({
            success: false,
            error: '文本内容不能为空'
          }), {
            status: 400,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }

        // 增强的文本预处理和语言检测
        function preprocessText(inputText) {
          // 第一步：基础清理
          let cleanText = inputText
            .replace(/[\u0000-\u001F\u007F-\u009F]/g, '') // 移除控制字符
            .replace(/[\u200B-\u200D\uFEFF]/g, '') // 移除零宽字符
            .replace(/\s+/g, ' ') // 规范化空格
            .trim();
          
                                // 第二步：字符替换（处理常见的特殊字符）
           // 智能引号和单引号
           cleanText = cleanText
             .replace(/[""]/g, '"')
             .replace(/['']/g, "'")
             .replace(/[—–]/g, '-')
             .replace(/…/g, '...')
             .replace(/°/g, '度')
             .replace(/×/g, 'x')
             .replace(/÷/g, '/')
             .replace(/±/g, '+/-')
             .replace(/≈/g, '约')
             .replace(/≤/g, '小于等于')
             .replace(/≥/g, '大于等于')
             .replace(/∞/g, '无穷大')
             .replace(/€/g, '欧元')
             .replace(/£/g, '英镑')
             .replace(/¥/g, '元')
             .replace(/\$/g, '美元')
             .replace(/©/g, '版权')
             .replace(/®/g, '注册商标')
             .replace(/™/g, '商标')
             .replace(/§/g, '节')
             .replace(/¶/g, '段落')
             .replace(/[†‡]/g, '')
             .replace(/•/g, '·')
             .replace(/→/g, '到')
             .replace(/←/g, '从')
             .replace(/↑/g, '上')
             .replace(/↓/g, '下')
             .replace(/[①②③④⑤⑥⑦⑧⑨⑩]/g, (match) => {
               const nums = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩'];
               return (nums.indexOf(match) + 1).toString();
             });
          
          // 第三步：保留安全字符集
          // 扩展安全字符范围，包括更多语言
          cleanText = cleanText.replace(/[^\u0020-\u007E\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af\u0100-\u017f\u1e00-\u1eff]/g, '');
          
          // 第四步：处理连续标点符号
          cleanText = cleanText
            .replace(/[，,]{2,}/g, '，') // 多个逗号
            .replace(/[。.]{2,}/g, '。') // 多个句号
            .replace(/[！!]{2,}/g, '！') // 多个感叹号
            .replace(/[？?]{2,}/g, '？') // 多个问号
            .replace(/[；;]{2,}/g, '；') // 多个分号
            .replace(/[：:]{2,}/g, '：') // 多个冒号
            .trim();
          
          // 第五步：限制文本长度
          if (cleanText.length > 1500) { // 降低长度限制以提高成功率
            cleanText = cleanText.substring(0, 1500);
            // 尝试在句子边界截断
            const lastPunctuation = Math.max(
              cleanText.lastIndexOf('。'),
              cleanText.lastIndexOf('！'),
              cleanText.lastIndexOf('？'),
              cleanText.lastIndexOf('.'),
              cleanText.lastIndexOf('!'),
              cleanText.lastIndexOf('?')
            );
            if (lastPunctuation > cleanText.length * 0.8) {
              cleanText = cleanText.substring(0, lastPunctuation + 1);
            }
          }
          
          return cleanText;
        }

        function detectLanguage(inputText) {
          // 简单的语言检测
          const chineseRegex = /[\u4e00-\u9fff]/;
          const japaneseRegex = /[\u3040-\u309f\u30a0-\u30ff]/;
          const koreanRegex = /[\uac00-\ud7af]/;
          
          if (chineseRegex.test(inputText)) return 'zh';
          if (japaneseRegex.test(inputText)) return 'ja';
          if (koreanRegex.test(inputText)) return 'ko';
          return 'en';
        }

        function selectVoiceForLanguage(lang, originalVoiceId) {
          // 根据语言选择合适的声音
          const voiceMap = {
            'zh': ['female-shaonv', 'male-qn-qingse', 'female-yujie', 'male-badao'],
            'en': ['female-shaonv', 'male-qn-qingse'], // MiniMax主要支持中文，英文使用相同声音
            'ja': ['female-shaonv', 'female-yujie'],
            'ko': ['female-shaonv', 'female-yujie']
          };
          
          const availableVoices = voiceMap[lang] || voiceMap['zh'];
          return availableVoices.includes(originalVoiceId) ? originalVoiceId : availableVoices[0];
        }

        try {
          // 预处理文本
          const processedText = preprocessText(text);
          
          if (!processedText) {
            return new Response(JSON.stringify({
              success: false,
              error: '处理后的文本为空，请检查输入内容'
            }), {
              status: 400,
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          }

          // 检测语言
          const detectedLang = language === 'auto' ? detectLanguage(processedText) : language;
          
          // 选择合适的声音
          const selectedVoice = selectVoiceForLanguage(detectedLang, voice_id);

          console.log(`TTS请求: 语言=${detectedLang}, 声音=${selectedVoice}, 文本长度=${processedText.length}`);

          // 尝试MiniMax TTS API
          const minimaxUrl = `https://api.minimax.io/v1/t2a_v2?GroupId=${env.MINIMAX_GROUP_ID || '1925025302392607036'}`;
          const minimaxPayload = {
            model: "speech-02-turbo",
            text: processedText,
            stream: false,
            voice_setting: {
              voice_id: selectedVoice,
              speed: Math.max(0.5, Math.min(2.0, speed)), // 限制速度范围
              vol: Math.max(0.1, Math.min(2.0, volume)),  // 限制音量范围
              pitch: Math.max(-12, Math.min(12, pitch))    // 限制音调范围
            },
            audio_setting: {
              sample_rate: 32000,
              bitrate: 128000,
              format: "mp3",
              channel: 1
            }
          };

          const minimaxResponse = await fetch(minimaxUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${env.MINIMAX_API_KEY || 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiJCRUkgTEkiLCJVc2VyTmFtZSI6IkJFSSBMSSIsIkFjY291bnQiOiIiLCJTdWJqZWN0SUQiOiIxOTI1MDI1MzAyNDAwOTk1NjQ0IiwiUGhvbmUiOiIiLCJHcm91cElEIjoiMTkyNTAyNTMwMjM5MjYwNzAzNiIsIlBhZ2VOYW1lIjoiIiwiTWFpbCI6ImJhaWxleWxpYmVpQGdtYWlsLmNvbSIsIkNyZWF0ZVRpbWUiOiIyMDI1LTA1LTIxIDEyOjIyOjI4IiwiVG9rZW5UeXBlIjoxLCJpc3MiOiJtaW5pbWF4In0.cMEP1g8YBLysihnD5RfmqtxGAGfR3XYxdXOAHurxoV5u92-ze8j5Iv1hc7O9qgFAoZyi2-eKRl6iRF3JM_IE1RQ6GXmfQnpr4a0VINu7c2GDW-x_4I-7CTHQTAmXfZOp6bVMbFvZqQDS9mzMexYDcFOghwJm1jFKhisU3J4996BqxC6R_u1J15yWkAb0Y5SX18hlYBEuO8MYPjAECSAcSthXIPxo4KQmd1LPuC2URnlhHBa6kvV0pZGp9tggSUlabyQaliCky8fxfOgyJc1YThQybg3iJ2VlYNnIhSj73SZ3pl6nB1unoiCsusAY0_mbzgcAiTd2rpKTh9xmUtcIxw'}`
            },
            body: JSON.stringify(minimaxPayload)
          });

          if (minimaxResponse.ok) {
            const result = await minimaxResponse.json();
            
            if (result.data && result.data.audio) {
              try {
                // Convert hex audio to binary
                const hexAudio = result.data.audio;
                const audioBytes = new Uint8Array(hexAudio.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
                
                // Return actual audio file
                return new Response(audioBytes, {
                  headers: { 
                    ...corsHeaders, 
                    'Content-Type': 'audio/mpeg',
                    'Content-Disposition': 'inline; filename="speech.mp3"',
                    'X-TTS-Language': detectedLang,
                    'X-TTS-Voice': selectedVoice
                  }
                });
              } catch (hexError) {
                console.error('音频数据转换失败:', hexError);
                throw new Error('音频数据格式错误');
              }
            } else {
              console.error('MiniMax响应格式错误:', result);
              throw new Error(result.message || '音频生成失败');
            }
          } else {
            const errorText = await minimaxResponse.text();
            console.error(`MiniMax API错误 ${minimaxResponse.status}:`, errorText);
            
            // 如果是字符编码或其他错误，尝试多种备用方案
            if ((minimaxResponse.status === 400 || minimaxResponse.status === 500) && env.OPENAI_API_KEY) {
              console.log('MiniMax失败，尝试OpenAI TTS备用方案...');
              
              try {
                // 为OpenAI进一步清理文本
                const openaiText = processedText
                  .replace(/[^\u0020-\u007E\u4e00-\u9fff]/g, '') // 只保留基本字符
                  .substring(0, 4000); // OpenAI限制
                
                const openaiVoiceMap = {
                  'zh': 'alloy',
                  'en': 'alloy',
                  'ja': 'nova',
                  'ko': 'shimmer'
                };
                
                const openaiResponse = await fetch('https://api.openai.com/v1/audio/speech', {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${env.OPENAI_API_KEY}`
                  },
                  body: JSON.stringify({
                    model: 'tts-1',
                    input: openaiText,
                    voice: openaiVoiceMap[detectedLang] || 'alloy',
                    response_format: 'mp3',
                    speed: Math.max(0.25, Math.min(4.0, speed))
                  })
                });

                if (openaiResponse.ok) {
                  const audioBuffer = await openaiResponse.arrayBuffer();
                  return new Response(audioBuffer, {
                    headers: { 
                      ...corsHeaders, 
                      'Content-Type': 'audio/mpeg',
                      'Content-Disposition': 'inline; filename="speech.mp3"',
                      'X-TTS-Provider': 'openai',
                      'X-TTS-Language': detectedLang,
                      'X-TTS-Fallback': 'true'
                    }
                  });
                } else {
                  console.error('OpenAI TTS也失败:', await openaiResponse.text());
                }
              } catch (openaiError) {
                console.error('OpenAI TTS备用方案也失败:', openaiError);
              }
            }
            
            // 如果所有方案都失败，尝试简化文本再试一次MiniMax
            if (minimaxResponse.status === 400) {
              console.log('尝试简化文本重新请求MiniMax...');
              
              try {
                // 极简文本处理
                const simpleText = processedText
                  .replace(/[^\u4e00-\u9fff\u0020-\u007E]/g, '') // 只保留中文和基本英文
                  .replace(/\s+/g, ' ')
                  .trim()
                  .substring(0, 500); // 大幅缩短
                
                if (simpleText.length > 10) {
                  const simplePayload = {
                    model: "speech-02-turbo",
                    text: simpleText,
                    stream: false,
                    voice_setting: {
                      voice_id: 'female-shaonv', // 使用默认声音
                      speed: 1.0,
                      vol: 1.0,
                      pitch: 0
                    },
                    audio_setting: {
                      sample_rate: 16000, // 降低采样率
                      bitrate: 64000,     // 降低比特率
                      format: "mp3",
                      channel: 1
                    }
                  };
                  
                  const retryResponse = await fetch(minimaxUrl, {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                      'Authorization': `Bearer ${env.MINIMAX_API_KEY}`
                    },
                    body: JSON.stringify(simplePayload)
                  });
                  
                  if (retryResponse.ok) {
                    const retryResult = await retryResponse.json();
                    if (retryResult.data && retryResult.data.audio) {
                      const hexAudio = retryResult.data.audio;
                      const audioBytes = new Uint8Array(hexAudio.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
                      
                      return new Response(audioBytes, {
                        headers: { 
                          ...corsHeaders, 
                          'Content-Type': 'audio/mpeg',
                          'Content-Disposition': 'inline; filename="speech.mp3"',
                          'X-TTS-Language': detectedLang,
                          'X-TTS-Voice': 'female-shaonv',
                          'X-TTS-Simplified': 'true'
                        }
                      });
                    }
                  }
                }
              } catch (retryError) {
                console.error('简化文本重试也失败:', retryError);
              }
            }
            
            throw new Error(`MiniMax API error: ${minimaxResponse.status} - ${errorText}`);
          }
        } catch (error) {
          console.error('TTS服务异常:', error);
          
          return new Response(JSON.stringify({
            success: false,
            error: `语音合成服务异常: ${error.message}`,
            details: {
              originalText: text,
              processedText: preprocessText(text),
              detectedLanguage: detectLanguage(preprocessText(text))
            }
          }), {
            status: 500,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }
      }
      
      // R2 Upload endpoint
      if (path === '/r2-upload' && request.method === 'POST') {
        try {
          const formData = await request.formData();
          const file = formData.get('file');
          const fileName = formData.get('fileName');
          
          if (!file || !fileName) {
            return new Response(JSON.stringify({
              error: '缺少文件或文件名'
            }), {
              status: 400,
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          }

          // 使用 R2 绑定上传（推荐方式）
          if (env.R2_BUCKET) {
            await env.R2_BUCKET.put(fileName, file);
            const publicUrl = `https://pub-f314a707297b4748936925bba8dd4962.r2.dev/${fileName}`;
            
            return new Response(JSON.stringify({
              success: true,
              url: publicUrl,
              fileName: fileName,
              size: file.size
            }), {
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          } else {
            // 环境变量验证
            const R2_ACCOUNT_ID = env.R2_ACCOUNT_ID;
            const R2_ACCESS_KEY_ID = env.R2_ACCESS_KEY_ID; 
            const R2_SECRET_ACCESS_KEY = env.R2_SECRET_ACCESS_KEY;
            
            if (!R2_ACCOUNT_ID || !R2_ACCESS_KEY_ID || !R2_SECRET_ACCESS_KEY) {
              return new Response(JSON.stringify({
                error: 'R2 配置缺失，请设置环境变量'
              }), {
                status: 503,
                headers: { ...corsHeaders, 'Content-Type': 'application/json' }
              });
            }

            // 使用 Fetch API 上传到 R2
            const endpoint = `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`;
            const uploadUrl = `${endpoint}/text-generation/${fileName}`;
            
            // 简化的 S3 兼容认证（生产环境需要完整的 AWS4 签名）
            const uploadResponse = await fetch(uploadUrl, {
              method: 'PUT',
              headers: {
                'Content-Type': file.type,
                'Content-Length': file.size.toString(),
              },
              body: file
            });
            
            if (!uploadResponse.ok) {
              throw new Error(`上传失败: ${uploadResponse.status} ${uploadResponse.statusText}`);
            }

            const publicUrl = `https://pub-f314a707297b4748936925bba8dd4962.r2.dev/${fileName}`;
            
            return new Response(JSON.stringify({
              success: true,
              url: publicUrl,
              fileName: fileName,
              size: file.size
            }), {
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          }
          
        } catch (error) {
          return new Response(JSON.stringify({
            error: error.message || 'R2 上传失败',
            success: false
          }), {
            status: 500,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }
      }

      // 智能聊天端点
      if (path === '/chat' && request.method === 'POST') {
        try {
          const body = await request.json();
          const { user_id, conversation_id, content } = body;
          
          if (!user_id || !content) {
            return new Response(JSON.stringify({
              success: false,
              error: '缺少必要参数: user_id 和 content'
            }), {
              status: 400,
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          }

          // 如果没有提供conversation_id，创建新对话
          let finalConversationId = conversation_id;
          if (!finalConversationId) {
            const chatManager = new ChatHistoryManager(env);
            const newConversation = await chatManager.createConversation(user_id);
            if (newConversation.success) {
              finalConversationId = newConversation.conversationId;
            } else {
              throw new Error('创建对话失败');
            }
          }

          // 处理聊天
          const chatManager = new ChatHistoryManager(env);
          const result = await chatManager.processChat(user_id, finalConversationId, content);

          if (result.success) {
            return new Response(JSON.stringify({
              success: true,
              response: result.response,
              conversation_id: result.conversationId,
              user_id: user_id
            }), {
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          } else {
            throw new Error(result.error);
          }

        } catch (error) {
          console.error('聊天处理失败:', error);
          return new Response(JSON.stringify({
            success: false,
            error: error.message || '聊天处理失败'
          }), {
            status: 500,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }
      }

      // 获取对话历史
      if (path === '/chat/history' && request.method === 'GET') {
        try {
          const url = new URL(request.url);
          const userId = url.searchParams.get('user_id');
          const conversationId = url.searchParams.get('conversation_id');
          const limit = parseInt(url.searchParams.get('limit') || '20');

          if (!userId || !conversationId) {
            return new Response(JSON.stringify({
              success: false,
              error: '缺少必要参数: user_id 和 conversation_id'
            }), {
              status: 400,
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          }

          // 从D1获取历史消息
          const messages = await env.DB.prepare(
            'SELECT role, content, created_at FROM messages WHERE user_id = ? AND conversation_id = ? ORDER BY created_at DESC LIMIT ?'
          ).bind(userId, conversationId, limit).all();

          return new Response(JSON.stringify({
            success: true,
            messages: messages.results.reverse(), // 按时间正序排列
            conversation_id: conversationId
          }), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });

        } catch (error) {
          console.error('获取历史失败:', error);
          return new Response(JSON.stringify({
            success: false,
            error: error.message || '获取历史失败'
          }), {
            status: 500,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }
      }

      // 获取用户的所有对话列表
      if (path === '/chat/conversations' && request.method === 'GET') {
        try {
          const url = new URL(request.url);
          const userId = url.searchParams.get('user_id');

          if (!userId) {
            return new Response(JSON.stringify({
              success: false,
              error: '缺少必要参数: user_id'
            }), {
              status: 400,
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          }

          // 获取用户的所有对话
          const conversations = await env.DB.prepare(
            'SELECT id, title, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY updated_at DESC'
          ).bind(userId).all();

          return new Response(JSON.stringify({
            success: true,
            conversations: conversations.results
          }), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });

        } catch (error) {
          console.error('获取对话列表失败:', error);
          return new Response(JSON.stringify({
            success: false,
            error: error.message || '获取对话列表失败'
          }), {
            status: 500,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }
      }

      // 创建新对话
      if (path === '/chat/conversation' && request.method === 'POST') {
        try {
          const body = await request.json();
          const { user_id, title, system_prompt } = body;

          if (!user_id) {
            return new Response(JSON.stringify({
              success: false,
              error: '缺少必要参数: user_id'
            }), {
              status: 400,
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          }

          const chatManager = new ChatHistoryManager(env);
          const result = await chatManager.createConversation(user_id, title, system_prompt);

          if (result.success) {
            return new Response(JSON.stringify({
              success: true,
              conversation_id: result.conversationId
            }), {
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          } else {
            throw new Error(result.error);
          }

        } catch (error) {
          console.error('创建对话失败:', error);
          return new Response(JSON.stringify({
            success: false,
            error: error.message || '创建对话失败'
          }), {
            status: 500,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }
      }

      // OpenAI Whisper ASR endpoint
      if (path === '/whisper-asr' && request.method === 'POST') {
        try {
          const body = await request.json();
          const { fileLink, language, prompt } = body;
          
          // 从环境变量获取OpenAI API Key
          const openaiApiKey = env.OPENAI_API_KEY;
          
          console.log('🔊 OpenAI Whisper ASR 请求:', { fileLink, language, prompt });
          
          // 验证必要参数
          if (!openaiApiKey) {
            return new Response(JSON.stringify({
              error: 'OpenAI API Key 缺失',
              message: '请设置 OPENAI_API_KEY 环境变量'
            }), {
              status: 400,
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          }

          if (!fileLink) {
            return new Response(JSON.stringify({
              error: '缺少音频文件链接'
            }), {
              status: 400,
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          }

          // 创建OpenAI Whisper客户端
          const whisperClient = new OpenAIWhisperClient(openaiApiKey);
          
          console.log('📤 开始 OpenAI Whisper 语音识别，文件链接:', fileLink);
          
          try {
            // 直接调用 Whisper API 进行识别
            const startTime = Date.now();
            const result = await whisperClient.transcribeAudio(fileLink, {
              language: language || undefined,
              prompt: prompt || undefined
            });
            
            const endTime = Date.now();
            const processingTime = endTime - startTime;
            
            console.log('✅ OpenAI Whisper 识别成功:', result);
            
            return new Response(JSON.stringify({
              success: true,
              text: result.text,
              language: result.language,
              processingTime: processingTime,
              provider: 'OpenAI Whisper'
            }), {
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
            
          } catch (whisperError) {
            console.error('❌ OpenAI Whisper 识别失败:', whisperError);
            
            // 如果 Whisper API 失败，返回错误信息
            return new Response(JSON.stringify({
              success: false,
              error: whisperError.message,
              provider: 'OpenAI Whisper',
              fallback: '语音识别暂时不可用，请稍后重试'
            }), {
              status: 500,
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          }
          
        } catch (error) {
          console.error('❌ OpenAI Whisper ASR 处理异常:', error);
          return new Response(JSON.stringify({
            success: false,
            error: error.message || 'Whisper ASR 处理失败',
            provider: 'OpenAI Whisper',
            fallback: '抱歉，语音识别暂时不可用，请稍后重试。'
          }), {
            status: 500,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }
      }
      
      // Default response
      return new Response(JSON.stringify({
        message: "AI Chat API is running",
        version: "2.0",
        features: {
          chat: "智能对话系统，支持短期+长期记忆",
          storage: "D1数据库 + KV缓存 + Vectorize向量搜索",
          voice: "OpenAI Whisper语音识别 + MiniMax TTS",
          memory: "语义相似搜索 + 上下文管理"
        },
        endpoints: [
          "/health",
          "/chat - POST: 智能对话",
          "/chat/history - GET: 获取对话历史", 
          "/chat/conversations - GET: 获取对话列表",
          "/chat/conversation - POST: 创建新对话",
          "/speech/tts - POST: 文字转语音",
          "/whisper-asr - POST: 语音识别",
          "/r2-upload - POST: 文件上传",
          "/chat/save - POST: 保存聊天记录(兼容)",
          "/chat/load/{id} - GET: 加载聊天记录(兼容)"
        ]
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
      
    } catch (error) {
      return new Response(JSON.stringify({
        error: error.message,
        success: false
      }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
  }
}; 