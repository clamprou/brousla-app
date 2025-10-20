import React, { useState, useEffect } from 'react'
import { Settings as SettingsIcon, FolderOpen, CheckCircle, AlertCircle, Server } from 'lucide-react'
import { settingsManager } from '../utils/settingsManager.js'

export default function Settings() {
  const [settings, setSettings] = useState({})
  const [isSelectingFolder, setIsSelectingFolder] = useState(false)

  useEffect(() => {
    // Load initial settings
    setSettings(settingsManager.getSettings())

    // Listen for settings updates
    const handleSettingsUpdate = (event) => {
      setSettings(event.detail.settings)
    }

    window.addEventListener('settingsUpdated', handleSettingsUpdate)
    
    return () => {
      window.removeEventListener('settingsUpdated', handleSettingsUpdate)
    }
  }, [])

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
          } else {
            // Show error message for invalid folder
            alert(`Invalid ComfyUI folder: ${validationResult.message}`)
          }
        }
      } else {
        // Fallback for web version - use input with directory attribute
        const input = document.createElement('input')
        input.type = 'file'
        input.webkitdirectory = true
        input.directory = true
        
        input.onchange = (event) => {
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

  const comfyuiStatus = getComfyUIStatus()
  const StatusIcon = comfyuiStatus.icon

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
                onClick={() => settingsManager.setComfyUIPath(null, null)}
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
              <li>Click "Select ComfyUI Folder" and choose the main ComfyUI directory</li>
              <li>The folder will be automatically validated for required files (main.py and comfy folder)</li>
              <li>Only valid ComfyUI installations will be accepted</li>
              <li>The application will use this path to start ComfyUI in the background when needed</li>
            </ol>
          </div>
        </div>
      </div>

    </div>
  )
}


