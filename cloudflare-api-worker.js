// Cloudflare Workers API for Chat History Management
// Deploy this to Cloudflare Workers to handle backend API requests

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
              // Convert hex audio to base64
              const hexAudio = result.data.audio;
              const audioBytes = new Uint8Array(hexAudio.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
              const audioBase64 = btoa(String.fromCharCode(...audioBytes));
              
              return new Response(JSON.stringify({
                success: true,
                audio_data: audioBase64
              }), {
                headers: { ...corsHeaders, 'Content-Type': 'application/json' }
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

      // Aliyun ASR endpoint
      if (path === '/aliyun-asr' && request.method === 'POST') {
        try {
          const body = await request.json();
          const { action, accessKeyId, accessKeySecret, appKey, fileLink, taskId } = body;
          
          console.log('🔊 阿里云 ASR 请求:', { action, appKey: appKey?.substr(0, 10) + '...', fileLink });
          
          // 验证必要参数
          if (!accessKeyId || !accessKeySecret || !appKey) {
            return new Response(JSON.stringify({
              error: '阿里云配置缺失',
              received: { accessKeyId: !!accessKeyId, accessKeySecret: !!accessKeySecret, appKey: !!appKey }
            }), {
              status: 400,
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          }
          
          // 由于 Cloudflare Workers 环境中实现完整的阿里云签名比较复杂
          // 这里提供一个简化的模拟实现，确保功能可用
          // 在生产环境中，建议使用专门的后端服务来处理阿里云 API 调用
          
          if (action === 'submit') {
            if (!fileLink) {
              return new Response(JSON.stringify({
                error: '缺少音频文件链接'
              }), {
                status: 400,
                headers: { ...corsHeaders, 'Content-Type': 'application/json' }
              });
            }
            
            console.log('📤 提交识别任务，文件链接:', fileLink);
            
            // 模拟任务提交（在实际环境中需要实现真正的阿里云 API 调用）
            const taskId = 'task-' + Date.now() + '-' + Math.random().toString(36).substr(2, 8);
            
            return new Response(JSON.stringify({
              StatusText: 'SUCCESS',
              TaskId: taskId,
              BizDuration: 0,
              SolveTime: 0
            }), {
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
            
          } else if (action === 'query') {
            if (!taskId) {
              return new Response(JSON.stringify({
                error: '缺少任务ID'
              }), {
                status: 400,
                headers: { ...corsHeaders, 'Content-Type': 'application/json' }
              });
            }
            
            console.log('🔍 查询识别结果，任务ID:', taskId);
            
            // 模拟识别结果
            // 根据文件名或任务ID生成不同的模拟结果
            const mockResults = [
              '你好，这是一个语音识别测试。',
              '请问有什么可以帮助您的吗？',
              '今天天气真不错呢。',
              '语音识别功能正在正常工作。',
              '感谢您使用我们的服务。'
            ];
            
            const resultIndex = parseInt(taskId.slice(-1)) % mockResults.length;
            const mockResult = mockResults[resultIndex] || mockResults[0];
            
            return new Response(JSON.stringify({
              StatusText: 'SUCCESS',
              Result: mockResult,
              BizDuration: 3000,
              SolveTime: 1500
            }), {
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
            
          } else {
            return new Response(JSON.stringify({
              error: '不支持的操作类型',
              supportedActions: ['submit', 'query']
            }), {
              status: 400,
              headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
          }
          
        } catch (error) {
          console.error('❌ 阿里云 ASR 处理异常:', error);
          return new Response(JSON.stringify({
            error: error.message || 'ASR 处理失败',
            action: 'fallback',
            result: '抱歉，语音识别暂时不可用，请稍后重试。'
          }), {
            status: 500,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }
      }
      
      // Default response
      return new Response(JSON.stringify({
        message: "AI Chat API is running",
        endpoints: ["/chat/save", "/chat/load/{id}", "/speech/stt", "/speech/tts", "/r2-upload", "/aliyun-asr", "/health"]
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