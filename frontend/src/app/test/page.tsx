'use client'

import { useState } from 'react'

export default function TestPage() {
  const [testResult, setTestResult] = useState('')
  const [loading, setLoading] = useState(false)
  const [apiKey, setApiKey] = useState('rpa_YT0BFBFZYAZM90qZoMzEGfv4rNRGlxCEzJpKFFEWyQXOe')
  const [endpoint, setEndpoint] = useState('https://api.runpod.ai/v2/4cx6jtjdx6hdhr/runsync')
  const [prompt, setPrompt] = useState('Hello, how are you today?')

  const testRunPodAPI = async () => {
    setLoading(true)
    setTestResult('Testing...')

    try {
      console.log('Testing RunPod API with:', {
        endpoint,
        apiKey: apiKey ? `${apiKey.substring(0, 10)}...` : 'NOT SET',
        prompt
      })

      const requestPayload = {
        input: {
          model_path: "/runpod-volume/text_models/L3.2-8X3B.gguf",
          prompt: `<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nYou are a helpful, harmless, and honest assistant.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n${prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n`,
          max_tokens: 150,
          temperature: 0.7,
          top_p: 0.9,
          repeat_penalty: 1.05,
          stop: ["<|eot_id|>", "<|end_of_text|>", "<|start_header_id|>"],
          stream: false
        }
      }

      console.log('Request Payload:', requestPayload)

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestPayload)
      })

      console.log('Response Status:', response.status)
      console.log('Response Headers:', Object.fromEntries(response.headers.entries()))

      const responseText = await response.text()
      console.log('Raw Response:', responseText)

      let data
      try {
        data = JSON.parse(responseText)
      } catch (e) {
        setTestResult(`❌ Invalid JSON Response:\n${responseText}`)
        setLoading(false)
        return
      }

      if (response.ok) {
        if (data.status === "COMPLETED" && data.output?.text) {
          const aiResponse = data.output.text.replace(requestPayload.input.prompt, "").trim()
          setTestResult(`✅ Success!\n\nStatus: ${data.status}\nResponse: ${aiResponse}\n\nFull Response: ${JSON.stringify(data, null, 2)}`)
        } else {
          setTestResult(`⚠️ Unexpected Response Format:\n${JSON.stringify(data, null, 2)}`)
        }
      } else {
        setTestResult(`❌ HTTP Error ${response.status}:\n${JSON.stringify(data, null, 2)}`)
      }

    } catch (error) {
      console.error('Test Error:', error)
      setTestResult(`❌ Network Error:\n${error instanceof Error ? error.message : String(error)}`)
    }

    setLoading(false)
  }

  const testEnvironmentVariables = () => {
    const envInfo = {
      'NEXT_PUBLIC_RUNPOD_API_KEY': process.env.NEXT_PUBLIC_RUNPOD_API_KEY || 'NOT SET',
      'RUNPOD_API_KEY': process.env.RUNPOD_API_KEY || 'NOT SET',
      'NEXT_PUBLIC_RUNPOD_ENDPOINT_ID': process.env.NEXT_PUBLIC_RUNPOD_ENDPOINT_ID || 'NOT SET',
      'RUNPOD_ENDPOINT_ID': process.env.RUNPOD_ENDPOINT_ID || 'NOT SET',
      'NEXT_PUBLIC_VITE_API_BASE_URL': process.env.NEXT_PUBLIC_VITE_API_BASE_URL || 'NOT SET',
      'VITE_API_BASE_URL': process.env.VITE_API_BASE_URL || 'NOT SET',
      'All env keys containing RUNPOD or VITE': Object.keys(process.env).filter(key => 
        key.includes('RUNPOD') || key.includes('VITE')
      ),
      'Process env type': typeof process.env,
      'Process env keys count': Object.keys(process.env).length
    }

    console.log('Environment Variables:', envInfo)
    setTestResult(`Environment Variables:\n${JSON.stringify(envInfo, null, 2)}`)
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">RunPod API 测试页面</h1>
        
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">API 配置</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                API Key:
              </label>
              <input
                type="text"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="rpa_..."
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Endpoint:
              </label>
              <input
                type="text"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                测试提示词:
              </label>
              <input
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">测试按钮</h2>
          
          <div className="space-x-4">
            <button
              onClick={testRunPodAPI}
              disabled={loading}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '测试中...' : '测试 RunPod API'}
            </button>
            
            <button
              onClick={testEnvironmentVariables}
              className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              检查环境变量
            </button>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">测试结果</h2>
          
          <pre className="bg-gray-100 p-4 rounded-md text-sm overflow-auto max-h-96 whitespace-pre-wrap">
            {testResult || '点击上面的按钮开始测试...'}
          </pre>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mt-6">
          <h3 className="text-lg font-medium text-yellow-800 mb-2">使用说明</h3>
          <ul className="text-sm text-yellow-700 space-y-1">
            <li>• 首先点击"检查环境变量"看看环境变量是否正确读取</li>
            <li>• 然后点击"测试 RunPod API"直接测试API连接</li>
            <li>• 可以修改API Key、Endpoint和提示词进行测试</li>
            <li>• 查看浏览器开发者工具的Console获取更多调试信息</li>
          </ul>
        </div>
      </div>
    </div>
  )
} 