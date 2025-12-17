import React from 'react'
import { X, AlertCircle } from 'lucide-react'

export default function ComfyUIErrorModal({ isOpen, onClose }) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-900/20 rounded-lg">
              <AlertCircle className="h-6 w-6 text-red-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-200">ComfyUI Server Not Running</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          <p className="text-sm text-gray-300">
            The ComfyUI server is not running or cannot be reached. Please start the ComfyUI server and try again.
          </p>
          
          <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
            <p className="text-xs text-gray-400 mb-2">To start ComfyUI:</p>
            <ol className="text-xs text-gray-300 space-y-1 list-decimal list-inside">
              <li>Open a terminal/command prompt</li>
              <li>Navigate to your ComfyUI directory</li>
              <li>Start ComfyUI either by running the script file or with python: <code className="bg-gray-900 px-1 rounded">python main.py</code></li>
              <li>Wait for the server to start (usually on port 8188)</li>
            </ol>
          </div>

          <div className="flex items-center justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm bg-blue-700 hover:bg-blue-600 text-gray-200 rounded transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

