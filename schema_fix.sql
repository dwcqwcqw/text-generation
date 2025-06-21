-- 修复后的D1数据库表结构
-- 移除外键约束以简化操作

-- 删除现有表
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS conversations;
DROP TABLE IF EXISTS users;

-- 重新创建用户表
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  username TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 重新创建对话表 (移除外键约束)
CREATE TABLE conversations (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT,
  system_prompt TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 重新创建消息表 (移除外键约束)
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  conversation_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  metadata TEXT, -- JSON格式存储额外信息
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引优化查询性能
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);

-- 插入默认系统提示
INSERT INTO users (id, username) VALUES ('system', 'System');
INSERT INTO conversations (id, user_id, title, system_prompt) VALUES 
  ('default', 'system', 'Default Conversation', '你是一个友善、专业的中文AI助手。请用简洁、准确的语言回答用户的问题。'); 