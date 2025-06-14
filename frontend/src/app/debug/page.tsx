'use client'

import { useState } from 'react'

export default function DebugPage() {
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)

  const testApiKey = async () => {
    setLoading(true)
    setResult('Testing...')

    try {
      // 直接硬编码API Key进行测试
      const API_KEY = 'rpa_YT0BFBFZYAZMQHR231H4DOKQEOAJXSMVIBDYN4ZQ1tdxlb'
      const ENDPOINT = 'https://api.runpod.ai/v2/4cx6jtjdx6hdhr/runsync'

      console.log('🔑 Debug API Key:', API_KEY ? `${API_KEY.substring(0, 15)}...` : 'NULL')
      console.log('🌐 Debug Endpoint:', ENDPOINT)

      const response = await fetch(ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${API_KEY}`
        },
        body: JSON.stringify({
          input: {
            prompt: 'Debug test from new page'
          }
        })
      })

      console.log('📡 Response status:', response.status)

      if (response.ok) {
        const data = await response.json()
        console.log('📦 Response data:', data)
        
        setResult(`✅ Success!\n\nStatus: ${response.status}\nOutput: ${data.output}\n\nFull Response:\n${JSON.stringify(data, null, 2)}`)
      } else {
        const errorText = await response.text()
        setResult(`❌ Error!\n\nStatus: ${response.status}\nError: ${errorText}`)
      }
    } catch (error) {
      console.error('❌ Error:', error)
      setResult(`❌ Exception!\n\nError: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">🐛 Debug API Key Test</h1>
        
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">API Key Debug Test</h2>
          
          <button
            onClick={testApiKey}
            disabled={loading}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed mb-4"
          >
            {loading ? 'Testing...' : 'Test API Key'}
          </button>
          
          <div className="bg-gray-100 p-4 rounded-md">
            <h3 className="font-medium mb-2">Test Result:</h3>
            <pre className="text-sm overflow-auto max-h-96 whitespace-pre-wrap">
              {result || 'Click the button to test API Key...'}
            </pre>
          </div>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h3 className="text-lg font-medium text-yellow-800 mb-2">Debug Info</h3>
          <p className="text-sm text-yellow-700">
            This page tests the API Key directly without environment variables.
            Check the browser console for detailed logs.
          </p>
        </div>
      </div>
    </div>
  )
} 