import React, { useState } from 'react'
import { AlertCircle, CheckCircle, Loader2, Server, Settings } from 'lucide-react'

export default function ComfyUIConnectionModal({ isOpen, onConnectionSuccess, onOpenSettings }) {
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [errorMessage, setErrorMessage] = useState(null)

  if (!isOpen) return null

  const handleTestConnection = async () => {
    setIsTesting(true)
    setTestResult(null)
    setErrorMessage(null)

    try {
      const response = await fetch('http://127.0.0.1:8000/comfyui/test-connection')
      const data = await response.json()

      if (data.success) {
        setTestResult({
          success: true,
          message: data.message || 'ComfyUI connection successful!'
        })
      } else {
        setTestResult({
          success: false,
          message: data.message || 'Failed to connect to ComfyUI'
        })
        setErrorMessage(data.error || data.message)
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: 'Failed to test connection'
      })
      setErrorMessage(error.message || 'Unknown error occurred')
    } finally {
      setIsTesting(false)
    }
  }

  const handleClose = () => {
    if (testResult && testResult.success) {
      onConnectionSuccess()
    }
  }

  const handleOpenSettings = () => {
    if (onOpenSettings) {
      onOpenSettings()
    }
  }

  return (
    <div 
      className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[9999]"
      style={{ pointerEvents: 'auto' }}
    >
      <div 
        className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md mx-4 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-900/20 rounded-lg">
              <Server className="h-6 w-6 text-red-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-200">ComfyUI Connection Required</h3>
          </div>
        </div>

        {/* Content */}
        <div className="space-y-4">
          <p className="text-sm text-gray-300">
            The application requires a connection to ComfyUI server to function. Please ensure ComfyUI is running and click "Test Connection" to verify.
          </p>

          {/* Test Result Display */}
          {testResult && (
            <div className={`p-4 rounded-lg border ${
              testResult.success 
                ? 'bg-green-900/20 border-green-600/30' 
                : 'bg-red-900/20 border-red-600/30'
            }`}>
              <div className="flex items-center gap-3">
                {testResult.success ? (
                  <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
                )}
                <p className={`text-sm font-medium ${
                  testResult.success ? 'text-green-300' : 'text-red-300'
                }`}>
                  {testResult.message}
                </p>
              </div>
              {errorMessage && !testResult.success && (
                <p className="text-xs text-red-400 mt-2 ml-8">
                  {errorMessage}
                </p>
              )}
            </div>
          )}

          {/* Instructions */}
          <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
            <p className="text-xs text-gray-400 mb-2">To start ComfyUI:</p>
            <ol className="text-xs text-gray-300 space-y-1 list-decimal list-inside">
              <li>Open a terminal/command prompt</li>
              <li>Navigate to your ComfyUI directory</li>
              <li>Start ComfyUI either by running the script file or with python: <code className="bg-gray-900 px-1 rounded">python main.py</code></li>
              <li>Wait for the server to start (usually on port 8188)</li>
            </ol>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={handleOpenSettings}
              className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg transition-colors"
            >
              <Settings className="h-4 w-4" />
              Settings
            </button>
            
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleTestConnection}
                disabled={isTesting || (testResult && testResult.success)}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-700 hover:bg-blue-600 disabled:bg-gray-700 disabled:text-gray-500 text-gray-200 rounded-lg transition-colors"
              >
                {isTesting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Testing...
                  </>
                ) : (
                  <>
                    <Server className="h-4 w-4" />
                    Test Connection
                  </>
                )}
              </button>
              
              {testResult && testResult.success && (
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-4 py-2 text-sm bg-green-700 hover:bg-green-600 text-gray-200 rounded-lg transition-colors"
                >
                  Close
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}








