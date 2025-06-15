/**
 * Cloudflare R2存储模块
 * 用于保存和管理聊天记录
 */

// API配置
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
  return `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * 格式化聊天记录
 */
function formatChatRecord(messages, metadata = {}) {
  return {
    id: generateChatId(),
    timestamp: new Date().toISOString(),
    messages: messages.map(msg => ({
      ...msg,
      timestamp: msg.timestamp || new Date().toISOString()
    })),
    metadata: {
      version: '1.0',
      model: metadata.model || 'unknown',
      ...metadata
    }
  };
}

/**
 * 保存聊天记录到R2 (通过后端API)
 */
export async function saveChatToR2(messages, metadata = {}) {
  try {
    const chatRecord = formatChatRecord(messages, metadata);
    
    console.log('💾 通过后端API保存聊天记录到R2:', chatRecord.id);
    
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
      console.log('✅ 聊天记录保存成功:', chatRecord.id);
      return {
        success: true,
        chatId: chatRecord.id,
        result: result
      };
    } else {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    
  } catch (error) {
    console.error('❌ 保存聊天记录失败:', error);
    
    // 如果后端API不可用，尝试本地存储作为备份
    try {
      const chatRecord = formatChatRecord(messages, metadata);
      const localKey = `chat_backup_${chatRecord.id}`;
      localStorage.setItem(localKey, JSON.stringify(chatRecord));
      console.log('📱 已保存到本地存储作为备份:', localKey);
      
      return {
        success: true,
        chatId: chatRecord.id,
        storage: 'local_backup'
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
 * 从R2加载聊天记录 (通过后端API)
 */
export async function loadChatFromR2(chatId) {
  try {
    console.log('📥 通过后端API从R2加载聊天记录:', chatId);
    
    const response = await fetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.loadChat}/${chatId}`);
    
    if (response.ok) {
      const chatRecord = await response.json();
      console.log('✅ 聊天记录加载成功:', chatId);
      return {
        success: true,
        data: chatRecord
      };
    } else if (response.status === 404) {
      // 尝试从本地存储加载备份
      try {
        const localKey = `chat_backup_${chatId}`;
        const localData = localStorage.getItem(localKey);
        if (localData) {
          console.log('📱 从本地存储加载备份:', localKey);
          return {
            success: true,
            data: JSON.parse(localData),
            storage: 'local_backup'
          };
        }
      } catch (localError) {
        console.error('❌ 本地存储加载失败:', localError);
      }
      
      return {
        success: false,
        error: '聊天记录不存在'
      };
    } else {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
  } catch (error) {
    console.error('❌ 加载聊天记录失败:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * 列出用户的聊天记录 (通过后端API)
 */
export async function listUserChats(userId = 'anonymous', date = null) {
  try {
    const dateParam = date || new Date().toISOString().split('T')[0].replace(/-/g, '/');
    const url = `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.listChats}/${dateParam}`;
    
    console.log('📋 获取聊天历史:', url);
    
    const response = await fetch(url);
    
    if (response.ok) {
      const data = await response.json();
      return {
        success: true,
        chats: data.chats || []
      };
    } else if (response.status === 404) {
      return {
        success: true,
        chats: []
      };
    } else {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
  } catch (error) {
    console.error('❌ 获取聊天列表失败:', error);
    
    // 尝试从本地存储获取备份列表
    try {
      const backupChats = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('chat_backup_')) {
          try {
            const data = JSON.parse(localStorage.getItem(key));
            backupChats.push({
              id: data.id,
              title: data.messages.find(msg => msg.role === 'user')?.content.substring(0, 30) + '...' || '备份对话',
              timestamp: data.timestamp,
              storage: 'local_backup'
            });
          } catch (e) {
            // 忽略损坏的备份
          }
        }
      }
      
      console.log('📱 从本地存储获取备份聊天列表:', backupChats.length);
      return {
        success: true,
        chats: backupChats
      };
    } catch (localError) {
      return {
        success: false,
        error: error.message
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