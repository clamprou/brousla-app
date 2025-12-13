import React, { useState, useEffect } from 'react'
import { Bot, Workflow, Zap, ArrowRight, ImageIcon, Film, Type, Upload, Sparkles, Plus, Play, Edit, Trash2, Clock, ChevronDown, ChevronUp, Timer, Power, PowerOff, Loader2, X } from 'lucide-react'
import { workflowManager } from '../utils/workflowManager.js'
import ConfirmationModal from '../components/ConfirmationModal.jsx'
import OutputFolderModal from '../components/OutputFolderModal.jsx'
import SubscriptionModal from '../components/SubscriptionModal.jsx'
import { settingsManager } from '../utils/settingsManager.js'
import { useAuth } from '../contexts/AuthContext.jsx'

const BACKEND_URL = 'http://127.0.0.1:8000'

export default function AIWorkflows() {
  const { userId, token, subscriptionStatus, fetchSubscriptionStatus } = useAuth()
  const [workflows, setWorkflows] = useState([])
  const [workflowStates, setWorkflowStates] = useState({})
  const [deleteModal, setDeleteModal] = useState({ isOpen: false, workflowId: null, workflowName: '' })
  const [isHelpSectionExpanded, setIsHelpSectionExpanded] = useState(false)
  const [activatingWorkflow, setActivatingWorkflow] = useState(null)
  const [showOutputFolderModal, setShowOutputFolderModal] = useState(false)
  const [cancellingWorkflow, setCancellingWorkflow] = useState(null)
  const [cancelConfirmModal, setCancelConfirmModal] = useState({ isOpen: false, workflowId: null })
  const [errorModal, setErrorModal] = useState({ isOpen: false, message: '' })
  const [showSubscriptionModal, setShowSubscriptionModal] = useState(false)

  // Load workflow states from backend
  const loadWorkflowStates = React.useCallback(async () => {
    if (!userId) {
      setWorkflowStates({})
      return
    }
    
    try {
      const response = await fetch(`${BACKEND_URL}/workflows/status`, {
        headers: {
          'X-User-Id': userId
        }
      })
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setWorkflowStates(data.states || {})
        }
      }
    } catch (error) {
      console.error('Error loading workflow states:', error)
    }
  }, [userId])

  // Check subscription status on mount - only once when token/userId changes
  useEffect(() => {
    if (token && userId) {
      fetchSubscriptionStatus()
    }
    // Only run when token or userId changes, not when fetchSubscriptionStatus changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, userId])

  // Check if subscription is required and show modal
  useEffect(() => {
    if (subscriptionStatus) {
      const canExecute = subscriptionStatus.can_execute
      if (!canExecute) {
        setShowSubscriptionModal(true)
      } else {
        setShowSubscriptionModal(false)
      }
    }
  }, [subscriptionStatus])

  // Check if output folder is set when component mounts
  useEffect(() => {
    const outputFolder = settingsManager.getAIWorkflowsOutputFolder()
    if (!outputFolder) {
      setShowOutputFolderModal(true)
    }

    // Listen for settings updates
    const handleSettingsUpdate = () => {
      const updatedOutputFolder = settingsManager.getAIWorkflowsOutputFolder()
      if (updatedOutputFolder) {
        setShowOutputFolderModal(false)
      }
    }

    window.addEventListener('settingsUpdated', handleSettingsUpdate)
    return () => {
      window.removeEventListener('settingsUpdated', handleSettingsUpdate)
    }
  }, [])

  // Update workflowManager userId when it changes
  useEffect(() => {
    if (userId) {
      // Set userId and load workflows from localStorage for this user
      workflowManager.setUserId(userId)
      // Force a reload to ensure workflows are loaded
      const loadedWorkflows = workflowManager.getWorkflows()
      if (loadedWorkflows.length > 0) {
        setWorkflows(loadedWorkflows)
      }
    } else {
      // Clear in-memory workflows when user logs out (but keep in localStorage)
      workflowManager.clearWorkflows()
      setWorkflows([])
    }
  }, [userId])

  // Sync workflows with backend and load states
  useEffect(() => {
    if (!userId) {
      setWorkflows([])
      return
    }

    const syncWorkflows = async () => {
      // Get workflows from local storage (already filtered by userId in getWorkflows)
      const localWorkflows = workflowManager.getWorkflows()
      setWorkflows(localWorkflows)
      
      // Sync workflows with backend
      try {
        await fetch(`${BACKEND_URL}/workflows/sync`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'X-User-Id': userId
          },
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
      // Filter to only show workflows for current user
      const userWorkflows = updatedWorkflows.filter(w => w.userId === userId)
      setWorkflows(userWorkflows)
      
      // Sync with backend
      try {
        await fetch(`${BACKEND_URL}/workflows/sync`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'X-User-Id': userId
          },
          body: JSON.stringify(userWorkflows)
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
  }, [loadWorkflowStates, userId])

  // Handle activate/deactivate workflow
  const handleToggleWorkflow = async (workflowId, isCurrentlyActive) => {
    if (!userId) return
    
    setActivatingWorkflow(workflowId)
    try {
      const endpoint = isCurrentlyActive ? 'deactivate' : 'activate'
      const response = await fetch(`${BACKEND_URL}/workflows/${workflowId}/${endpoint}`, {
        method: 'POST',
        headers: {
          'X-User-Id': userId
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          // Reload states
          await loadWorkflowStates()
        } else {
          setErrorModal({ isOpen: true, message: data.error || 'Failed to update workflow state' })
        }
      } else {
        setErrorModal({ isOpen: true, message: 'Failed to update workflow state' })
      }
    } catch (error) {
      console.error('Error toggling workflow:', error)
      setErrorModal({ isOpen: true, message: 'Error updating workflow state' })
    } finally {
      setActivatingWorkflow(null)
    }
  }

  // Handle cancel workflow execution
  const handleCancelWorkflow = (workflowId) => {
    setCancelConfirmModal({ isOpen: true, workflowId })
  }

  const confirmCancelWorkflow = async () => {
    const workflowId = cancelConfirmModal.workflowId
    setCancelConfirmModal({ isOpen: false, workflowId: null })
    
    if (!workflowId || !userId) return
    
    setCancellingWorkflow(workflowId)
    try {
      const response = await fetch(`${BACKEND_URL}/workflows/${workflowId}/cancel`, {
        method: 'POST',
        headers: {
          'X-User-Id': userId
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          // Reload states immediately
          await loadWorkflowStates()
        } else {
          setErrorModal({ isOpen: true, message: data.error || 'Failed to cancel workflow' })
        }
      } else {
        setErrorModal({ isOpen: true, message: 'Failed to cancel workflow' })
      }
    } catch (error) {
      console.error('Error cancelling workflow:', error)
      setErrorModal({ isOpen: true, message: 'Error cancelling workflow' })
    } finally {
      setCancellingWorkflow(null)
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

  const handleSubscriptionModalClose = () => {
    // Navigate to profile page when modal is closed
    const ev = new CustomEvent('navigate', { detail: 'profile' })
    window.dispatchEvent(ev)
  }

  // Block all interactions if subscription modal is shown
  const isBlocked = showSubscriptionModal

  return (
    <div className="p-6 max-w-6xl mx-auto relative">
      {/* Subscription Modal */}
      <SubscriptionModal
        isOpen={showSubscriptionModal}
        onClose={handleSubscriptionModalClose}
        subscriptionStatus={subscriptionStatus}
      />
      
      {/* Overlay to block interactions when subscription modal is shown */}
      {isBlocked && (
        <div className="absolute inset-0 z-40 bg-gray-950/50 backdrop-blur-sm" />
      )}
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
            disabled={isBlocked}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
            {workflows.map((workflow) => {
              const state = getWorkflowState(workflow.id)
              const isActive = state.isActive
              const isRunning = state.isRunning
              
              // Determine card styling based on state
              let cardClasses = 'bg-gray-800 border rounded-lg p-5 hover:bg-gray-750 transition-colors relative'
              if (isRunning) {
                // Blue border for running state
                cardClasses += ' border-blue-600 bg-blue-600/5'
              } else if (isActive) {
                // Green border and subtle green background for activated state
                cardClasses += ' border-green-600 bg-green-600/10'
              } else {
                // Default gray border for inactive state
                cardClasses += ' border-gray-700'
              }
              
              return (
              <div key={workflow.id} className={cardClasses}>
                {/* Loading overlay for running state */}
                {isRunning && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-blue-600/10 rounded-lg z-10">
                    <Loader2 className="h-8 w-8 text-blue-400 animate-spin mb-2" />
                    <button
                      onClick={() => handleCancelWorkflow(workflow.id)}
                      disabled={cancellingWorkflow === workflow.id}
                      className="px-2 py-1 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Cancel Workflow Execution"
                    >
                      {cancellingWorkflow === workflow.id ? (
                        <>
                          <Loader2 className="h-3 w-3 animate-spin" />
                          <span>Cancelling...</span>
                        </>
                      ) : (
                        <>
                          <X className="h-3 w-3" />
                          <span>Cancel</span>
                        </>
                      )}
                    </button>
                  </div>
                )}
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-3">
                      <h4 className="font-medium text-base text-gray-200">{workflow.name}</h4>
                      {(() => {
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
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    {(() => {
                      const isProcessing = activatingWorkflow === workflow.id
                      
                      return (
                        <button
                          onClick={() => handleToggleWorkflow(workflow.id, isActive)}
                          disabled={isProcessing || isRunning || isBlocked}
                          className={`p-2 rounded-lg transition-colors ${
                            isActive
                              ? 'text-green-400 hover:text-green-300 hover:bg-green-600/20'
                              : 'text-gray-400 hover:text-red-300 hover:bg-red-600/20'
                          } ${isProcessing || isRunning || isBlocked ? 'opacity-50 cursor-not-allowed' : ''}`}
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
                      disabled={isBlocked}
                      className="p-2 text-gray-400 hover:text-gray-300 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed" 
                      title="Edit Workflow"
                    >
                      <Edit className="h-4 w-4" />
                    </button>
                    <button 
                      onClick={() => handleDeleteWorkflow(workflow.id, workflow.name)}
                      disabled={isBlocked}
                      className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-600/20 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed" 
                      title="Delete Workflow"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
              )
            })}
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
              disabled={isBlocked}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Plus className="h-4 w-4" />
              Create Your First Workflow
            </button>
          </div>
        )}
      </div>

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

      {/* Output Folder Modal */}
      <OutputFolderModal
        isOpen={showOutputFolderModal}
        onClose={() => setShowOutputFolderModal(false)}
        onFolderSelected={() => setShowOutputFolderModal(false)}
        navigateBackOnClose={true}
      />

      {/* Cancel Confirmation Modal */}
      <ConfirmationModal
        isOpen={cancelConfirmModal.isOpen}
        onClose={() => setCancelConfirmModal({ isOpen: false, workflowId: null })}
        onConfirm={confirmCancelWorkflow}
        title="Cancel Workflow Execution"
        message="Are you sure you want to cancel this workflow execution? The current execution will be stopped."
        confirmText="Cancel Execution"
        cancelText="Keep Running"
        type="danger"
      />

      {/* Error Modal */}
      <ConfirmationModal
        isOpen={errorModal.isOpen}
        onClose={() => setErrorModal({ isOpen: false, message: '' })}
        onConfirm={() => setErrorModal({ isOpen: false, message: '' })}
        title="Error"
        message={errorModal.message}
        confirmText="OK"
        cancelText=""
        type="danger"
      />
    </div>
  )
}


