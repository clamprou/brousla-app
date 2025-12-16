import React from 'react'
import { Upload, FileText, AlertCircle, Save, Trash2, Clock, X } from 'lucide-react'
import { getStoredWorkflows, loadStoredWorkflow, deleteStoredWorkflow, markWorkflowUsed, saveWorkflow } from '../utils/workflowStorage.js'
import { useAuth } from '../contexts/AuthContext.jsx'
import ConfirmationModal from './ConfirmationModal.jsx'

export default function WorkflowFileUpload({ value, onChange, label = "ComfyUI Workflow" }) {
  const { userId } = useAuth()
  const fileInputRef = React.useRef(null)
  const [error, setError] = React.useState(null)
  const [isDragging, setIsDragging] = React.useState(false)
  const [storedWorkflows, setStoredWorkflows] = React.useState([])
  const [isLoadingStored, setIsLoadingStored] = React.useState(false)
  const [showStoredList, setShowStoredList] = React.useState(false)
  const [showSaveModal, setShowSaveModal] = React.useState(false)
  const [saveName, setSaveName] = React.useState('')
  const [saveDescription, setSaveDescription] = React.useState('')
  const [isSaving, setIsSaving] = React.useState(false)
  const [deleteModal, setDeleteModal] = React.useState({ isOpen: false, workflowId: null, workflowName: '' })

  const processFile = async (file) => {
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

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    await processFile(file)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const file = e.dataTransfer.files?.[0]
    await processFile(file)
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

  // Load stored workflows on mount and when userId changes
  React.useEffect(() => {
    if (userId) {
      loadStoredWorkflowsList()
    } else {
      setStoredWorkflows([])
    }
  }, [userId])

  const loadStoredWorkflowsList = async () => {
    if (!userId) return
    
    setIsLoadingStored(true)
    try {
      const workflows = await getStoredWorkflows(userId)
      setStoredWorkflows(workflows)
    } catch (error) {
      console.error('Error loading stored workflows:', error)
    } finally {
      setIsLoadingStored(false)
    }
  }

  const handleLoadStoredWorkflow = async (workflowId) => {
    if (!userId) return
    
    try {
      const result = await loadStoredWorkflow(workflowId, userId)
      if (result) {
        // Mark as used
        await markWorkflowUsed(workflowId, userId)
        
        // Set the workflow as current value
        const payload = {
          fileName: result.metadata.filename,
          json: result.json,
          fileSize: result.metadata.fileSize,
          lastModified: new Date(result.metadata.uploadDate).getTime(),
          storedWorkflowId: workflowId
        }
        onChange?.(payload)
        
        // Refresh stored workflows list to update lastUsed
        await loadStoredWorkflowsList()
      }
    } catch (error) {
      console.error('Error loading stored workflow:', error)
      setError('Failed to load stored workflow')
    }
  }

  const handleDeleteStoredWorkflow = (workflowId, workflowName, e) => {
    e.stopPropagation()
    if (!userId) return
    setDeleteModal({ isOpen: true, workflowId, workflowName })
  }

  const confirmDeleteStoredWorkflow = async () => {
    const { workflowId } = deleteModal
    if (!workflowId || !userId) return
    
    setDeleteModal({ isOpen: false, workflowId: null, workflowName: '' })
    
    try {
      const success = await deleteStoredWorkflow(workflowId, userId)
      if (success) {
        await loadStoredWorkflowsList()
        // If the deleted workflow was currently selected, clear it
        if (value?.storedWorkflowId === workflowId) {
          onChange?.(null)
        }
      } else {
        setError('Failed to delete workflow')
      }
    } catch (error) {
      console.error('Error deleting workflow:', error)
      setError('Failed to delete workflow')
    }
  }

  const closeDeleteModal = () => {
    setDeleteModal({ isOpen: false, workflowId: null, workflowName: '' })
  }

  const handleSaveClick = () => {
    if (!value) return
    setSaveName(value.fileName.replace('.json', '') || '')
    setSaveDescription('')
    setShowSaveModal(true)
  }

  const handleSaveWorkflow = async () => {
    if (!value || !saveName.trim()) {
      setError('Please enter a workflow name')
      return
    }

    if (!userId) {
      setError('You must be logged in to save workflows')
      return
    }

    setIsSaving(true)
    setError(null)

    try {
      const savedWorkflow = await saveWorkflow(saveName.trim(), saveDescription.trim(), value, userId)
      if (savedWorkflow) {
        // Update the current value to mark it as saved
        onChange?.({
          ...value,
          storedWorkflowId: savedWorkflow.id
        })
        
        // Refresh stored workflows list
        await loadStoredWorkflowsList()
        
        // Close modal
        setShowSaveModal(false)
        setSaveName('')
        setSaveDescription('')
      } else {
        setError('Failed to save workflow')
      }
    } catch (error) {
      console.error('Error saving workflow:', error)
      setError('Failed to save workflow')
    } finally {
      setIsSaving(false)
    }
  }

  const handleCloseSaveModal = () => {
    setShowSaveModal(false)
    setSaveName('')
    setSaveDescription('')
    setError(null)
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Never'
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return 'Invalid date'
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-xs text-gray-400">{label}</label>
        {storedWorkflows.length > 0 && (
          <button
            type="button"
            onClick={() => setShowStoredList(!showStoredList)}
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            {showStoredList ? 'Hide' : 'Show'} Saved Workflows ({storedWorkflows.length})
          </button>
        )}
      </div>

      {/* Stored Workflows List */}
      {showStoredList && storedWorkflows.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 space-y-2 max-h-64 overflow-y-auto">
          <div className="text-xs text-gray-400 mb-2">Saved Workflows</div>
          {isLoadingStored ? (
            <div className="text-xs text-gray-500 text-center py-2">Loading...</div>
          ) : (
            storedWorkflows.map((workflow) => (
              <div
                key={workflow.id}
                className="flex items-center justify-between p-2 bg-gray-800 rounded border border-gray-700 hover:border-gray-600 transition-colors cursor-pointer group"
                onClick={() => handleLoadStoredWorkflow(workflow.id)}
              >
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-gray-200 truncate font-medium">
                    {workflow.name}
                  </div>
                  {workflow.description && (
                    <div className="text-xs text-gray-400 truncate mt-0.5">
                      {workflow.description}
                    </div>
                  )}
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      Used: {formatDate(workflow.lastUsed)}
                    </span>
                    <span>{(workflow.fileSize / 1024).toFixed(1)} KB</span>
                  </div>
                </div>
                <div className="flex items-center gap-1 ml-2">
                  <button
                    type="button"
                    onClick={(e) => handleDeleteStoredWorkflow(workflow.id, workflow.name, e)}
                    className="p-1 text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Delete workflow"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
      
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
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`flex items-center justify-center gap-2 p-4 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
              isDragging 
                ? 'border-blue-500 bg-blue-900/20' 
                : 'border-gray-700 hover:border-gray-600 bg-gray-900/50'
            }`}
          >
            <Upload className={`h-5 w-5 ${isDragging ? 'text-blue-400' : 'text-gray-400'}`} />
            <span className={`text-sm ${isDragging ? 'text-blue-300' : 'text-gray-300'}`}>
              {isDragging ? 'Drop workflow file here' : 'Click or drag to upload ComfyUI API workflow file'}
            </span>
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
                  {value.storedWorkflowId && (
                    <span className="ml-2 text-blue-400">(Saved)</span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {!value.storedWorkflowId && (
                <button
                  type="button"
                  onClick={handleSaveClick}
                  className="px-2 py-1 text-xs bg-blue-700 hover:bg-blue-600 text-gray-200 rounded transition-colors flex items-center gap-1"
                  title="Save workflow"
                >
                  <Save className="h-3 w-3" />
                  Save
                </button>
              )}
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

      {/* Save Workflow Modal */}
      {showSaveModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={handleCloseSaveModal}>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-200">Save Workflow</h3>
              <button
                type="button"
                onClick={handleCloseSaveModal}
                className="text-gray-400 hover:text-gray-200 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-300 mb-1">
                  Workflow Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  placeholder="Enter workflow name"
                  className="w-full bg-gray-950 text-gray-100 rounded-lg border border-gray-800 p-2 focus:outline-none focus:ring-2 focus:ring-blue-600"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm text-gray-300 mb-1">
                  Description (Optional)
                </label>
                <textarea
                  value={saveDescription}
                  onChange={(e) => setSaveDescription(e.target.value)}
                  placeholder="Enter workflow description"
                  rows={3}
                  className="w-full bg-gray-950 text-gray-100 rounded-lg border border-gray-800 p-2 focus:outline-none focus:ring-2 focus:ring-blue-600 resize-none"
                />
              </div>

              {error && (
                <div className="flex items-center gap-2 p-2 bg-red-900/20 border border-red-800 rounded text-sm text-red-300">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div className="flex items-center gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={handleCloseSaveModal}
                  className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-gray-200 rounded transition-colors"
                  disabled={isSaving}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveWorkflow}
                  disabled={isSaving || !saveName.trim()}
                  className="px-4 py-2 text-sm bg-blue-700 hover:bg-blue-600 text-gray-200 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isSaving ? (
                    <>
                      <div className="h-4 w-4 border-2 border-gray-200 border-t-transparent rounded-full animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4" />
                      Save
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <ConfirmationModal
        isOpen={deleteModal.isOpen}
        onClose={closeDeleteModal}
        onConfirm={confirmDeleteStoredWorkflow}
        title="Delete Workflow"
        message={`Are you sure you want to delete "${deleteModal.workflowName}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        type="danger"
      />
    </div>
  )
}
