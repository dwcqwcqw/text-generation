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
  const [autoSave, setAutoSave] = useState(true)
  const [lastSaveTime, setLastSaveTime] = useState<Date | null>(null)
  const [saveStatus, setSaveStatus] = useState<'none' | 'saving' | 'saved' | 'local' | 'error'>('none')
  const [apiHealthy, setApiHealthy] = useState<boolean | null>(null)
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
    if (!currentSession) {
      console.log('🔄 初始化：创建新对话')
      createNewChat()
    } else {
      console.log('🔄 初始化：已有对话，跳过创建', currentSession.id)
    }
  }, [])

  // 添加调试日志，监控currentSession变化
  useEffect(() => {
    console.log('🧪 currentSession 更新:', 
      currentSession ? 
      { 
        id: currentSession.id, 
        title: currentSession.title, 
        messagesCount: currentSession.messages.length 
      } : 'null'
    )
  }, [currentSession])

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

  // 生成对话标题（不超过5个单词）
  const generateChatTitle = (firstMessage: string): string => {
    const words = firstMessage.trim().split(/\s+/).slice(0, 4) // 最多4个词
    const title = words.join(' ')
    return title.length > 20 ? title.substring(0, 17) + '...' : title
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

    // 保存当前会话ID，用于后续确认是否仍在同一会话中
    const currentSessionId = currentSession?.id
    console.log('🔄 开始生成回复，当前会话ID:', currentSessionId)

    // 使用传入的历史记录，不再添加用户消息（已在handleSendMessage中添加）
    let updatedSession = currentSession
    
    // 如果是第一条消息，更新会话标题
    if (currentSession && history.length === 1 && history[0].role === 'user') {
      updateSessionTitle(currentSession, history[0].content)
    }

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
    
    // 直接使用硬编码的API Key，不依赖localStorage
    const FINAL_API_KEY = RUNPOD_API_KEY
    
    console.log('Using API Key:', FINAL_API_KEY ? `${FINAL_API_KEY.substring(0, 10)}...` : 'NONE')

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
          // 再次确认会话ID是否一致
          if (currentSession?.id !== currentSessionId) {
            console.warn('⚠️ API调用前会话ID已变化，从', currentSessionId, '变为', currentSession?.id)
            // 如果会话ID已变，可能用户切换了会话，需要谨慎处理
          }
          
          // 准备对话历史 - 确保内容是字符串格式，过滤[object Object]
          const conversationHistory = history.map(msg => ({
            role: msg.role,
            content: typeof msg.content === 'string' ? msg.content : String(msg.content || '')
          })).filter(msg => {
            const content = msg.content.trim()
            return content !== '' && content !== '[object Object]' && content !== 'undefined' && content !== 'null'
          })
          
          console.log('🗂️ 过滤后的对话历史:', conversationHistory)
          
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
              stream: false  // 先关闭流式，确保基础功能正常
            }
          }
          
          console.log('📤 发送到RunPod的请求:', {
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

          // 添加AI响应消息到当前会话
          if (updatedSession) {
            // 再次确认会话ID是否一致
            if (currentSession?.id !== currentSessionId) {
              console.warn('⚠️ 添加AI响应前会话ID已变化，从', currentSessionId, '变为', currentSession?.id)
              // 如果会话ID已变，尝试在当前会话中添加消息
              if (currentSession) {
                const updatedMessages = [...currentSession.messages, streamingMessage]
                const newUpdatedSession = { ...currentSession, messages: updatedMessages, lastMessage: new Date() }
                
                setCurrentSession(newUpdatedSession)
                setChatSessions(prev => 
                  prev.map(s => s.id === currentSession.id ? newUpdatedSession : s)
                )
              }
            } else {
              // 会话ID一致，正常添加消息
              const updatedMessages = [...updatedSession.messages, streamingMessage]
              updatedSession = { ...updatedSession, messages: updatedMessages, lastMessage: new Date() }
              
              setCurrentSession(updatedSession)
              setChatSessions(prev => 
                prev.map(s => s.id === updatedSession!.id ? updatedSession! : s)
              )
            }
          }
          
          const response = await fetch(RUNPOD_ENDPOINT, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${FINAL_API_KEY}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestPayload)
          })

          console.log('📡 RunPod响应状态:', response.status)
          
          if (response.ok) {
            try {
              const data = await response.json()
              console.log('📦 RunPod完整响应:', JSON.stringify(data, null, 2))
              
              let aiResponse = ''
              
              // 详细的响应解析逻辑，添加步骤式调试
              console.log('🔍 开始解析响应...')
              console.log('🔍 data类型:', typeof data)
              console.log('🔍 data内容:', data)
              
              if (data && typeof data === 'object') {
                console.log('✅ data是有效对象')
                
                try {
                  // 检查output字段
                  console.log('🔍 output存在:', 'output' in data)
                  console.log('🔍 output类型:', typeof data.output)
                  console.log('🔍 output内容:', data.output)
                  
                  // 直接处理output字段 - 简化逻辑
                  if (data.output !== null && data.output !== undefined) {
                    console.log('✅ 发现output字段，开始处理')
                    
                    // 检查output是否为对象类型，如果是则尝试提取其中的文本内容
                    if (typeof data.output === 'object' && data.output !== null) {
                      console.log('🔍 output是对象类型，尝试提取内容')
                      
                      // 尝试从对象中提取文本内容
                      if ('model_info' in data.output && 'output' in data.output) {
                        // 处理特定格式的响应 {model_info: {...}, output: "文本内容", status: "success"}
                        aiResponse = String(data.output.output).trim()
                        console.log('✅ 从model_info/output格式提取的响应:', aiResponse)
                      } else if (data.output.text) {
                        aiResponse = String(data.output.text).trim()
                        console.log('✅ 从text字段提取的响应:', aiResponse)
                      } else if (data.output.response) {
                        aiResponse = String(data.output.response).trim()
                        console.log('✅ 从response字段提取的响应:', aiResponse)
                      } else if (data.output.content) {
                        aiResponse = String(data.output.content).trim()
                        console.log('✅ 从content字段提取的响应:', aiResponse)
                      } else {
                        // 如果没有找到合适的字段，使用JSON字符串
                        const outputStr = JSON.stringify(data.output)
                        console.log('⚠️ 未找到标准字段，使用JSON字符串:', outputStr)
                        
                        // 尝试从JSON字符串中提取可能的文本内容
                        try {
                          const outputObj = JSON.parse(outputStr)
                          if (typeof outputObj === 'string') {
                            aiResponse = outputObj
                          } else if (outputObj && typeof outputObj === 'object') {
                            // 尝试从嵌套对象中提取文本
                            if (outputObj.text) aiResponse = String(outputObj.text)
                            else if (outputObj.content) aiResponse = String(outputObj.content)
                            else if (outputObj.message) aiResponse = String(outputObj.message)
                            else if (outputObj.response) aiResponse = String(outputObj.response)
                            else if (outputObj.result) aiResponse = String(outputObj.result)
                            else if (outputObj.output) aiResponse = String(outputObj.output)
                            else aiResponse = outputStr
                          } else {
                            aiResponse = outputStr
                          }
                        } catch (parseError) {
                          console.error('⚠️ JSON解析失败，使用原始字符串:', parseError)
                          aiResponse = outputStr
                        }
                      }
                    } else {
                      // output不是对象，直接使用
                      aiResponse = String(data.output).trim()
                      console.log('✅ 直接使用非对象output:', aiResponse)
                    }
                  } else if (data.result) {
                    console.log('⚠️ 没有output，尝试使用result字段')
                    aiResponse = String(data.result).trim()
                    console.log('📤 使用result:', aiResponse)
                  } else {
                    console.log('❌ 没有找到output或result字段')
                    console.log('🔍 可用字段:', Object.keys(data))
                    aiResponse = '抱歉，服务器返回了无效的响应格式。😔'
                  }
                } catch (parseError) {
                  console.error('❌ 响应解析错误:', parseError)
                  // 尝试使用整个数据对象作为字符串
                  aiResponse = JSON.stringify(data)
                  console.log('⚠️ 使用整个数据对象作为字符串:', aiResponse)
                }
              } else {
                console.log('❌ data不是有效对象')
                aiResponse = '抱歉，服务器返回了无效的数据格式。😔'
              }
              
              console.log('🎯 解析完成，最终AI响应:', aiResponse)
              console.log('🎯 AI响应类型:', typeof aiResponse)
              console.log('🎯 AI响应长度:', aiResponse.length)
              
              // 强制确保aiResponse是字符串类型
              if (typeof aiResponse !== 'string') {
                console.log('⚠️ aiResponse不是字符串，强制转换:', typeof aiResponse)
                aiResponse = String(aiResponse)
              }
              
              // 再次验证响应有效性
              if (!aiResponse || aiResponse === '[object Object]' || aiResponse === 'undefined' || aiResponse === 'null' || aiResponse.trim() === '') {
                console.log('❌ AI响应无效或为空，使用默认消息')
                aiResponse = '抱歉，我无法生成回复，请重试。😔'
              }
              
              console.log('🎯 最终确认的AI响应 (字符串):', aiResponse)
              console.log('🎯 字符串长度:', aiResponse.length)
              
              // 创建流式消息（如果尚未创建）
              if (!streamingMessage) {
                streamingMessage = {
                  id: Date.now().toString(),
                  content: '',
                  role: 'assistant',
                  timestamp: new Date(),
                  model: selectedModel.id
                }
                
                // 添加AI响应消息到当前会话
                if (updatedSession) {
                  // 再次确认会话ID是否一致
                  if (currentSession?.id !== currentSessionId) {
                    console.warn('⚠️ 添加AI响应前会话ID已变化，从', currentSessionId, '变为', currentSession?.id)
                    // 如果会话ID已变，尝试在当前会话中添加消息
                    if (currentSession) {
                      const updatedMessages = [...currentSession.messages, streamingMessage]
                      const newUpdatedSession = { ...currentSession, messages: updatedMessages, lastMessage: new Date() }
                      
                      setCurrentSession(newUpdatedSession)
                      setChatSessions(prev => 
                        prev.map(s => s.id === currentSession.id ? newUpdatedSession : s)
                      )
                    }
                  } else {
                    // 会话ID一致，正常添加消息
                    const updatedMessages = [...updatedSession.messages, streamingMessage]
                    updatedSession = { ...updatedSession, messages: updatedMessages, lastMessage: new Date() }
                    
                    setCurrentSession(updatedSession)
                    setChatSessions(prev => 
                      prev.map(s => s.id === updatedSession!.id ? updatedSession! : s)
                    )
                  }
                }
              }
              
              if (aiResponse && streamingMessage) {
                try {
                  // 实现流式效果 - 逐字显示
                  await simulateStreamingResponse(aiResponse, streamingMessage)
                  setIsLoading(false)
                  return // 成功处理API响应，直接返回
                } catch (streamError) {
                  console.error('❌ 流式响应错误:', streamError)
                  // 如果流式显示失败，直接设置完整消息
                  if (currentSession && streamingMessage) {
                    const updatedMessages = currentSession.messages.map(msg => 
                      msg.id === streamingMessage?.id 
                        ? { ...msg, content: aiResponse }
                        : msg
                    )
                    const updatedSession = { ...currentSession, messages: updatedMessages, lastMessage: new Date() }
                    
                    setCurrentSession(updatedSession)
                    setChatSessions(prev => 
                      prev.map(s => s.id === currentSession.id ? updatedSession : s)
                    )
                  }
                }
              }
            } catch (responseError) {
              console.error('❌ 处理API响应时出错:', responseError)
              
              // 确保即使出错也能显示一个回复
              const errorMessage: Message = {
                id: Date.now().toString(),
                content: '抱歉，处理API响应时出错。请重试。😔',
                role: 'assistant',
                timestamp: new Date(),
                model: selectedModel.id
              }
              
              if (currentSession) {
                const updatedMessages = [...currentSession.messages, errorMessage]
                const updatedSession = { ...currentSession, messages: updatedMessages, lastMessage: new Date() }
                
                setCurrentSession(updatedSession)
                setChatSessions(prev => 
                  prev.map(s => s.id === currentSession.id ? updatedSession : s)
                )
              }
            }
          } else {
            const errorText = await response.text()
            console.error('❌ RunPod API错误:', response.status, errorText)
            
            // 添加API错误消息
            const errorMessage: Message = {
              id: Date.now().toString(),
              content: `抱歉，API请求失败 (${response.status}): ${errorText || '未知错误'}`,
              role: 'assistant',
              timestamp: new Date(),
              model: selectedModel.id
            }
            
            if (currentSession) {
              const updatedMessages = [...currentSession.messages, errorMessage]
              const updatedSession = { ...currentSession, messages: updatedMessages, lastMessage: new Date() }
              
              setCurrentSession(updatedSession)
              setChatSessions(prev => 
                prev.map(s => s.id === currentSession.id ? updatedSession : s)
              )
            }
          }
        } catch (apiError) {
          console.error('❌ RunPod API调用异常:', apiError)
        }
      }

      // 如果API不可用，使用模拟回复
      console.log('🤖 使用模拟AI响应')
      
      // 模拟AI思考时间
      await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000))
      
      // 生成模拟的AI回复（带表情符号）
      const simulatedResponses = [
        `好的，关于"${userInput}"这个问题，让我想想... 🤔`,
        `我理解您询问"${userInput}"的意思，这是我的想法： 💭`,
        `关于"${userInput}"，我可以分享一些见解： ✨`,
        `这是个很好的话题！关于"${userInput}"，以下是我的想法： 🎯`,
        `感谢您的问题"${userInput}"，这是我的观点： 📝`
      ]
      
      const responseBodies = [
        "这是一个复杂的话题，涉及多个方面。需要考虑用户体验、技术实现和整体系统设计等关键因素。🔧",
        "有几种方法可以考虑，每种都有其优势和潜在挑战，我们应该仔细评估。⚖️",
        "这需要一个平衡的方法，既要考虑当前的功能需求，也要考虑未来的可扩展性。🚀",
        "最有效的解决方案可能是结合现代最佳实践和经过验证的方法论。💡",
        "这是一个需要仔细规划和迭代开发才能取得优秀结果的领域。🎨"
      ]
      
      const responseEndings = [
        "您希望我详细解释某个特定方面吗？🤗",
        "您对这种方法有什么想法？💬", 
        "有什么特定的领域您想进一步探讨吗？🔍",
        "这有助于回答您的问题吗？✅",
        "如果您需要更多细节，请告诉我。📚"
      ]
      
      const randomIntro = simulatedResponses[Math.floor(Math.random() * simulatedResponses.length)]
      const randomBody = responseBodies[Math.floor(Math.random() * responseBodies.length)]
      const randomEnding = responseEndings[Math.floor(Math.random() * responseEndings.length)]
      
      const simulatedResponse = `${randomIntro}\n\n${randomBody}\n\n${randomEnding}`

      // 如果没有创建流式消息，创建一个
      if (!streamingMessage) {
        streamingMessage = {
          id: Date.now().toString(),
          content: '',
          role: 'assistant',
          timestamp: new Date(),
          model: selectedModel.id
        }

        // 添加AI响应消息到当前会话
        if (updatedSession) {
          const updatedMessages = [...updatedSession.messages, streamingMessage]
          updatedSession = { ...updatedSession, messages: updatedMessages, lastMessage: new Date() }
          
          setCurrentSession(updatedSession)
          setChatSessions(prev => 
            prev.map(s => s.id === updatedSession!.id ? updatedSession! : s)
          )
        }
      }

      // 模拟流式响应
      await simulateStreamingResponse(simulatedResponse, streamingMessage)
      
    } catch (error) {
      console.error('💥 生成响应时出错:', error)
      const errorMessage: Message = {
        id: Date.now().toString(),
        content: `抱歉，我遇到了一个错误：${error instanceof Error ? error.message : '未知错误'} 😔`,
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
    try {
      const sessionIdAtStart = currentSession?.id;
      console.log('🔄 开始流式显示，会话ID:', sessionIdAtStart, '消息ID:', messageToUpdate.id);
      const words = fullResponse.split(' ');
      let currentContent = '';
      for (let i = 0; i < words.length; i++) {
        currentContent += (i > 0 ? ' ' : '') + words[i];
        if (currentSession && (i % 2 === 0 || i === words.length - 1)) {
          try {
            if (currentSession.id !== sessionIdAtStart) {
              console.warn('⚠️ 会话ID已变化，从', sessionIdAtStart, '变为', currentSession.id);
            }
            const messageExists = currentSession.messages.some(msg => msg.id === messageToUpdate.id);
            if (!messageExists) {
              console.warn('⚠️ 消息ID不存在于当前会话中:', messageToUpdate.id);
              const newMessage = { ...messageToUpdate, content: currentContent };
              const updatedMessages = [...currentSession.messages, newMessage];
              const updatedSession = { ...currentSession, messages: updatedMessages, lastMessage: new Date() };
              setCurrentSession(updatedSession);
              if (i === words.length - 1) {
                setChatSessions(prev => prev.map(s => s.id === currentSession.id ? updatedSession : s));
              }
              continue;
            }
            const updatedMessages = currentSession.messages.map(msg => msg.id === messageToUpdate.id ? { ...msg, content: currentContent } : msg);
            const updatedSession = { ...currentSession, messages: updatedMessages, lastMessage: new Date() };
            setCurrentSession(updatedSession);
            if (i === words.length - 1) {
              setChatSessions(prev => prev.map(s => s.id === currentSession.id ? updatedSession : s));
            }
          } catch (updateError) {
            console.error('❌ 更新消息内容失败:', updateError);
          }
        }
        await new Promise(resolve => setTimeout(resolve, 15 + Math.random() * 25));
      }
      
      // 延迟自动保存，避免与UI渲染冲突
      if (autoSave && currentSession && currentSession.messages.length >= 2) {
        setTimeout(async () => {
          try {
            if (currentSession?.id !== sessionIdAtStart) {
              console.warn('⚠️ 自动保存时会话ID已变化，取消保存');
              return;
            }
            setSaveStatus('saving');
            console.log('💾 自动保存聊天记录到R2...');
            const saveResult = await autoSaveChatHistory(currentSession.messages, {
              model: selectedModel.id,
              persona: 'default',
              temperature: 0.7,
              timestamp: new Date().toISOString()
            });
            if (saveResult.success) {
              console.log('✅ 聊天记录已保存到R2:', saveResult.chatId);
              setLastSaveTime(new Date());
              setSaveStatus('storage' in saveResult && saveResult.storage === 'local' ? 'local' : 'saved');
            } else {
              console.error('❌ 聊天记录保存失败:', 'error' in saveResult ? saveResult.error : 'Unknown error');
              setSaveStatus('error');
            }
          } catch (error) {
            console.error('❌ 自动保存异常，但继续显示消息:', error);
            setSaveStatus('error');
          }
        }, 2000); // 延长到2秒
      }
    } catch (streamingError) {
      console.error('❌ 流式响应处理错误:', streamingError);
      if (currentSession) {
        try {
          const messageExists = currentSession.messages.some(msg => msg.id === messageToUpdate.id);
          if (messageExists) {
            const updatedMessages = currentSession.messages.map(msg => msg.id === messageToUpdate.id ? { ...msg, content: fullResponse } : msg);
            const updatedSession = { ...currentSession, messages: updatedMessages, lastMessage: new Date() };
            setCurrentSession(updatedSession);
            setChatSessions(prev => prev.map(s => s.id === currentSession.id ? updatedSession : s));
          } else {
            const newMessage = { ...messageToUpdate, content: fullResponse };
            const updatedMessages = [...currentSession.messages, newMessage];
            const updatedSession = { ...currentSession, messages: updatedMessages, lastMessage: new Date() };
            setCurrentSession(updatedSession);
            setChatSessions(prev => prev.map(s => s.id === currentSession.id ? updatedSession : s));
          }
        } catch (finalUpdateError) {
          console.error('❌ 最终更新消息失败:', finalUpdateError);
        }
      }
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading || !currentSession) return

    const userInput = inputValue.trim()
    setInputValue('')
    
    // 添加用户消息到当前会话
    const userMessage: Message = {
      id: Date.now().toString(),
      content: userInput,
      role: 'user',
      timestamp: new Date()
    }
    
    // 更新会话，添加用户消息
    const updatedMessages = [...currentSession.messages, userMessage]
    const updatedSession = { ...currentSession, messages: updatedMessages, lastMessage: new Date() }
    
    setCurrentSession(updatedSession)
    setChatSessions(prev => prev.map(s => s.id === currentSession.id ? updatedSession : s))
    
    // 调用generateResponse生成AI响应
    await generateResponse(userInput, updatedMessages)
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
            {chatSessions.map((session) => (
              <button
                key={session.id}
                onClick={() => {
                  setCurrentSession(session)
                }}
                className={`w-full text-left p-3 rounded-lg transition-colors ${
                  currentSession?.id === session.id
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium truncate">
                      {session.title && session.title !== 'New Chat' ? session.title : '新对话'}
                    </h3>
                    <p className="text-sm opacity-75 truncate">
                      {session.messages.length > 0 
                        ? `${session.messages.length} 条消息` 
                        : '开始对话...'}
                    </p>
                    <p className="text-xs opacity-60">
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
                {/* 存储状态指示器 */}
                {saveStatus !== 'none' && (
                  <div className={`flex items-center gap-1 text-xs px-2 py-1 rounded-lg ${
                    saveStatus === 'saving' ? 'bg-yellow-100 text-yellow-700' :
                    saveStatus === 'saved' ? 'bg-green-100 text-green-700' :
                    saveStatus === 'local' ? 'bg-blue-100 text-blue-700' :
                    saveStatus === 'error' ? 'bg-red-100 text-red-700' : ''
                  }`}>
                    {saveStatus === 'saving' && '⏳ 保存中...'}
                    {saveStatus === 'saved' && '✅ 已保存到云端'}
                    {saveStatus === 'local' && '📱 已保存到本地'}
                    {saveStatus === 'error' && '❌ 保存失败'}
                  </div>
                )}
                
                {/* 自动保存开关 */}
                <label className="flex items-center gap-2 text-sm text-gray-600">
                  <input
                    type="checkbox"
                    checked={autoSave}
                    onChange={(e) => setAutoSave(e.target.checked)}
                    className="rounded"
                  />
                  自动保存
                </label>
                
                {/* 手动保存按钮 */}
                {currentSession.messages.length >= 2 && (
                  <button
                    onClick={async () => {
                      try {
                        setSaveStatus('saving')
                        const saveResult = await autoSaveChatHistory(currentSession.messages, {
                          model: selectedModel.id,
                          persona: 'default',
                          temperature: 0.7
                        })
                        if (saveResult.success) {
                          setLastSaveTime(new Date())
                          setSaveStatus('storage' in saveResult && saveResult.storage === 'local' ? 'local' : 'saved')
                          alert('✅ 聊天记录已保存')
                        } else {
                          setSaveStatus('error')
                          alert('❌ 保存失败: ' + ('error' in saveResult ? saveResult.error : 'Unknown error'))
                        }
                      } catch (error) {
                        setSaveStatus('error')
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