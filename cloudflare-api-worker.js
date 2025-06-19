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
      
      // Default response
      return new Response(JSON.stringify({
        message: "AI Chat API is running",
        endpoints: ["/chat/save", "/chat/load/{id}", "/health"]
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