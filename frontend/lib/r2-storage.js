/**
 * Cloudflare R2存储模块
 * 用于保存和管理聊天记录
 */

// R2配置
const R2_CONFIG = {
  endpoint: 'https://c7c141ce43d175e60601edc46d904553.r2.cloudflarestorage.com',
  bucket: 'text-generation',
  region: 'auto'
};

/**
 * 生成聊天记录的唯一ID
 */
function generateChatId() {
  return `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * 格式化聊天记录数据
 */
function formatChatRecord(messages, metadata = {}) {
  return {
    id: generateChatId(),
    timestamp: new Date().toISOString(),
    messages: messages,
    metadata: {
      userAgent: navigator.userAgent,
      url: window.location.href,
      ...metadata
    },
    version: '1.0'
  };
}

/**
 * 保存聊天记录到R2
 */
export async function saveChatToR2(messages, metadata = {}) {
  try {
    const chatRecord = formatChatRecord(messages, metadata);
    const fileName = `chats/${chatRecord.id}.json`;
    
    console.log('💾 保存聊天记录到R2:', fileName);
    
    // 使用S3兼容API上传到R2
    const response = await fetch(`${R2_CONFIG.endpoint}/${R2_CONFIG.bucket}/${fileName}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'x-amz-acl': 'private'
      },
      body: JSON.stringify(chatRecord, null, 2)
    });
    
    if (response.ok) {
      console.log('✅ 聊天记录保存成功:', chatRecord.id);
      return {
        success: true,
        chatId: chatRecord.id,
        url: `${R2_CONFIG.endpoint}/${R2_CONFIG.bucket}/${fileName}`
      };
    } else {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
  } catch (error) {
    console.error('❌ 保存聊天记录失败:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * 从R2加载聊天记录
 */
export async function loadChatFromR2(chatId) {
  try {
    const fileName = `chats/${chatId}.json`;
    
    console.log('📥 从R2加载聊天记录:', fileName);
    
    const response = await fetch(`${R2_CONFIG.endpoint}/${R2_CONFIG.bucket}/${fileName}`);
    
    if (response.ok) {
      const chatRecord = await response.json();
      console.log('✅ 聊天记录加载成功:', chatId);
      return {
        success: true,
        data: chatRecord
      };
    } else if (response.status === 404) {
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
 * 列出用户的聊天记录
 */
export async function listUserChats(userId = 'anonymous') {
  try {
    // 由于R2不直接支持列表操作，我们使用一个索引文件
    const indexFile = `users/${userId}/chat_index.json`;
    
    const response = await fetch(`${R2_CONFIG.endpoint}/${R2_CONFIG.bucket}/${indexFile}`);
    
    if (response.ok) {
      const index = await response.json();
      return {
        success: true,
        chats: index.chats || []
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
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * 更新用户聊天索引
 */
export async function updateUserChatIndex(chatId, chatTitle, userId = 'anonymous') {
  try {
    const indexFile = `users/${userId}/chat_index.json`;
    
    // 先获取现有索引
    let index = { chats: [] };
    try {
      const response = await fetch(`${R2_CONFIG.endpoint}/${R2_CONFIG.bucket}/${indexFile}`);
      if (response.ok) {
        index = await response.json();
      }
    } catch (e) {
      // 索引文件不存在，使用默认值
    }
    
    // 添加新的聊天记录
    const chatEntry = {
      id: chatId,
      title: chatTitle || '新对话',
      timestamp: new Date().toISOString()
    };
    
    // 避免重复
    index.chats = index.chats.filter(chat => chat.id !== chatId);
    index.chats.unshift(chatEntry); // 最新的在前面
    
    // 限制最多保存100个聊天记录
    if (index.chats.length > 100) {
      index.chats = index.chats.slice(0, 100);
    }
    
    // 保存更新的索引
    const response = await fetch(`${R2_CONFIG.endpoint}/${R2_CONFIG.bucket}/${indexFile}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'x-amz-acl': 'private'
      },
      body: JSON.stringify(index, null, 2)
    });
    
    if (response.ok) {
      console.log('✅ 聊天索引更新成功');
      return { success: true };
    } else {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
  } catch (error) {
    console.error('❌ 更新聊天索引失败:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * 自动保存聊天记录（带去重）
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
  
  // 保存聊天记录
  const saveResult = await saveChatToR2(messages, metadata);
  
  if (saveResult.success) {
    // 更新用户索引
    await updateUserChatIndex(saveResult.chatId, chatTitle);
    
    console.log('💾 聊天记录自动保存完成:', saveResult.chatId);
    return saveResult;
  }
  
  return saveResult;
}

/**
 * 导出聊天记录为JSON文件
 */
export function exportChatAsJSON(messages, filename = null) {
  const chatRecord = formatChatRecord(messages, { exported: true });
  const jsonString = JSON.stringify(chatRecord, null, 2);
  const blob = new Blob([jsonString], { type: 'application/json' });
  
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename || `chat_${chatRecord.id}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  
  console.log('📁 聊天记录已导出:', a.download);
} 