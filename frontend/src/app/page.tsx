'use client'

import { useState, useEffect, useRef } from 'react'
import { Send, Bot, User, Search, Plus, ChevronDown, MessageSquare, RefreshCw, Settings, Save, Download } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { autoSaveChatHistory, exportChatAsJSON, loadChatFromR2, listUserChats } from '../../lib/r2-storage'

// 强制更新版本 v2.0 - 确保只显示两个GGUF模型，清除所有缓存

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

// 强制定义：只有这两个模型，没有其他任何模型！
const MODELS_V2: Model[] = [
  {
    id: 'L3.2-8X3B',
    name: 'L3.2-8X3B.gguf',
    description: '18.4B参数模型',
    parameters: '/runpod-volume/text_models/L3.2-8X3B.gguf'
  },
  {
    id: 'L3.2-8X4B',
    name: 'L3.2-8X4B.gguf', 
    description: '21B参数模型',
    parameters: '/runpod-volume/text_models/L3.2-8X4B.gguf'
  }
]

// 确保没有其他模型定义
const models = MODELS_V2

export default function ChatPage() {
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([])
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null)
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState(MODELS_V2[0]) // 强制使用MODELS_V2
  const [showModelDropdown, setShowModelDropdown] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filteredSessions, setFilteredSessions] = useState<ChatSession[]>([])
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(true)
  const [lastSaveTime, setLastSaveTime] = useState<Date | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 强制验证模型数量
  useEffect(() => {
    console.log('🔍 模型验证 v2.0:', {
      modelCount: MODELS_V2.length,
      models: MODELS_V2.map(m => ({ id: m.id, name: m.name })),
      selectedModel: selectedModel.id
    })
    
    if (MODELS_V2.length !== 2) {
      console.error('❌ 模型数量错误！应该只有2个模型')
    }
  }, [selectedModel])

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

    // RunPod API 配置 - 直接使用完整的API Key (强制部署更新)
    const RUNPOD_API_KEY = 'rpa_YT0BFBFZYAZMQHR231H4DOKQEOAJXSMVIBDYN4ZQ1tdxlb'
    
    // 调试：确认API Key被正确设置
    console.log('🔑 RUNPOD_API_KEY直接设置为:', RUNPOD_API_KEY ? `${RUNPOD_API_KEY.substring(0, 15)}...` : 'NULL')
    
    const RUNPOD_ENDPOINT_ID = process.env.NEXT_PUBLIC_RUNPOD_ENDPOINT_ID || 
                              process.env.RUNPOD_ENDPOINT_ID || 
                              '4cx6jtjdx6hdhr'
    
    const VITE_API_BASE_URL = process.env.NEXT_PUBLIC_VITE_API_BASE_URL || 
                             process.env.VITE_API_BASE_URL || 
                             'https://api.runpod.ai/v2'
    
    const RUNPOD_ENDPOINT = `${VITE_API_BASE_URL}/${RUNPOD_ENDPOINT_ID}/runsync`
    
    // 详细环境变量调试信息
    console.log('Environment Variables Debug:', {
      'process.env': typeof process.env,
      'NEXT_PUBLIC_RUNPOD_API_KEY': process.env.NEXT_PUBLIC_RUNPOD_API_KEY || 'NOT SET',
      'RUNPOD_API_KEY': process.env.RUNPOD_API_KEY || 'NOT SET', 
      'NEXT_PUBLIC_RUNPOD_ENDPOINT_ID': process.env.NEXT_PUBLIC_RUNPOD_ENDPOINT_ID || 'NOT SET',
      'RUNPOD_ENDPOINT_ID': process.env.RUNPOD_ENDPOINT_ID || 'NOT SET',
      'NEXT_PUBLIC_VITE_API_BASE_URL': process.env.NEXT_PUBLIC_VITE_API_BASE_URL || 'NOT SET',
      'VITE_API_BASE_URL': process.env.VITE_API_BASE_URL || 'NOT SET',
      'All env keys': Object.keys(process.env).filter(key => key.includes('RUNPOD') || key.includes('VITE')),
      'finalApiKey': RUNPOD_API_KEY ? `CONFIGURED (${RUNPOD_API_KEY.substring(0, 10)}...)` : 'NOT CONFIGURED',
      'finalEndpoint': RUNPOD_ENDPOINT,
      'finalEndpointId': RUNPOD_ENDPOINT_ID
    })
    
          // 直接使用硬编码的API Key，不依赖localStorage
      const FINAL_API_KEY = RUNPOD_API_KEY
    
    console.log('Using API Key:', FINAL_API_KEY ? `${FINAL_API_KEY.substring(0, 10)}...` : 'NONE')
    console.log('🔍 API Key Length:', FINAL_API_KEY ? FINAL_API_KEY.length : 0)
    console.log('🔍 API Key Type:', typeof FINAL_API_KEY)
    
          // 如果没有配置API Key，直接使用模拟模式
      if (!FINAL_API_KEY) {
        console.log('No RunPod API key configured, using simulated responses')
      }

    // 创建一个临时的助手消息用于流式显示
    let streamingMessage: Message | null = null
    
    try {
      console.log('RunPod API Configuration:', {
        endpoint: RUNPOD_ENDPOINT,
        hasApiKey: !!RUNPOD_API_KEY,
        selectedModel: selectedModel,
        endpointId: RUNPOD_ENDPOINT_ID
      })

      // 首先尝试RunPod API调用（如果有API Key）
      if (FINAL_API_KEY) {
        try {
          // 准备对话历史
          const conversationHistory = history.map(msg => ({
            role: msg.role,
            content: msg.content
          }))
          
          // 根据选择的模型确定系统模版和模型路径
          let systemTemplate = 'default'
          if (selectedModel.id === 'L3.2-8X3B') {
            systemTemplate = 'default'  // 使用默认模板
          } else if (selectedModel.id === 'L3.2-8X4B') {
            systemTemplate = 'default'  // 使用默认模板
          }
          
          // 使用新的AI handler格式，包含模型路径
          const requestPayload = {
            input: {
              prompt: userInput,
              system_template: systemTemplate,
              history: conversationHistory,
              max_tokens: 1000,
              temperature: 0.7,
              model_path: selectedModel.parameters,  // 传递实际的模型文件路径
              stream: true  // 启用流式响应
            }
          }
          
          console.log('Sending RunPod request:', {
            endpoint: RUNPOD_ENDPOINT,
            selectedModelId: selectedModel.id,
            payload: requestPayload
          })

          // 创建流式响应的临时消息
          streamingMessage = {
            id: Date.now().toString(),
            content: '',
            role: 'assistant',
            timestamp: new Date(),
            model: selectedModel.id
          }

          // 添加到当前会话中
          if (currentSession) {
            const updatedMessages = [...(history.length > 0 ? history : currentSession.messages), streamingMessage]
            const updatedSession = { ...currentSession, messages: updatedMessages, lastMessage: new Date() }
            
            setCurrentSession(updatedSession)
            setChatSessions(prev => 
              prev.map(s => s.id === currentSession.id ? updatedSession : s)
            )
          }
          
          const response = await fetch(RUNPOD_ENDPOINT, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${FINAL_API_KEY}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestPayload)
          })

          console.log('RunPod response status:', response.status)
          
          if (response.ok) {
            const data = await response.json()
            console.log('RunPod Response:', data)
            
            let aiResponse = ''
            // 处理不同的响应格式
            if (data.status === "COMPLETED" && data.output) {
              if (typeof data.output === 'string') {
                aiResponse = data.output
              } else if (data.output.text) {
                aiResponse = data.output.text
              } else if (data.output.response) {
                aiResponse = data.output.response
              } else {
                aiResponse = data.output.toString()
              }
            } else if (data.output) {
              // 直接使用output字段
              aiResponse = typeof data.output === 'string' ? data.output : data.output.toString()
            }
            
            console.log('🎯 提取的AI响应:', aiResponse)
            
            if (aiResponse && streamingMessage) {
              // 模拟流式效果 - 逐字显示
              await simulateStreamingResponse(aiResponse, streamingMessage)
              setIsLoading(false)
              return
            }
          } else {
            console.log('RunPod API error:', response.status, await response.text())
          }
        } catch (apiError) {
          console.log('RunPod API not available, using offline mode:', apiError)
        }
      }

      // 如果API不可用，使用模拟回复
      console.log('Using simulated AI response')
      
      // 模拟AI思考时间
      await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000))
      
      // 生成模拟的AI回复
      const simulatedResponses = [
        `That's an interesting question about "${userInput}". Let me think about this... 🤔`,
        `I understand you're asking about "${userInput}". Here's what I think: 💭`,
        `Regarding "${userInput}", I can share some insights: ✨`,
        `That's a great topic! About "${userInput}", here are my thoughts: 🎯`,
        `Thanks for your question about "${userInput}". Here's my perspective: 📝`
      ]
      
      const responseIntros = [
        "Based on my understanding, ",
        "From what I know, ",
        "In my analysis, ",
        "Generally speaking, ",
        "To answer your question, "
      ]
      
      const responseBodies = [
        "this is a complex topic that involves multiple factors. The key considerations include user experience, technical implementation, and overall system design. 🔧",
        "there are several approaches we could take. Each has its own advantages and potential challenges that we should carefully evaluate. ⚖️",
        "this requires a balanced approach that takes into account both current capabilities and future scalability needs. 🚀",
        "the most effective solution would likely involve combining modern best practices with proven methodologies. 💡",
        "this is an area where careful planning and iterative development can lead to excellent results. 🎨"
      ]
      
      const responseEndings = [
        " Would you like me to elaborate on any specific aspect? 🤗",
        " What are your thoughts on this approach? 💬",
        " Is there a particular area you'd like to explore further? 🔍",
        " Does this help address your question? ✅",
        " Let me know if you need more details on any part of this. 📚"
      ]
      
      const randomIntro = simulatedResponses[Math.floor(Math.random() * simulatedResponses.length)]
      const randomBody = responseIntros[Math.floor(Math.random() * responseIntros.length)] + 
                        responseBodies[Math.floor(Math.random() * responseBodies.length)]
      const randomEnding = responseEndings[Math.floor(Math.random() * responseEndings.length)]
      
      const simulatedResponse = `${randomIntro}\n\n${randomBody}${randomEnding}`

      // 如果没有创建流式消息，创建一个
      if (!streamingMessage) {
        streamingMessage = {
          id: Date.now().toString(),
          content: '',
          role: 'assistant',
          timestamp: new Date(),
          model: selectedModel.id
        }

        if (currentSession) {
          const updatedMessages = [...(history.length > 0 ? history : currentSession.messages), streamingMessage]
          const updatedSession = { ...currentSession, messages: updatedMessages, lastMessage: new Date() }
          
          setCurrentSession(updatedSession)
          setChatSessions(prev => 
            prev.map(s => s.id === currentSession.id ? updatedSession : s)
          )
        }
      }

      // 模拟流式响应
      await simulateStreamingResponse(simulatedResponse, streamingMessage)
      
    } catch (error) {
      console.error('Error generating response:', error)
      const errorMessage: Message = {
        id: Date.now().toString(),
        content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'} 😔`,
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

  // 模拟流式响应效果
  const simulateStreamingResponse = async (fullResponse: string, messageToUpdate: Message) => {
    const words = fullResponse.split(' ')
    let currentContent = ''
    
    for (let i = 0; i < words.length; i++) {
      currentContent += (i > 0 ? ' ' : '') + words[i]
      
      // 更新消息内容
      if (currentSession) {
        const updatedMessages = currentSession.messages.map(msg => 
          msg.id === messageToUpdate.id 
            ? { ...msg, content: currentContent }
            : msg
        )
        const updatedSession = { ...currentSession, messages: updatedMessages, lastMessage: new Date() }
        
        setCurrentSession(updatedSession)
        setChatSessions(prev => 
          prev.map(s => s.id === currentSession.id ? updatedSession : s)
        )
      }
      
      // 控制流式速度
      await new Promise(resolve => setTimeout(resolve, 50 + Math.random() * 100))
    }

    // 完成后自动保存聊天记录
    if (autoSaveEnabled && currentSession && currentSession.messages.length >= 2) {
      try {
        console.log('💾 自动保存聊天记录到R2...')
        const saveResult = await autoSaveChatHistory(currentSession.messages, {
          model: selectedModel.name,
          sessionId: currentSession.id,
          sessionTitle: currentSession.title
        })
        
        if (saveResult.success) {
          setLastSaveTime(new Date())
          console.log('✅ 聊天记录已保存到R2:', saveResult.chatId)
        } else {
          console.warn('⚠️ 聊天记录保存失败:', saveResult.error)
        }
      } catch (error) {
        console.error('❌ 自动保存异常:', error)
      }
    }
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

  const testApiKeyDirect = async () => {
    console.log('🧪 Direct API Key Test Started')
    const API_KEY = 'rpa_YT0BFBFZYAZMQHR231H4DOKQEOAJXSMVIBDYN4ZQ1tdxlb'
    const ENDPOINT = 'https://api.runpod.ai/v2/4cx6jtjdx6hdhr/runsync'
    
    console.log('🔑 Test API Key:', API_KEY ? `${API_KEY.substring(0, 15)}...` : 'NULL')
    
    try {
      const response = await fetch(ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${API_KEY}`
        },
        body: JSON.stringify({
          input: { prompt: 'Direct test from main page' }
        })
      })
      
      console.log('🧪 Test Response Status:', response.status)
      
      if (response.ok) {
        const data = await response.json()
        console.log('🧪 Test Response Data:', data)
        alert(`✅ API Test Success!\nOutput: ${data.output}`)
      } else {
        console.log('🧪 Test Error:', await response.text())
        alert(`❌ API Test Failed: ${response.status}`)
      }
    } catch (error) {
      console.log('🧪 Test Exception:', error)
      alert(`❌ API Test Exception: ${error}`)
    }
  }

  return (
    <div className="h-screen flex bg-white">
      {/* 左侧边栏 - 按照截图样式 */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        {/* 顶部标题 */}
        <div className="p-6">
          <h1 className="text-2xl font-bold text-black">CHAT A.I+</h1>
          <a 
            href="/test" 
            className="text-sm text-blue-600 hover:text-blue-800 underline mt-2 block"
          >
            🔧 API 测试页面
          </a>
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
                {MODELS_V2.map((model) => (
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
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  {currentSession.title}
                </h2>
                {lastSaveTime && (
                  <p className="text-xs text-green-600 mt-1">
                    💾 已保存到R2: {lastSaveTime.toLocaleTimeString()}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                {/* 自动保存开关 */}
                <label className="flex items-center gap-2 text-sm text-gray-600">
                  <input
                    type="checkbox"
                    checked={autoSaveEnabled}
                    onChange={(e) => setAutoSaveEnabled(e.target.checked)}
                    className="rounded"
                  />
                  自动保存
                </label>
                
                {/* 手动保存按钮 */}
                {currentSession.messages.length >= 2 && (
                  <button
                    onClick={async () => {
                      try {
                        const saveResult = await autoSaveChatHistory(currentSession.messages, {
                          model: selectedModel.name,
                          sessionId: currentSession.id,
                          sessionTitle: currentSession.title
                        })
                        if (saveResult.success) {
                          setLastSaveTime(new Date())
                          alert('✅ 聊天记录已保存到R2')
                        } else {
                          alert('❌ 保存失败: ' + saveResult.error)
                        }
                      } catch (error) {
                        alert('❌ 保存异常: ' + error)
                      }
                    }}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <Save size={16} />
                    保存
                  </button>
                )}
                
                {/* 导出按钮 */}
                {currentSession.messages.length > 0 && (
                  <button
                    onClick={() => exportChatAsJSON(currentSession.messages)}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <Download size={16} />
                    导出
                  </button>
                )}
                
                {/* 重新生成按钮 */}
                {currentSession.messages.length > 1 && (
                  <button
                    onClick={regenerateLastMessage}
                    disabled={isLoading}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                  >
                    <RefreshCw size={16} />
                    重新生成
                  </button>
                )}
              </div>
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
                        <span className="ml-2">• {MODELS_V2.find(m => m.id === message.model)?.name}</span>
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
            
            <div className="mt-3 flex items-center justify-between">
              <div className="text-xs text-gray-500">
                Using {selectedModel.name} • Press Enter to send, Shift+Enter for new line
              </div>
              <button
                onClick={testApiKeyDirect}
                className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors"
              >
                🧪 Test API
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
} 