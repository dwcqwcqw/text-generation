/**
 * Cloudflare R2存储模块
 * 用于保存和管理聊天记录
 */

// Cloudflare R2配置
const R2_CONFIG = {
  accessKeyId: '5885b29961ce9fc2b593139d9de52f81',
  secretAccessKey: 'a4415c670e669229db451ea7b38544c0a2e44dbe630f1f35f99f28a27593d181',
  endpoint: 'https://c7c141ce43d175e60601edc46d904553.r2.cloudflarestorage.com',
  publicUrl: 'https://pub-f314a707297b4748936925bba8dd4962.r2.dev',
  bucket: 'text-generation',
  region: 'auto'
};

// API配置 (备用)
const API_CONFIG = {
  baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  endpoints: {
    saveChat: '/chat/save',
    loadChat: '/chat/load',
    listChats: '/chat/history',
    healthCheck: '/health'
  }
};

/**
 * 生成聊天记录的唯一ID
 */
function generateChatId() {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substr(2, 9);
  return `chat_${timestamp}_${random}`;
}

/**
 * 格式化聊天记录
 */
function formatChatRecord(messages, metadata = {}) {
  const chatId = generateChatId();
  return {
    id: chatId,
    timestamp: new Date().toISOString(),
    title: messages.find(msg => msg.role === 'user')?.content.substring(0, 30) + '...' || '新对话',
    messages: messages.map(msg => ({
      ...msg,
      timestamp: msg.timestamp instanceof Date ? msg.timestamp.toISOString() : msg.timestamp || new Date().toISOString()
    })),
    metadata: {
      version: '2.0',
      model: metadata.model || 'unknown',
      userId: metadata.userId || 'anonymous',
      ...metadata
    }
  };
}

/**
 * 直接保存到Cloudflare R2
 */
async function saveToR2Direct(chatRecord) {
  try {
    // 使用现代的fetch API直接上传到R2
    const fileName = `chats/${new Date().toISOString().split('T')[0]}/${chatRecord.id}.json`;
    
    // 创建AWS-style签名 (简化版本)
    const url = `${R2_CONFIG.endpoint}/${R2_CONFIG.bucket}/${fileName}`;
    
    console.log('💾 直接保存到R2:', fileName);
    
    // 使用预签名URL或直接API调用
    // 注意：在生产环境中应该通过后端API来处理，避免暴露密钥
    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `AWS4-HMAC-SHA256 Credential=${R2_CONFIG.accessKeyId}/${new Date().toISOString().split('T')[0]}/${R2_CONFIG.region}/s3/aws4_request`,
        // 实际的AWS签名会更复杂，这里简化处理
      },
      body: JSON.stringify(chatRecord)
    });

    if (response.ok) {
      console.log('✅ R2存储成功:', fileName);
      return { success: true, fileName };
    } else {
      throw new Error(`R2 upload failed: ${response.status}`);
    }
  } catch (error) {
    console.error('❌ R2存储失败:', error);
    throw error;
  }
}

/**
 * 保存聊天记录到R2 (混合方案：后端API + 本地存储)
 */
export async function saveChatToR2(messages, metadata = {}) {
  const chatRecord = formatChatRecord(messages, metadata);
  
  // 优先尝试后端API
  try {
    console.log('💾 尝试通过后端API保存聊天记录到R2:', chatRecord.id);
    
    const response = await fetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.saveChat}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        chat_id: chatRecord.id,
        messages: chatRecord.messages,
        metadata: chatRecord.metadata
      })
    });
    
    if (response.ok) {
      const result = await response.json();
      console.log('✅ 聊天记录保存成功 (后端API):', chatRecord.id);
      return {
        success: true,
        chatId: chatRecord.id,
        result: result,
        storage: 'r2'
      };
    } else {
      throw new Error(`后端API HTTP ${response.status}`);
    }
    
  } catch (error) {
    console.log('⚠️ 后端API不可用，将使用本地存储备份:', error.message);
    
    // 后端API不可用，使用本地存储
    try {
      const localKey = `chat_backup_${chatRecord.id}`;
      localStorage.setItem(localKey, JSON.stringify(chatRecord));
      console.log('📱 已保存到本地存储作为备份:', localKey);
      
      // 同时保存到全局列表以便后续查询
      const chatList = JSON.parse(localStorage.getItem('chat_list') || '[]');
      const chatSummary = {
        id: chatRecord.id,
        title: chatRecord.title,
        timestamp: chatRecord.timestamp,
        messageCount: chatRecord.messages.length
      };
      
      // 避免重复添加
      if (!chatList.find(chat => chat.id === chatRecord.id)) {
        chatList.unshift(chatSummary); // 添加到开头
        localStorage.setItem('chat_list', JSON.stringify(chatList));
      }
      
      return {
        success: true,
        chatId: chatRecord.id,
        storage: 'local'
      };
    } catch (localError) {
      console.error('❌ 本地备份也失败:', localError);
      return {
        success: false,
        error: error.message
      };
    }
  }
}

/**
 * 从R2加载聊天记录 (混合方案：后端API + 本地存储)
 */
export async function loadChatFromR2(chatId) {
  // 优先尝试后端API
  try {
    console.log('📥 尝试通过后端API从R2加载聊天记录:', chatId);
    
    const response = await fetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.loadChat}/${chatId}`);
    
    if (response.ok) {
      const result = await response.json();
      console.log('✅ 聊天记录加载成功 (后端API):', chatId);
      return {
        success: true,
        data: result.data,
        storage: 'r2'
      };
    } else if (response.status === 404) {
      console.log('⚠️ 后端API中未找到记录，尝试本地存储');
      throw new Error('Not found in API');
    } else {
      throw new Error(`后端API HTTP ${response.status}`);
    }
    
  } catch (error) {
    console.log('⚠️ 后端API不可用，尝试从本地存储加载:', error.message);
    
    // 尝试从本地存储加载
    try {
      const localKey = `chat_backup_${chatId}`;
      const localData = localStorage.getItem(localKey);
      if (localData) {
        console.log('📱 从本地存储加载成功:', localKey);
        return {
          success: true,
          data: JSON.parse(localData),
          storage: 'local'
        };
      } else {
        return {
          success: false,
          error: '聊天记录不存在（本地存储中也未找到）'
        };
      }
    } catch (localError) {
      console.error('❌ 本地存储加载失败:', localError);
      return {
        success: false,
        error: `加载失败: ${localError.message}`
      };
    }
  }
}

/**
 * 列出用户的聊天记录 (混合方案：后端API + 本地存储)
 */
export async function listUserChats(userId = 'anonymous', date = null) {
  // 优先尝试后端API
  try {
    const dateParam = date || new Date().toISOString().split('T')[0];
    const url = `${API_CONFIG.baseUrl}/chat/history/${dateParam}`;
    
    console.log('📋 尝试通过后端API获取聊天历史:', url);
    
    const response = await fetch(url);
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ 聊天历史获取成功 (后端API):', data.chats?.length || 0);
      return {
        success: true,
        chats: data.chats || [],
        storage: 'r2'
      };
    } else if (response.status === 404) {
      console.log('⚠️ 后端API中无历史记录，尝试本地存储');
      throw new Error('No history in API');
    } else {
      throw new Error(`后端API HTTP ${response.status}`);
    }
    
  } catch (error) {
    console.log('⚠️ 后端API不可用，从本地存储获取聊天历史:', error.message);
    
    // 从本地存储获取聊天历史
    try {
      // 优先从chat_list获取（保存时已整理的列表）
      const chatList = JSON.parse(localStorage.getItem('chat_list') || '[]');
      if (chatList.length > 0) {
        console.log('📱 从本地存储聊天列表获取:', chatList.length);
        return {
          success: true,
          chats: chatList.map(chat => ({
            ...chat,
            message_count: chat.messageCount || 0,
            storage: 'local'
          })),
          storage: 'local'
        };
      }
      
      // 如果没有整理的列表，扫描所有备份
      const backupChats = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('chat_backup_')) {
          try {
            const data = JSON.parse(localStorage.getItem(key));
            backupChats.push({
              id: data.id,
              title: data.title || (data.messages.find(msg => msg.role === 'user')?.content.substring(0, 30) + '...' || '本地对话'),
              timestamp: data.timestamp,
              message_count: data.messages?.length || 0,
              storage: 'local'
            });
          } catch (e) {
            console.warn('跳过损坏的备份:', key);
          }
        }
      }
      
      const sortedChats = backupChats.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
      console.log('📱 从本地存储备份获取:', sortedChats.length);
      
      return {
        success: true,
        chats: sortedChats,
        storage: 'local'
      };
    } catch (localError) {
      console.error('❌ 本地存储查询失败:', localError);
      return {
        success: true,
        chats: [],
        storage: 'none'
      };
    }
  }
}

/**
 * 检查后端API健康状态
 */
export async function checkAPIHealth() {
  try {
    const response = await fetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.healthCheck}`);
    return response.ok;
  } catch (error) {
    console.log('⚠️ 后端API不可用，将使用本地存储备份');
    return false;
  }
}

/**
 * 自动保存聊天记录（智能选择存储方式）
 */
export async function autoSaveChatHistory(messages, metadata = {}) {
  // 只有当消息数量大于1时才保存（至少有一轮对话）
  if (!messages || messages.length < 2) {
    return { success: false, error: '消息太少，不需要保存' };
  }
  
  // 生成聊天标题（使用第一个用户消息的前30个字符）
  const firstUserMessage = messages.find(msg => msg.role === 'user');
  const chatTitle = firstUserMessage ? 
    firstUserMessage.content.substring(0, 30) + (firstUserMessage.content.length > 30 ? '...' : '') :
    '新对话';
  
  // 检查API健康状态
  const apiHealthy = await checkAPIHealth();
  
  if (apiHealthy) {
    // 使用后端API保存到R2
    const saveResult = await saveChatToR2(messages, metadata);
    
    if (saveResult.success) {
      console.log('💾 聊天记录自动保存完成 (R2):', saveResult.chatId);
      return saveResult;
    }
  }
  
  // 后端不可用时，使用本地存储
  try {
    const chatRecord = formatChatRecord(messages, metadata);
    const localKey = `chat_backup_${chatRecord.id}`;
    localStorage.setItem(localKey, JSON.stringify(chatRecord));
    
    console.log('📱 聊天记录自动保存完成 (本地):', chatRecord.id);
    return {
      success: true,
      chatId: chatRecord.id,
      storage: 'local',
      title: chatTitle
    };
  } catch (error) {
    console.error('❌ 本地存储失败:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * 导出聊天记录为JSON文件
 */
export function exportChatAsJSON(messages, filename = null) {
  try {
    const chatRecord = formatChatRecord(messages);
    const jsonString = JSON.stringify(chatRecord, null, 2);
    
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || `chat_${chatRecord.id}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    URL.revokeObjectURL(url);
    
    console.log('💾 聊天记录已导出为JSON文件');
    return { success: true, filename: link.download };
  } catch (error) {
    console.error('❌ 导出失败:', error);
    return { success: false, error: error.message };
  }
}

/**
 * 删除聊天记录
 */
export async function deleteChatFromR2(chatId) {
  try {
    console.log('🗑️ 删除聊天记录:', chatId);
    
    const response = await fetch(`${API_CONFIG.baseUrl}/chat/delete/${chatId}`, {
      method: 'DELETE'
    });
    
    if (response.ok) {
      const result = await response.json();
      console.log('✅ 聊天记录删除成功:', chatId);
      
      // 同时删除本地备份
      try {
        const localKey = `chat_backup_${chatId}`;
        localStorage.removeItem(localKey);
      } catch (e) {
        // 忽略本地删除错误
      }
      
      return {
        success: true,
        message: result.message
      };
    } else {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
  } catch (error) {
    console.error('❌ 删除聊天记录失败:', error);
    return {
      success: false,
      error: error.message
    };
  }
} 