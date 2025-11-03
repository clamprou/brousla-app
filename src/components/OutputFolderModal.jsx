import React, { useState, useCallback, useEffect } from 'react'
import { X, FolderOpen, AlertCircle } from 'lucide-react'
import { settingsManager } from '../utils/settingsManager.js'

export default function OutputFolderModal({ 
  isOpen, 
  onClose, 
  onFolderSelected,
  navigateBackOnClose = false
}) {
  const [isSelectingFolder, setIsSelectingFolder] = useState(false)

  const handleClose = useCallback(() => {
    if (navigateBackOnClose && window.getPreviousPage) {
      const previousPage = window.getPreviousPage()
      if (previousPage) {
        const ev = new CustomEvent('navigate', { detail: previousPage })
        window.dispatchEvent(ev)
      }
    }
    if (onClose) {
      onClose()
    }
  }, [navigateBackOnClose, onClose])

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') {
      handleClose()
    }
  }, [handleClose])

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
    }
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'unset'
    }
  }, [isOpen, handleKeyDown])

  if (!isOpen) return null

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      handleClose()
    }
  }

  const handleSelectFolder = async () => {
    setIsSelectingFolder(true)
    
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
          
          if (onFolderSelected) {
            onFolderSelected(selectedPath)
          } else {
            handleClose()
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
            
            if (onFolderSelected) {
              onFolderSelected(path)
            } else {
              handleClose()
            }
          }
        }
        
        input.click()
      }
    } catch (error) {
      console.error('Error selecting output folder:', error)
    } finally {
      setIsSelectingFolder(false)
    }
  }

  return (
    <div 
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-yellow-600/20">
              <AlertCircle className="h-5 w-5 text-yellow-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-200">Output Folder Required</h3>
          </div>
          <button
            onClick={handleClose}
            className="p-1 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          <p className="text-gray-300 mb-6">
            You need to set up the output folder before using AI Workflows. 
            All generated videos will be saved to this folder.
          </p>
          
          {/* Action Button */}
          <div className="flex items-center justify-end gap-3">
            <button
              onClick={handleClose}
              className="px-4 py-2 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-lg font-medium transition-colors"
            >
              Close
            </button>
            <button
              onClick={handleSelectFolder}
              disabled={isSelectingFolder}
              className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg font-medium transition-colors"
            >
              <FolderOpen className="h-4 w-4" />
              {isSelectingFolder ? 'Selecting...' : 'Select Output Folder'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

