import React, { useState, useEffect } from 'react'
import { Settings as SettingsIcon, FolderOpen, CheckCircle, AlertCircle, Server, Bot } from 'lucide-react'
import { settingsManager } from '../utils/settingsManager.js'
import ErrorModal from '../components/ErrorModal.jsx'

export default function Settings() {
  const [settings, setSettings] = useState({})
  const [isSelectingFolder, setIsSelectingFolder] = useState(false)
  const [isSelectingOutputFolder, setIsSelectingOutputFolder] = useState(false)
  const [comfyuiServerUrl, setComfyuiServerUrl] = useState('http://127.0.0.1:8188')
  const [errorModal, setErrorModal] = useState({ isOpen: false, title: '', message: '' })

  useEffect(() => {
    // Load initial settings
    setSettings(settingsManager.getSettings())
    
    // Sync settings from backend preferences
    const syncFromBackend = async () => {
      try {
        const backendPrefs = await fetch('http://127.0.0.1:8000/preferences').then(r => r.json())
        
        // Sync ComfyUI server URL
        const localPrefs = JSON.parse(localStorage.getItem('userPreferences') || '{}')
        let needsBackendSync = false
        
        if (backendPrefs.comfyUiServer) {
          setComfyuiServerUrl(backendPrefs.comfyUiServer)
          // Also save to localStorage for backward compatibility
          localPrefs.comfyUiServer = backendPrefs.comfyUiServer
          localStorage.setItem('userPreferences', JSON.stringify(localPrefs))
        } else if (localPrefs.comfyUiServer) {
          // Backend doesn't have it but localStorage does - sync to backend
          setComfyuiServerUrl(localPrefs.comfyUiServer)
          backendPrefs.comfyUiServer = localPrefs.comfyUiServer
          needsBackendSync = true
        }
        
        // Sync ComfyUI path
        const currentPath = settingsManager.getComfyUIPath()
        if (backendPrefs.comfyuiPath) {
          // Backend has it - sync to frontend if different
          if (currentPath !== backendPrefs.comfyuiPath) {
            settingsManager.setComfyUIPath(backendPrefs.comfyuiPath, {
              isValid: true,
              message: 'Synced from backend'
            })
          }
        } else if (currentPath) {
          // Frontend has it but backend doesn't - sync to backend
          backendPrefs.comfyuiPath = currentPath
          needsBackendSync = true
        }
        
        // Sync to backend if needed
        if (needsBackendSync) {
          await fetch('http://127.0.0.1:8000/preferences', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(backendPrefs)
          })
        }
        
        // Sync output folder
        if (backendPrefs.aiWorkflowsOutputFolder) {
          const currentFolder = settingsManager.getAIWorkflowsOutputFolder()
          if (currentFolder !== backendPrefs.aiWorkflowsOutputFolder) {
            settingsManager.setAIWorkflowsOutputFolder(backendPrefs.aiWorkflowsOutputFolder)
          }
        }
      } catch (error) {
        console.error('Error syncing settings from backend:', error)
      }
    }
    syncFromBackend()

    // Listen for settings updates
    const handleSettingsUpdate = (event) => {
      setSettings(event.detail.settings)
    }

    window.addEventListener('settingsUpdated', handleSettingsUpdate)
    
    return () => {
      window.removeEventListener('settingsUpdated', handleSettingsUpdate)
    }
  }, [])

  const handleComfyuiServerUrlChange = async (url) => {
    setComfyuiServerUrl(url)
    // Save to localStorage
    const prefs = JSON.parse(localStorage.getItem('userPreferences') || '{}')
    prefs.comfyUiServer = url
    localStorage.setItem('userPreferences', JSON.stringify(prefs))
    
    // Sync to backend preferences
    try {
      const backendPrefs = await fetch('http://127.0.0.1:8000/preferences').then(r => r.json())
      backendPrefs.comfyUiServer = url
      await fetch('http://127.0.0.1:8000/preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(backendPrefs)
      })
    } catch (error) {
      console.error('Error syncing ComfyUI server URL to backend:', error)
    }
  }

  const handleSelectComfyUIFolder = async () => {
    setIsSelectingFolder(true)
    
    try {
      // Use Electron's dialog if available (for desktop app)
      if (window.electronAPI && window.electronAPI.selectFolder) {
        const result = await window.electronAPI.selectFolder()
        if (result && !result.canceled && result.filePaths && result.filePaths.length > 0) {
          const selectedPath = result.filePaths[0]
          
          // Validate the selected folder
          const validationResult = await window.electronAPI.validateComfyUIFolder(selectedPath)
          
          // Only set the path if validation passes
          if (validationResult.isValid) {
            settingsManager.setComfyUIPath(selectedPath, validationResult)
            
            // Sync to backend preferences
            try {
              const prefs = await fetch('http://127.0.0.1:8000/preferences').then(r => r.json())
              prefs.comfyuiPath = selectedPath
              await fetch('http://127.0.0.1:8000/preferences', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(prefs)
              })
            } catch (error) {
              console.error('Error syncing ComfyUI path to backend:', error)
            }
          } else {
            // Show styled error modal for invalid folder
            setErrorModal({
              isOpen: true,
              title: 'Invalid ComfyUI Folder',
              message: validationResult.message
            })
          }
        }
      } else {
        // Fallback for web version - use input with directory attribute
        const input = document.createElement('input')
        input.type = 'file'
        input.webkitdirectory = true
        input.directory = true
        
        input.onchange = async (event) => {
          const files = event.target.files
          if (files && files.length > 0) {
            // Get the directory path from the first file
            const path = files[0].webkitRelativePath.split('/')[0]
            // For web version, we can't validate the folder structure
            // So we'll just set it and let the user know validation isn't available
            settingsManager.setComfyUIPath(path, {
              isValid: true,
              message: 'Folder selected (validation not available in web version)'
            })
            
            // Sync to backend preferences
            try {
              const prefs = await fetch('http://127.0.0.1:8000/preferences').then(r => r.json())
              prefs.comfyuiPath = path
              await fetch('http://127.0.0.1:8000/preferences', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(prefs)
              })
            } catch (error) {
              console.error('Error syncing ComfyUI path to backend:', error)
            }
          }
        }
        
        input.click()
      }
    } catch (error) {
      console.error('Error selecting ComfyUI folder:', error)
    } finally {
      setIsSelectingFolder(false)
    }
  }

  const getComfyUIStatus = () => {
    if (settings.comfyuiPath && settings.comfyuiValidation && settings.comfyuiValidation.isValid) {
      return {
        status: 'connected',
        icon: CheckCircle,
        color: 'text-green-400',
        bgColor: 'bg-green-600/20',
        borderColor: 'border-green-600/30',
        message: 'ComfyUI folder configured and validated'
      }
    } else if (settings.comfyuiPath) {
      return {
        status: 'configured_but_invalid',
        icon: AlertCircle,
        color: 'text-red-400',
        bgColor: 'bg-red-600/20',
        borderColor: 'border-red-600/30',
        message: 'ComfyUI folder configured but validation failed'
      }
    } else {
      return {
        status: 'not_configured',
        icon: AlertCircle,
        color: 'text-yellow-400',
        bgColor: 'bg-yellow-600/20',
        borderColor: 'border-yellow-600/30',
        message: 'ComfyUI folder not configured'
      }
    }
  }

  const handleSelectOutputFolder = async () => {
    setIsSelectingOutputFolder(true)
    
    try {
      // Use Electron's dialog if available (for desktop app)
      if (window.electronAPI && window.electronAPI.selectFolder) {
        const result = await window.electronAPI.selectFolder()
        if (result && !result.canceled && result.filePaths && result.filePaths.length > 0) {
          const selectedPath = result.filePaths[0]
          settingsManager.setAIWorkflowsOutputFolder(selectedPath)
          
          // Sync to backend preferences
          try {
            const prefs = await fetch('http://127.0.0.1:8000/preferences').then(r => r.json())
            prefs.aiWorkflowsOutputFolder = selectedPath
            await fetch('http://127.0.0.1:8000/preferences', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(prefs)
            })
          } catch (error) {
            console.error('Error syncing output folder to backend:', error)
          }
        }
      } else {
        // Fallback for web version - use input with directory attribute
        const input = document.createElement('input')
        input.type = 'file'
        input.webkitdirectory = true
        input.directory = true
        
        input.onchange = async (event) => {
          const files = event.target.files
          if (files && files.length > 0) {
            // Get the directory path from the first file
            const path = files[0].webkitRelativePath.split('/')[0]
            settingsManager.setAIWorkflowsOutputFolder(path)
            
            // Sync to backend preferences
            try {
              const prefs = await fetch('http://127.0.0.1:8000/preferences').then(r => r.json())
              prefs.aiWorkflowsOutputFolder = path
              await fetch('http://127.0.0.1:8000/preferences', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(prefs)
              })
            } catch (error) {
              console.error('Error syncing output folder to backend:', error)
            }
          }
        }
        
        input.click()
      }
    } catch (error) {
      console.error('Error selecting output folder:', error)
      setErrorModal({
        isOpen: true,
        title: 'Error Selecting Folder',
        message: `Failed to select output folder: ${error.message}`
      })
    } finally {
      setIsSelectingOutputFolder(false)
    }
  }

  const getOutputFolderStatus = () => {
    if (settings.aiWorkflowsOutputFolder) {
      return {
        status: 'configured',
        icon: CheckCircle,
        color: 'text-green-400',
        bgColor: 'bg-green-600/20',
        borderColor: 'border-green-600/30',
        message: 'AI Workflows output folder configured'
      }
    } else {
      return {
        status: 'not_configured',
        icon: AlertCircle,
        color: 'text-yellow-400',
        bgColor: 'bg-yellow-600/20',
        borderColor: 'border-yellow-600/30',
        message: 'AI Workflows output folder not configured'
      }
    }
  }

  const comfyuiStatus = getComfyUIStatus()
  const StatusIcon = comfyuiStatus.icon
  const outputFolderStatus = getOutputFolderStatus()
  const OutputFolderStatusIcon = outputFolderStatus.icon

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-600/20 rounded-lg">
            <SettingsIcon className="h-6 w-6 text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-100">Settings</h1>
            <p className="text-gray-400">Configure your application preferences and integrations</p>
          </div>
        </div>
      </div>

      {/* ComfyUI Configuration Section */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-purple-600/20 rounded-lg">
            <Server className="h-5 w-5 text-purple-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-200">ComfyUI Integration</h2>
            <p className="text-sm text-gray-400">Configure ComfyUI folder for background processing</p>
          </div>
        </div>

        <div className="space-y-4">
          {/* Status Display */}
          <div className={`flex items-center gap-3 p-4 rounded-lg border ${comfyuiStatus.bgColor} ${comfyuiStatus.borderColor}`}>
            <StatusIcon className={`h-5 w-5 ${comfyuiStatus.color}`} />
            <div className="flex-1">
              <p className={`text-sm font-medium ${comfyuiStatus.color}`}>
                {comfyuiStatus.message}
              </p>
              {settings.comfyuiPath && (
                <p className="text-xs text-gray-400 mt-1 font-mono">
                  {settings.comfyuiPath}
                </p>
              )}
            </div>
          </div>

          {/* ComfyUI Server URL */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-300">
              ComfyUI Server URL
            </label>
            <div className="flex items-center gap-3">
              <input
                type="url"
                value={comfyuiServerUrl}
                onChange={(e) => handleComfyuiServerUrlChange(e.target.value)}
                placeholder="http://127.0.0.1:8188"
                className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-600 focus:border-transparent"
              />
              <button
                onClick={() => handleComfyuiServerUrlChange('http://127.0.0.1:8188')}
                className="px-3 py-2 text-gray-400 hover:text-gray-300 hover:bg-gray-700 rounded-lg font-medium transition-colors"
              >
                Reset
              </button>
            </div>
            <p className="text-xs text-gray-400">
              The URL where your ComfyUI server is running. Default is localhost:8188.
            </p>
          </div>

          {/* Folder Selection Button */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleSelectComfyUIFolder}
              disabled={isSelectingFolder}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg font-medium transition-colors"
            >
              <FolderOpen className="h-4 w-4" />
              {isSelectingFolder ? 'Selecting...' : settings.comfyuiPath ? 'Change ComfyUI Folder' : 'Select ComfyUI Folder'}
            </button>
            
            {settings.comfyuiPath && (
              <button
                onClick={async () => {
                  settingsManager.setComfyUIPath(null, null)
                  // Sync to backend preferences
                  try {
                    const prefs = await fetch('http://127.0.0.1:8000/preferences').then(r => r.json())
                    prefs.comfyuiPath = null
                    await fetch('http://127.0.0.1:8000/preferences', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify(prefs)
                    })
                  } catch (error) {
                    console.error('Error syncing ComfyUI path to backend:', error)
                  }
                }}
                className="px-3 py-2 text-gray-400 hover:text-red-400 hover:bg-red-600/20 rounded-lg font-medium transition-colors"
              >
                Clear
              </button>
            )}
          </div>

          {/* Help Text */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-300 mb-2">How to set up ComfyUI:</h4>
            <ol className="text-xs text-gray-400 space-y-1 list-decimal list-inside">
              <li>Download and install ComfyUI on your system</li>
              <li>Click "Select ComfyUI Folder" and choose the parent directory containing the ComfyUI folder</li>
              <li>The folder will be automatically validated for the ComfyUI subfolder and main.py file</li>
              <li>Only valid ComfyUI installations will be accepted</li>
              <li>The application will use this path to start ComfyUI in the background when needed</li>
            </ol>
          </div>
        </div>
      </div>

      {/* AI Workflows Output Folder Configuration Section */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-blue-600/20 rounded-lg">
            <Bot className="h-5 w-5 text-blue-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-200">AI Workflows Output Folder</h2>
            <p className="text-sm text-gray-400">Configure where generated videos from AI Workflows will be saved</p>
          </div>
        </div>

        <div className="space-y-4">
          {/* Status Display */}
          <div className={`flex items-center gap-3 p-4 rounded-lg border ${outputFolderStatus.bgColor} ${outputFolderStatus.borderColor}`}>
            <OutputFolderStatusIcon className={`h-5 w-5 ${outputFolderStatus.color}`} />
            <div className="flex-1">
              <p className={`text-sm font-medium ${outputFolderStatus.color}`}>
                {outputFolderStatus.message}
              </p>
              {settings.aiWorkflowsOutputFolder && (
                <p className="text-xs text-gray-400 mt-1 font-mono">
                  {settings.aiWorkflowsOutputFolder}
                </p>
              )}
            </div>
          </div>

          {/* Folder Selection Button */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleSelectOutputFolder}
              disabled={isSelectingOutputFolder}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg font-medium transition-colors"
            >
              <FolderOpen className="h-4 w-4" />
              {isSelectingOutputFolder ? 'Selecting...' : settings.aiWorkflowsOutputFolder ? 'Change Output Folder' : 'Select Output Folder'}
            </button>
            
            {settings.aiWorkflowsOutputFolder && (
              <button
                onClick={async () => {
                  settingsManager.setAIWorkflowsOutputFolder(null)
                  // Sync to backend preferences
                  try {
                    const prefs = await fetch('http://127.0.0.1:8000/preferences').then(r => r.json())
                    prefs.aiWorkflowsOutputFolder = null
                    await fetch('http://127.0.0.1:8000/preferences', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify(prefs)
                    })
                  } catch (error) {
                    console.error('Error syncing output folder to backend:', error)
                  }
                }}
                className="px-3 py-2 text-gray-400 hover:text-red-400 hover:bg-red-600/20 rounded-lg font-medium transition-colors"
              >
                Clear
              </button>
            )}
          </div>

          {/* Help Text */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-300 mb-2">About AI Workflows Output Folder:</h4>
            <ul className="text-xs text-gray-400 space-y-1 list-disc list-inside">
              <li>All videos generated by AI Workflows will be saved to this folder</li>
              <li>You must configure this folder before using AI Workflows</li>
              <li>The folder will be created automatically if it doesn't exist</li>
              <li>Make sure you have write permissions for the selected folder</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Error Modal */}
      <ErrorModal
        isOpen={errorModal.isOpen}
        onClose={() => setErrorModal({ isOpen: false, title: '', message: '' })}
        title={errorModal.title}
        message={errorModal.message}
      />

    </div>
  )
}


