import React, { useState, useEffect } from 'react'
import { Bot, Workflow, Zap, ArrowRight, ImageIcon, Film, Type, Upload, Sparkles, Plus, Play, Edit, Trash2, Clock, ChevronDown, ChevronUp, Timer, Power, PowerOff } from 'lucide-react'
import { workflowManager } from '../utils/workflowManager.js'
import ConfirmationModal from '../components/ConfirmationModal.jsx'

const BACKEND_URL = 'http://127.0.0.1:8000'

export default function AIWorkflows() {
  const [workflows, setWorkflows] = useState([])
  const [workflowStates, setWorkflowStates] = useState({})
  const [deleteModal, setDeleteModal] = useState({ isOpen: false, workflowId: null, workflowName: '' })
  const [isHelpSectionExpanded, setIsHelpSectionExpanded] = useState(false)
  const [activatingWorkflow, setActivatingWorkflow] = useState(null)

  // Load workflow states from backend
  const loadWorkflowStates = React.useCallback(async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/workflows/status`)
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setWorkflowStates(data.states || {})
        }
      }
    } catch (error) {
      console.error('Error loading workflow states:', error)
    }
  }, [])

  // Sync workflows with backend and load states
  useEffect(() => {
    const syncWorkflows = async () => {
      // Get workflows from local storage
      const localWorkflows = workflowManager.getWorkflows()
      setWorkflows(localWorkflows)
      
      // Sync workflows with backend
      try {
        await fetch(`${BACKEND_URL}/workflows/sync`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(localWorkflows)
        })
      } catch (error) {
        console.error('Error syncing workflows:', error)
      }
      
      // Load workflow states
      await loadWorkflowStates()
    }
    
    syncWorkflows()
    
    // Listen for workflow updates
    const handleWorkflowsUpdate = async (event) => {
      const updatedWorkflows = event.detail.workflows
      setWorkflows(updatedWorkflows)
      
      // Sync with backend
      try {
        await fetch(`${BACKEND_URL}/workflows/sync`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updatedWorkflows)
        })
        await loadWorkflowStates()
      } catch (error) {
        console.error('Error syncing workflows:', error)
      }
    }

    window.addEventListener('workflowsUpdated', handleWorkflowsUpdate)
    
    // Poll workflow states every 5 seconds
    const statePollInterval = setInterval(loadWorkflowStates, 5000)
    
    return () => {
      window.removeEventListener('workflowsUpdated', handleWorkflowsUpdate)
      clearInterval(statePollInterval)
    }
  }, [loadWorkflowStates])

  // Handle activate/deactivate workflow
  const handleToggleWorkflow = async (workflowId, isCurrentlyActive) => {
    setActivatingWorkflow(workflowId)
    try {
      const endpoint = isCurrentlyActive ? 'deactivate' : 'activate'
      const response = await fetch(`${BACKEND_URL}/workflows/${workflowId}/${endpoint}`, {
        method: 'POST'
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          // Reload states
          await loadWorkflowStates()
        } else {
          alert(data.error || 'Failed to update workflow state')
        }
      } else {
        alert('Failed to update workflow state')
      }
    } catch (error) {
      console.error('Error toggling workflow:', error)
      alert('Error updating workflow state')
    } finally {
      setActivatingWorkflow(null)
    }
  }

  // Get workflow state helper
  const getWorkflowState = (workflowId) => {
    return workflowStates[workflowId] || {
      isActive: false,
      isRunning: false
    }
  }

  const features = [
    {
      icon: Workflow,
      title: 'Multi-Step Pipelines',
      description: 'Chain together complex workflows like text → image → video → upscale → upload'
    },
    {
      icon: Bot,
      title: 'Autonomous Agents',
      description: 'Let AI agents handle entire content creation processes with minimal oversight'
    },
    {
      icon: Zap,
      title: 'Smart Concatenation',
      description: 'Automatically merge and combine multiple generated outputs into cohesive content'
    }
  ]

  const exampleWorkflows = [
    {
      title: 'Social Media Campaign',
      steps: ['Text Prompt', 'Generate Image', 'Create Video', 'Add Captions', 'Export']
    },
    {
      title: 'Product Showcase',
      steps: ['Product Description', 'Generate Images', 'Create Demo Video', 'Add Music', 'Upload']
    },
    {
      title: 'Educational Content',
      steps: ['Topic Research', 'Generate Visuals', 'Create Animation', 'Add Narration', 'Publish']
    }
  ]

  const navigateToCreateWorkflow = () => {
    // Navigate to workflow type selection page first
    const ev = new CustomEvent('navigate', { detail: 'workflow-type-selection' })
    window.dispatchEvent(ev)
  }

  const handleDeleteWorkflow = (workflowId, workflowName) => {
    setDeleteModal({
      isOpen: true,
      workflowId,
      workflowName
    })
  }

  const confirmDelete = () => {
    if (deleteModal.workflowId) {
      workflowManager.deleteWorkflow(deleteModal.workflowId)
    }
  }

  const closeDeleteModal = () => {
    setDeleteModal({ isOpen: false, workflowId: null, workflowName: '' })
  }

  const handleEditWorkflow = (workflowId) => {
    // Set the editing workflow ID in global state
    window.editingWorkflowId = workflowId
    // Navigate to CreateWorkflow page
    const ev = new CustomEvent('navigate', { detail: 'create-workflow' })
    window.dispatchEvent(ev)
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600/20 rounded-lg">
              <Bot className="h-6 w-6 text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-100">AI Workflows</h1>
              <p className="text-gray-400">Advanced AI-powered content generation pipelines</p>
            </div>
          </div>
          <button 
            onClick={navigateToCreateWorkflow}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            <Plus className="h-4 w-4" />
            Create Workflow
          </button>
        </div>
      </div>

      {/* Workflows List */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 mb-8">
        <div className="flex items-center justify-between mb-8">
          <h3 className="text-xl font-semibold text-gray-200">Your Workflows</h3>
          <div className="text-base text-gray-400">
            {workflows.length} workflow{workflows.length !== 1 ? 's' : ''}
          </div>
        </div>
        
        {workflows.length > 0 ? (
          <div className="space-y-4">
            {workflows.map((workflow) => (
              <div key={workflow.id} className="bg-gray-800 border border-gray-700 rounded-lg p-5 hover:bg-gray-750 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-3">
                      <h4 className="font-medium text-base text-gray-200">{workflow.name}</h4>
                      {(() => {
                        const state = getWorkflowState(workflow.id)
                        const isActive = state.isActive
                        const isRunning = state.isRunning
                        
                        // Determine badge color and text
                        let badgeClass, badgeText
                        if (isRunning) {
                          // Blue for running
                          badgeClass = 'bg-blue-600/20 text-blue-400 border border-blue-600/30'
                          badgeText = 'Running'
                        } else if (isActive) {
                          // Green for active and not running
                          badgeClass = 'bg-green-600/20 text-green-400 border border-green-600/30'
                          badgeText = 'Active'
                        } else {
                          // Red for inactive
                          badgeClass = 'bg-red-600/20 text-red-400 border border-red-600/30'
                          badgeText = 'Inactive'
                        }
                        
                        return (
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${badgeClass}`}>
                            {badgeText}
                          </span>
                        )
                      })()}
                      <span className="px-2 py-1 bg-gray-700 text-gray-300 rounded-full text-xs">
                        {workflow.numberOfClips} clips
                      </span>
                    </div>
                    <p className="text-sm text-gray-400 mb-4">{workflow.description}</p>
                    <div className="flex items-center gap-4 text-sm text-gray-500">
                      <div className="flex items-center gap-1">
                        <Workflow className="h-3 w-3" />
                        {workflow.steps} steps
                      </div>
                      <div className="flex items-center gap-1">
                        <Timer className="h-3 w-3" />
                        {(() => {
                          const scheduleMinutes = workflow.schedule || 60
                          if (scheduleMinutes >= 60 && scheduleMinutes % 60 === 0) {
                            return `Every ${scheduleMinutes / 60} hour${scheduleMinutes / 60 !== 1 ? 's' : ''}`
                          } else {
                            return `Every ${scheduleMinutes} minute${scheduleMinutes !== 1 ? 's' : ''}`
                          }
                        })()}
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Created: {new Date(workflow.createdAt).toLocaleDateString()}
                      </div>
                      <div className="flex items-center gap-1">
                        <span>Duration: {workflow.clipDuration}s</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    {(() => {
                      const state = getWorkflowState(workflow.id)
                      const isActive = state.isActive
                      const isProcessing = activatingWorkflow === workflow.id
                      
                      return (
                        <button
                          onClick={() => handleToggleWorkflow(workflow.id, isActive)}
                          disabled={isProcessing || state.isRunning}
                          className={`p-2 rounded-lg transition-colors ${
                            isActive
                              ? 'text-green-400 hover:text-green-300 hover:bg-green-600/20'
                              : 'text-gray-400 hover:text-red-300 hover:bg-red-600/20'
                          } ${isProcessing || state.isRunning ? 'opacity-50 cursor-not-allowed' : ''}`}
                          title={isActive ? 'Deactivate Workflow' : 'Activate Workflow'}
                        >
                          {isActive ? (
                            <PowerOff className="h-4 w-4" />
                          ) : (
                            <Power className="h-4 w-4" />
                          )}
                        </button>
                      )
                    })()}
                    <button 
                      onClick={() => handleEditWorkflow(workflow.id)}
                      className="p-2 text-gray-400 hover:text-gray-300 hover:bg-gray-700 rounded-lg transition-colors" 
                      title="Edit Workflow"
                    >
                      <Edit className="h-4 w-4" />
                    </button>
                    <button 
                      onClick={() => handleDeleteWorkflow(workflow.id, workflow.name)}
                      className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-600/20 rounded-lg transition-colors" 
                      title="Delete Workflow"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-800 rounded-full mb-6">
              <Workflow className="h-8 w-8 text-gray-500" />
            </div>
            <h4 className="text-gray-300 font-medium text-lg mb-3">No workflows yet</h4>
            <p className="text-gray-500 text-base mb-6">Create your first workflow to get started with AI-powered content generation</p>
            <button 
              onClick={navigateToCreateWorkflow}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              <Plus className="h-4 w-4" />
              Create Your First Workflow
            </button>
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={deleteModal.isOpen}
        onClose={closeDeleteModal}
        onConfirm={confirmDelete}
        title="Delete Workflow"
        message={`Are you sure you want to delete "${deleteModal.workflowName}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        type="danger"
      />

      {/* Help Section - Expandable */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <button
          onClick={() => setIsHelpSectionExpanded(!isHelpSectionExpanded)}
          className="w-full flex items-center justify-between p-6 hover:bg-gray-800/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <Sparkles className="h-5 w-5 text-blue-400" />
            <h3 className="text-lg font-semibold text-gray-200">Learn About AI Workflows</h3>
          </div>
          {isHelpSectionExpanded ? (
            <ChevronUp className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          )}
        </button>
        
        {isHelpSectionExpanded && (
          <div className="px-6 pb-6 space-y-6">
            {/* Main Description Card */}
            <div className="bg-gradient-to-br from-gray-800 to-gray-900 border border-gray-700 rounded-xl p-8">
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600/20 rounded-full mb-4">
                  <Sparkles className="h-8 w-8 text-blue-400" />
                </div>
                <h2 className="text-xl font-semibold text-gray-100 mb-3">Advanced AI Workflows</h2>
                <p className="text-gray-400 max-w-2xl mx-auto">
                  Design sophisticated, multi-step content creation pipelines that combine multiple AI models 
                  and automation tools. Create autonomous workflows that can handle complex content generation 
                  tasks from start to finish.
                </p>
              </div>
            </div>

            {/* Features Grid */}
            <div className="grid md:grid-cols-3 gap-6">
              {features.map((feature, index) => (
                <div key={index} className="bg-gray-800 border border-gray-700 rounded-lg p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-blue-600/20 rounded-lg">
                      <feature.icon className="h-5 w-5 text-blue-400" />
                    </div>
                    <h3 className="font-semibold text-gray-200">{feature.title}</h3>
                  </div>
                  <p className="text-sm text-gray-400">{feature.description}</p>
                </div>
              ))}
            </div>

            {/* Example Workflows */}
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-gray-200 mb-4">Example Workflow Templates</h3>
              <div className="grid md:grid-cols-3 gap-4">
                {exampleWorkflows.map((workflow, index) => (
                  <div key={index} className="bg-gray-900 border border-gray-700 rounded-lg p-4">
                    <h4 className="font-medium text-gray-200 mb-3">{workflow.title}</h4>
                    <div className="space-y-2">
                      {workflow.steps.map((step, stepIndex) => (
                        <div key={stepIndex} className="flex items-center gap-2 text-sm">
                          <div className="flex items-center justify-center w-6 h-6 bg-gray-700 rounded-full text-xs text-gray-300">
                            {stepIndex + 1}
                          </div>
                          <span className="text-gray-400">{step}</span>
                          {stepIndex < workflow.steps.length - 1 && (
                            <ArrowRight className="h-3 w-3 text-gray-500 ml-auto" />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

    </div>
  )
}


