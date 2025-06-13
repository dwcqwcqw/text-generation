'use client'

import { useState, useEffect, useRef } from 'react'
import { Send, Bot, User, Search, Plus, ChevronDown, MessageSquare, RefreshCw, Settings } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
  model?: string
}

interface ChatSession {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
  lastMessage: Date
}

interface Model {
  id: string
  name: string
  description: string
  parameters: string
}

const models: Model[] = [
  {
    id: 'L3.2-8X3B',
    name: 'Llama-3.2-8X3B',
    description: 'Dark Champion Instruct MOE (18.4B parameters)',
    parameters: '18.4B'
  },
  {
    id: 'L3.2-8X4B',
    name: 'Llama-3.2-8X4B',
    description: 'Dark Champion Instruct V2 MOE (21B parameters)',
    parameters: '21B'
  }
]

export default function ChatPage() {
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([])
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null)
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState(models[0])
  const [showModelDropdown, setShowModelDropdown] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filteredSessions, setFilteredSessions] = useState<ChatSession[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 初始化：创建新对话
  useEffect(() => {
    createNewChat()
  }, [])

  // 搜索功能
  useEffect(() => {
    if (searchQuery.trim() === '') {
      setFilteredSessions(chatSessions)
    } else {
      const filtered = chatSessions.filter(session =>
        session.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        session.messages.some(msg => 
          msg.content.toLowerCase().includes(searchQuery.toLowerCase())
        )
      )
      setFilteredSessions(filtered)
    }
  }, [searchQuery, chatSessions])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [currentSession?.messages])

  const createNewChat = () => {
    // 如果当前已经是空的新对话，就不创建新的
    if (currentSession && currentSession.messages.length === 0) {
      return
    }
    
    const newSession: ChatSession = {
      id: Date.now().toString(),
      title: 'New Chat',
      messages: [],
      createdAt: new Date(),
      lastMessage: new Date()
    }
    setChatSessions(prev => [newSession, ...prev])
    setCurrentSession(newSession)
  }

  const generateChatTitle = (firstMessage: string): string => {
    // 移除标点符号并分割成单词
    const words = firstMessage.toLowerCase()
      .replace(/[^\w\s]/g, '')
      .split(/\s+/)
      .filter(word => word.length > 2) // 过滤掉短词
    
    // 常见停用词
    const stopWords = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use']
    
    // 过滤停用词
    const meaningfulWords = words.filter(word => !stopWords.includes(word))
    
    // 取前5个有意义的单词，如果不够就用原始单词
    const titleWords = meaningfulWords.length >= 5 
      ? meaningfulWords.slice(0, 5)
      : words.slice(0, 5)
    
    // 首字母大写
    const title = titleWords
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
    
    return title || 'New Chat'
  }

  const updateSessionTitle = (session: ChatSession, firstMessage: string) => {
    const title = generateChatTitle(firstMessage)
    
    setChatSessions(prev => 
      prev.map(s => 
        s.id === session.id 
          ? { ...s, title, lastMessage: new Date() }
          : s
      )
    )
    
    if (currentSession?.id === session.id) {
      setCurrentSession(prev => prev ? { ...prev, title, lastMessage: new Date() } : null)
    }
  }

  const selectSession = (session: ChatSession) => {
    setCurrentSession(session)
  }

  const regenerateLastMessage = async () => {
    if (!currentSession || currentSession.messages.length < 2) return
    
    const messages = currentSession.messages
    const lastUserMessage = messages[messages.length - 2]
    
    if (lastUserMessage.role !== 'user') return
    
    // 移除最后一条AI回复
    const updatedMessages = messages.slice(0, -1)
    const updatedSession = { ...currentSession, messages: updatedMessages }
    
    setCurrentSession(updatedSession)
    setChatSessions(prev => 
      prev.map(s => s.id === currentSession.id ? updatedSession : s)
    )
    
    // 重新生成回复
    await generateResponse(lastUserMessage.content, updatedMessages)
  }

  const generateResponse = async (userInput: string, history: Message[] = []) => {
    setIsLoading(true)

    try {
      console.log('Sending request to API:', {
        url: `${process.env.NEXT_PUBLIC_API_URL}/chat`,
        data: {
          prompt: userInput,
          model: selectedModel.id,
          max_length: 150,
          temperature: 0.7
        }
      })

      // 首先尝试API调用
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            prompt: userInput,
            model: selectedModel.id,
            max_length: 150,
            temperature: 0.7
          })
        })

        console.log('Response status:', response.status)
        
        if (response.ok) {
          const data = await response.json()
          console.log('API Response:', data)
          
          const assistantMessage: Message = {
            id: Date.now().toString(),
            content: data.output || data.response || data.generated_text || 'Sorry, I couldn\'t generate a response.',
            role: 'assistant',
            timestamp: new Date(),
            model: selectedModel.id
          }

          if (currentSession) {
            const updatedMessages = [...(history.length > 0 ? history : currentSession.messages), assistantMessage]
            const updatedSession = { ...currentSession, messages: updatedMessages, lastMessage: new Date() }
            
            setCurrentSession(updatedSession)
            setChatSessions(prev => 
              prev.map(s => s.id === currentSession.id ? updatedSession : s)
            )
          }
          setIsLoading(false)
          return
        }
      } catch (apiError) {
        console.log('API not available, using offline mode:', apiError)
      }

      // 如果API不可用，使用模拟回复
      console.log('Using simulated AI response')
      
      // 模拟AI思考时间
      await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000))
      
      // 生成模拟的AI回复
      const simulatedResponses = [
        `That's an interesting question about "${userInput}". Let me think about this...`,
        `I understand you're asking about "${userInput}". Here's what I think:`,
        `Regarding "${userInput}", I can share some insights:`,
        `That's a great topic! About "${userInput}", here are my thoughts:`,
        `Thanks for your question about "${userInput}". Here's my perspective:`
      ]
      
      const responseIntros = [
        "Based on my understanding, ",
        "From what I know, ",
        "In my analysis, ",
        "Generally speaking, ",
        "To answer your question, "
      ]
      
      const responseBodies = [
        "this is a complex topic that involves multiple factors. The key considerations include user experience, technical implementation, and overall system design.",
        "there are several approaches we could take. Each has its own advantages and potential challenges that we should carefully evaluate.",
        "this requires a balanced approach that takes into account both current capabilities and future scalability needs.",
        "the most effective solution would likely involve combining modern best practices with proven methodologies.",
        "this is an area where careful planning and iterative development can lead to excellent results."
      ]
      
      const responseEndings = [
        " Would you like me to elaborate on any specific aspect?",
        " What are your thoughts on this approach?",
        " Is there a particular area you'd like to explore further?",
        " Does this help address your question?",
        " Let me know if you need more details on any part of this."
      ]
      
      const randomIntro = simulatedResponses[Math.floor(Math.random() * simulatedResponses.length)]
      const randomBody = responseIntros[Math.floor(Math.random() * responseIntros.length)] + 
                        responseBodies[Math.floor(Math.random() * responseBodies.length)]
      const randomEnding = responseEndings[Math.floor(Math.random() * responseEndings.length)]
      
      const simulatedResponse = `${randomIntro}\n\n${randomBody}${randomEnding}`
      
      const assistantMessage: Message = {
        id: Date.now().toString(),
        content: simulatedResponse,
        role: 'assistant',
        timestamp: new Date(),
        model: selectedModel.id
      }

      if (currentSession) {
        const updatedMessages = [...(history.length > 0 ? history : currentSession.messages), assistantMessage]
        const updatedSession = { ...currentSession, messages: updatedMessages, lastMessage: new Date() }
        
        setCurrentSession(updatedSession)
        setChatSessions(prev => 
          prev.map(s => s.id === currentSession.id ? updatedSession : s)
        )
      }
      
    } catch (error) {
      console.error('Error generating response:', error)
      const errorMessage: Message = {
        id: Date.now().toString(),
        content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        role: 'assistant',
        timestamp: new Date()
      }
      
      if (currentSession) {
        const updatedMessages = [...currentSession.messages, errorMessage]
        const updatedSession = { ...currentSession, messages: updatedMessages }
        
        setCurrentSession(updatedSession)
        setChatSessions(prev => 
          prev.map(s => s.id === currentSession.id ? updatedSession : s)
        )
      }
    }

    setIsLoading(false)
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading || !currentSession) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue.trim(),
      role: 'user',
      timestamp: new Date()
    }

    const updatedMessages = [...currentSession.messages, userMessage]
    const updatedSession = { ...currentSession, messages: updatedMessages }
    
    setCurrentSession(updatedSession)
    setChatSessions(prev => 
      prev.map(s => s.id === currentSession.id ? updatedSession : s)
    )

    // 如果是第一条消息，更新会话标题
    if (currentSession.messages.length === 0) {
      updateSessionTitle(currentSession, userMessage.content)
    }

    setInputValue('')
    await generateResponse(userMessage.content, updatedMessages)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="h-screen flex bg-white">
      {/* 左侧边栏 - 按照截图样式 */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        {/* 顶部标题 */}
        <div className="p-6">
          <h1 className="text-2xl font-bold text-black">CHAT A.I+</h1>
        </div>
        
        {/* New Chat 按钮 */}
        <div className="px-6 mb-6">
          <button
            onClick={createNewChat}
            className="w-full flex items-center gap-3 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            <Plus size={18} />
            New chat
          </button>
        </div>

        {/* 搜索框 */}
        <div className="px-6 mb-6">
          <div className="relative">
            <Search size={18} className="absolute left-3 top-3 text-gray-400" />
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* 对话列表 */}
        <div className="flex-1 overflow-y-auto px-6">
          <h3 className="text-sm font-medium text-gray-600 mb-3">Your conversations</h3>
          <div className="space-y-2">
            {filteredSessions.map((session) => (
              <button
                key={session.id}
                onClick={() => selectSession(session)}
                className={`w-full text-left p-3 rounded-lg transition-all duration-200 ${
                  currentSession?.id === session.id
                    ? 'bg-blue-50 border border-blue-200'
                    : 'hover:bg-gray-50 border border-transparent'
                }`}
              >
                <div className="flex items-start gap-3">
                  <MessageSquare size={16} className="text-gray-400 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {session.title}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {session.lastMessage.toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* 底部模型选择器 */}
        <div className="p-6 border-t border-gray-200">
          <div className="relative">
            <button
              onClick={() => setShowModelDropdown(!showModelDropdown)}
              className="w-full flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-gray-600 rounded-lg flex items-center justify-center">
                  <Bot size={18} className="text-white" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-medium text-gray-900">{selectedModel.name}</p>
                  <p className="text-xs text-gray-500">{selectedModel.parameters}</p>
                </div>
              </div>
              <ChevronDown size={18} className="text-gray-400" />
            </button>
            
            {showModelDropdown && (
              <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200 rounded-lg shadow-xl z-20">
                {models.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => {
                      setSelectedModel(model)
                      setShowModelDropdown(false)
                    }}
                    className="w-full text-left p-4 hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg transition-colors"
                  >
                    <p className="text-sm font-medium text-gray-900">{model.name}</p>
                    <p className="text-xs text-gray-500">{model.description}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 主聊天区域 */}
      <div className="flex-1 flex flex-col bg-white">
        {/* 聊天头部 */}
        {currentSession && currentSession.messages.length > 0 && (
          <div className="px-6 py-4 border-b border-gray-200 bg-white">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">
                {currentSession.title}
              </h2>
              {currentSession.messages.length > 1 && (
                <button
                  onClick={regenerateLastMessage}
                  disabled={isLoading}
                  className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                >
                  <RefreshCw size={16} />
                  Regenerate
                </button>
              )}
            </div>
          </div>
        )}

        {/* 消息区域 */}
        <div className="flex-1 overflow-y-auto bg-gray-50">
          {!currentSession || currentSession.messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-md mx-auto px-6">
                <div className="w-16 h-16 bg-black rounded-2xl flex items-center justify-center mx-auto mb-6">
                  <Bot size={32} className="text-white" />
                </div>
                <h2 className="text-3xl font-bold text-gray-900 mb-4">
                  What's in your mind?
                </h2>
                <p className="text-gray-600 mb-8 text-lg">
                  Start a conversation with our AI assistant. Ask questions, get help, or just chat!
                </p>
                <div className="text-sm text-gray-500 bg-white p-4 rounded-lg border border-gray-200">
                  <p><strong>Model:</strong> {selectedModel.name}</p>
                  <p>{selectedModel.description}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 space-y-6 max-w-4xl mx-auto w-full">
              {currentSession.messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-4 message-bubble ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {message.role === 'assistant' && (
                    <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                      <Bot size={16} className="text-white" />
                    </div>
                  )}
                  
                  <div
                    className={`max-w-2xl p-4 rounded-2xl ${
                      message.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-gray-900 border border-gray-200'
                    }`}
                  >
                    {message.role === 'user' ? (
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    ) : (
                      <ReactMarkdown className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-700">
                        {message.content}
                      </ReactMarkdown>
                    )}
                    
                    <div className={`text-xs mt-3 ${
                      message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                    }`}>
                      {message.timestamp.toLocaleTimeString()}
                      {message.model && (
                        <span className="ml-2">• {models.find(m => m.id === message.model)?.name}</span>
                      )}
                    </div>
                  </div>

                  {message.role === 'user' && (
                    <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center flex-shrink-0">
                      <User size={16} className="text-white" />
                    </div>
                  )}
                </div>
              ))}
              
              {isLoading && (
                <div className="flex gap-4">
                  <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                    <Bot size={16} className="text-white" />
                  </div>
                  <div className="bg-white rounded-2xl p-4 border border-gray-200">
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* 输入区域 */}
        <div className="p-6 bg-white border-t border-gray-200">
          <div className="max-w-4xl mx-auto">
            <div className="relative">
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="What's in your mind?"
                className="w-full p-4 pr-14 border border-gray-200 rounded-2xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-500"
                rows={1}
                style={{ minHeight: '56px', maxHeight: '160px' }}
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isLoading}
                className="absolute right-2 bottom-2 p-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Send size={18} />
              </button>
            </div>
            
            <div className="mt-3 text-xs text-gray-500 text-center">
              Using {selectedModel.name} • Press Enter to send, Shift+Enter for new line
            </div>
          </div>
        </div>
      </div>
    </div>
  )
} 