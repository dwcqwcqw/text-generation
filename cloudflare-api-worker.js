// Cloudflare Workers API for Chat History Management
// Deploy this to Cloudflare Workers to handle backend API requests

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
      
      // Text to Speech endpoint (proxy to MiniMax)
      if (path === '/speech/tts' && request.method === 'POST') {
        const body = await request.json();
        const { text, voice_id = 'female-shaonv', speed = 1.0, volume = 1.0, pitch = 0 } = body;
        
        if (!text || !text.trim()) {
          return new Response(JSON.stringify({
            success: false,
            error: '文本内容不能为空'
          }), {
            status: 400,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }
        
        // MiniMax TTS API
        const minimaxUrl = `https://api.minimax.io/v1/t2a_v2?GroupId=${env.MINIMAX_GROUP_ID || '1925025302392607036'}`;
        const minimaxPayload = {
          model: "speech-02-turbo",
          text: text,
          stream: false,
          voice_setting: {
            voice_id,
            speed,
            vol: volume,
            pitch
          },
          audio_setting: {
            sample_rate: 32000,
            bitrate: 128000,
            format: "mp3",
            channel: 1
          }
        };
        
        try {
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
              // Convert hex audio to binary
              const hexAudio = result.data.audio;
              const audioBytes = new Uint8Array(hexAudio.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
              
              // Return actual audio file
              return new Response(audioBytes, {
                headers: { 
                  ...corsHeaders, 
                  'Content-Type': 'audio/mpeg',
                  'Content-Disposition': 'inline; filename="speech.mp3"'
                }
              });
            } else {
              return new Response(JSON.stringify({
                success: false,
                error: '音频生成失败'
              }), {
                status: 500,
                headers: { ...corsHeaders, 'Content-Type': 'application/json' }
              });
            }
          } else {
            throw new Error(`MiniMax API error: ${minimaxResponse.status}`);
          }
        } catch (error) {
          return new Response(JSON.stringify({
            success: false,
            error: `语音合成服务异常: ${error.message}`
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
        endpoints: ["/chat/save", "/chat/load/{id}", "/speech/stt", "/speech/tts", "/r2-upload", "/whisper-asr", "/health"]
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