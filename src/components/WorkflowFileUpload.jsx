import React from 'react'
import { Upload, FileText, AlertCircle } from 'lucide-react'

export default function WorkflowFileUpload({ value, onChange, label = "ComfyUI Workflow" }) {
  const fileInputRef = React.useRef(null)
  const [error, setError] = React.useState(null)

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    setError(null)
    
    try {
      const text = await file.text()
      const json = JSON.parse(text)
      
      // Basic validation to ensure it's a ComfyUI workflow
      if (typeof json !== 'object' || json === null) {
        throw new Error('Invalid JSON format')
      }
      
      // Check for ComfyUI API workflow format
      // API format can have different structures:
      // 1. { "workflow": { "nodes": {...}, "links": [...] } } - some API formats
      // 2. { "prompt": { "1": {...}, "2": {...} } } - ComfyUI's standard API format
      // 3. { "1": {...}, "2": {...} } - original format
      
      if (json.workflow && typeof json.workflow === 'object') {
        // This is API format with 'workflow' property
        if (!json.workflow.nodes || !json.workflow.links) {
          throw new Error('This appears to be an API format workflow but is missing required workflow structure')
        }
      } else if (json.prompt && typeof json.prompt === 'object') {
        // This is ComfyUI's standard API format with 'prompt' property
        // Check if it has node-like structure (numeric keys with class_type)
        const hasValidNodes = Object.values(json.prompt).some(node => 
          typeof node === 'object' && node.class_type
        )
        if (!hasValidNodes) {
          throw new Error('This appears to be an API format workflow but is missing valid node structure')
        }
      } else if (json.nodes && json.links) {
        // This might be the original format - check if it has the right structure
        console.warn('This appears to be an original workflow format. For best results, please export your workflow using the "API" format from ComfyUI.')
      } else {
        // Check if it's a direct node structure (original format)
        const hasValidNodes = Object.values(json).some(node => 
          typeof node === 'object' && node.class_type
        )
        if (hasValidNodes) {
          console.warn('This appears to be an original workflow format. For best results, please export your workflow using the "API" format from ComfyUI.')
        } else {
          throw new Error('This doesn\'t appear to be a valid ComfyUI workflow file. Please export your workflow using the "API" format from ComfyUI.')
        }
      }
      
      const payload = { 
        fileName: file.name, 
        json,
        fileSize: file.size,
        lastModified: file.lastModified
      }
      
      onChange?.(payload)
    } catch (err) {
      console.error('Invalid workflow file', err)
      setError(err.message)
      onChange?.(null)
    }
  }

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleRemoveFile = () => {
    onChange?.(null)
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <label className="text-xs text-gray-400">{label}</label>
      </div>
      
      <div className="space-y-2">
        <input
          ref={fileInputRef}
          type="file"
          accept="application/json,.json"
          className="hidden"
          onChange={handleFileChange}
        />
        
        {!value ? (
          <div
            onClick={handleUploadClick}
            className="flex items-center justify-center gap-2 p-4 border-2 border-dashed border-gray-700 rounded-lg cursor-pointer hover:border-gray-600 transition-colors bg-gray-900/50"
          >
            <Upload className="h-5 w-5 text-gray-400" />
            <span className="text-sm text-gray-300">Click to upload ComfyUI API workflow file</span>
          </div>
        ) : (
          <div className="flex items-center justify-between p-3 bg-gray-800 rounded-lg border border-gray-700">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <FileText className="h-4 w-4 text-blue-400 flex-shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="text-sm text-gray-200 truncate" title={value.fileName}>
                  {value.fileName}
                </div>
                <div className="text-xs text-gray-400">
                  {(value.fileSize / 1024).toFixed(1)} KB
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleUploadClick}
                className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-200 rounded transition-colors"
              >
                Replace
              </button>
              <button
                type="button"
                onClick={handleRemoveFile}
                className="px-2 py-1 text-xs bg-red-700 hover:bg-red-600 text-gray-200 rounded transition-colors"
              >
                Remove
              </button>
            </div>
          </div>
        )}
        
        {error && (
          <div className="flex items-center gap-2 p-2 bg-red-900/20 border border-red-800 rounded text-sm text-red-300">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  )
}
