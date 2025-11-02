import React, { useState } from 'react'
import { ArrowLeft, Save, Bot, HelpCircle } from 'lucide-react'
import WorkflowFileUpload from '../components/WorkflowFileUpload.jsx'
import { workflowManager } from '../utils/workflowManager.js'

export default function CreateWorkflow() {
  const [name, setName] = useState('')
  const [concept, setConcept] = useState('')
  const [clipDuration, setClipDuration] = useState(5)
  const [numberOfClips, setNumberOfClips] = useState(1)
  const [videoWorkflowFile, setVideoWorkflowFile] = useState(null)
  const [imageWorkflowFile, setImageWorkflowFile] = useState(null)
  const [scheduleValue, setScheduleValue] = useState(1)
  const [scheduleUnit, setScheduleUnit] = useState('hours')
  const [isSaving, setIsSaving] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editingWorkflowId, setEditingWorkflowId] = useState(null)
  const [workflowType, setWorkflowType] = useState(null)
  const conceptTextareaRef = React.useRef(null)


  // Load workflow data if editing or get workflow type from selection
  React.useEffect(() => {
    // Reset any potential focus issues
    document.body.style.overflow = 'unset'
    
    // Check if we're editing a workflow (check global edit state)
    const editWorkflowId = window.editingWorkflowId
    if (editWorkflowId) {
      const workflow = workflowManager.getWorkflowById(editWorkflowId)
      if (workflow) {
        setIsEditing(true)
        setEditingWorkflowId(editWorkflowId)
        setName(workflow.name || '')
        setConcept(workflow.concept || '')
        setClipDuration(workflow.clipDuration || 5)
        setNumberOfClips(workflow.numberOfClips || 1)
        setVideoWorkflowFile(workflow.videoWorkflowFile || null)
        setImageWorkflowFile(workflow.imageWorkflowFile || null)
        
        // Determine workflow type based on whether image workflow file exists
        // If imageWorkflowFile exists, it's an image-to-video workflow
        // Otherwise, it's a text-to-video workflow
        const detectedType = workflow.imageWorkflowFile ? 'image-to-video' : 'text-to-video'
        setWorkflowType(detectedType)
        
        // Load schedule: convert from minutes to appropriate display unit
        const scheduleInMinutes = workflow.schedule || 60 // Default to 60 minutes if not set
        if (scheduleInMinutes >= 60 && scheduleInMinutes % 60 === 0) {
          // Display in hours if it's a whole number of hours
          setScheduleValue(scheduleInMinutes / 60)
          setScheduleUnit('hours')
        } else {
          // Display in minutes, default to 60 if value is less than 60
          setScheduleValue(Math.max(60, scheduleInMinutes))
          setScheduleUnit('minutes')
        }
      }
      // Clear the edit state after loading
      window.editingWorkflowId = null
    } else {
      // If not editing, check for selected workflow type from selection page
      const selectedType = window.selectedWorkflowType
      if (selectedType) {
        setWorkflowType(selectedType)
        // Clear the selected workflow type after using it
        window.selectedWorkflowType = null
      }
    }
    
    // Clean up any potential event listeners that might interfere
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [])

  const handleSave = async () => {
    if (!name.trim()) {
      alert('Please enter a name for your workflow')
      return
    }
    
    if (!concept.trim()) {
      // Focus the concept textarea and show a visual indication
      if (conceptTextareaRef.current) {
        conceptTextareaRef.current.focus()
        conceptTextareaRef.current.style.borderColor = '#ef4444'
        setTimeout(() => {
          if (conceptTextareaRef.current) {
            conceptTextareaRef.current.style.borderColor = ''
          }
        }, 2000)
      }
      return
    }

    // Validate workflow files based on workflow type
    if (!videoWorkflowFile) {
      alert('Please select a Video Workflow file. This field is required.')
      return
    }

    // For image-to-video workflow, image workflow file is required
    if (workflowType === 'image-to-video' && !imageWorkflowFile) {
      alert('Please select an Image Workflow file. This field is required.')
      return
    }

    // Validate schedule
    const minScheduleValue = scheduleUnit === 'minutes' ? 60 : 1
    if (!scheduleValue || scheduleValue < minScheduleValue) {
      const unitText = scheduleUnit === 'minutes' ? 'minutes' : 'hours'
      alert(`Please enter a valid schedule value. The schedule must be at least ${minScheduleValue} ${unitText}.`)
      return
    }

    setIsSaving(true)
    
    try {
      // Convert schedule to minutes
      const scheduleInMinutes = scheduleUnit === 'hours' ? scheduleValue * 60 : scheduleValue
      
      const workflowData = {
        name: name.trim(),
        concept: concept.trim(),
        clipDuration,
        numberOfClips,
        videoWorkflowFile,
        imageWorkflowFile,
        schedule: scheduleInMinutes
      }

      let result
      if (isEditing && editingWorkflowId) {
        // Update existing workflow
        result = workflowManager.updateWorkflow(editingWorkflowId, workflowData)
        console.log('Workflow updated successfully:', result)
      } else {
        // Create new workflow
        result = workflowManager.addWorkflow(workflowData)
        console.log('Workflow created successfully:', result)
      }
      
      // Navigate back to AI Workflows page
      const ev = new CustomEvent('navigate', { detail: 'ai-composer' })
      window.dispatchEvent(ev)
    } catch (error) {
      console.error('Error saving workflow:', error)
      alert('Failed to save workflow. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }

  const handleBack = () => {
    // If editing, go back to AI Workflows page
    // If creating new, go back to Workflow Type Selection page
    const navigateTo = isEditing ? 'ai-composer' : 'workflow-type-selection'
    const ev = new CustomEvent('navigate', { detail: navigateTo })
    window.dispatchEvent(ev)
  }

  // Tooltip component
  const Tooltip = ({ children, content }) => {
    const [isVisible, setIsVisible] = useState(false)

    return (
      <div className="relative inline-block">
        <div
          onMouseEnter={() => setIsVisible(true)}
          onMouseLeave={() => setIsVisible(false)}
          className="inline-block"
        >
          {children}
        </div>
        {isVisible && (
          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-800 text-white text-sm rounded-lg shadow-lg whitespace-nowrap z-50 border border-gray-700">
            {content}
            <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-800"></div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-4 mb-4">
          <button
            onClick={handleBack}
            className="p-2 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-lg transition-colors"
            title="Back to AI Workflows"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600/20 rounded-lg">
              <Bot className="h-6 w-6 text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-100">
                {isEditing ? 'Edit Workflow' : 'Create New Workflow'}
              </h1>
              <p className="text-gray-400">
                {isEditing ? 'Modify your AI-powered content generation workflow' : 'Design a new AI-powered content generation workflow'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Form */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="space-y-6">
          {/* Name Field */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <label className="block text-sm font-medium text-gray-200">
                Name <span className="text-red-400">*</span>
              </label>
              <Tooltip content="Give your workflow a descriptive name">
                <HelpCircle className="h-4 w-4 text-gray-400 hover:text-gray-300 cursor-help" />
              </Tooltip>
            </div>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Social Media Campaign Workflow"
              className="w-full rounded-md bg-gray-950 border border-gray-800 p-3 text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            />
          </div>

          {/* Concept Field */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <label className="block text-sm font-medium text-gray-200">
                Concept <span className="text-red-400">*</span>
              </label>
              <Tooltip content="Describe the main concept/theme of videos">
                <HelpCircle className="h-4 w-4 text-gray-400 hover:text-gray-300 cursor-help" />
              </Tooltip>
            </div>
            <textarea
              ref={conceptTextareaRef}
              value={concept}
              onChange={(e) => setConcept(e.target.value)}
              placeholder="e.g., A cinematic sequence showing the transformation of a caterpillar into a butterfly, with soft lighting and nature sounds..."
              rows={4}
              className="w-full resize-y rounded-md bg-gray-950 border border-gray-800 p-3 text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            />
          </div>

          {/* Clip Duration Field */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <label className="block text-sm font-medium text-gray-200">
                Clip Duration
              </label>
              <Tooltip content="Duration of each clip in seconds">
                <HelpCircle className="h-4 w-4 text-gray-400 hover:text-gray-300 cursor-help" />
              </Tooltip>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min="1"
                max="60"
                value={clipDuration}
                onChange={(e) => setClipDuration(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-24 rounded-md bg-gray-950 border border-gray-800 p-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
              />
              <span className="text-sm text-gray-400">seconds</span>
            </div>
          </div>

          {/* Number of Clips Field */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <label className="block text-sm font-medium text-gray-200">
                Number of Clips
              </label>
              <Tooltip content="Total number of video clips to generate (minimum 1)">
                <HelpCircle className="h-4 w-4 text-gray-400 hover:text-gray-300 cursor-help" />
              </Tooltip>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min="1"
                value={numberOfClips}
                onChange={(e) => setNumberOfClips(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-24 rounded-md bg-gray-950 border border-gray-800 p-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
              />
              <span className="text-sm text-gray-400">clips</span>
            </div>
          </div>

          {/* Schedule Field */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <label className="block text-sm font-medium text-gray-200">
                Schedule <span className="text-red-400">*</span>
              </label>
              <Tooltip content="Set how often this workflow should run automatically">
                <HelpCircle className="h-4 w-4 text-gray-400 hover:text-gray-300 cursor-help" />
              </Tooltip>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min={scheduleUnit === 'minutes' ? 60 : 1}
                value={scheduleValue}
                onChange={(e) => {
                  const value = parseFloat(e.target.value) || (scheduleUnit === 'minutes' ? 60 : 1)
                  const minValue = scheduleUnit === 'minutes' ? 60 : 1
                  setScheduleValue(Math.max(minValue, value))
                }}
                className="w-24 rounded-md bg-gray-950 border border-gray-800 p-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
              />
              <select
                value={scheduleUnit}
                onChange={(e) => {
                  const newUnit = e.target.value
                  const oldUnit = scheduleUnit
                  setScheduleUnit(newUnit)
                  // When switching to minutes, default to 60 (minimum value for minutes)
                  // When switching to hours, convert minutes to hours (rounding up to at least 1)
                  if (newUnit === 'minutes') {
                    if (oldUnit === 'hours') {
                      // Convert hours to minutes
                      const minutes = scheduleValue * 60
                      setScheduleValue(minutes)
                    } else {
                      // Already in minutes, ensure minimum is 60
                      setScheduleValue(Math.max(60, scheduleValue))
                    }
                  } else if (newUnit === 'hours') {
                    if (oldUnit === 'minutes') {
                      // Convert minutes to hours, rounding up to at least 1
                      const hours = Math.max(1, Math.round(scheduleValue / 60))
                      setScheduleValue(hours)
                    }
                    // If already in hours, keep the value as is (default is 1)
                  }
                }}
                className="rounded-md bg-gray-950 border border-gray-800 p-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
              >
                <option value="minutes">minutes</option>
                <option value="hours">hours</option>
              </select>
            </div>
          </div>

          {/* Video Model Dropdown */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <label className="block text-sm font-medium text-gray-200">
                Video Model <span className="text-red-400">*</span>
              </label>
              <Tooltip content="Select the AI model for video generation">
                <HelpCircle className="h-4 w-4 text-gray-400 hover:text-gray-300 cursor-help" />
              </Tooltip>
            </div>
            <WorkflowFileUpload
              value={videoWorkflowFile}
              onChange={setVideoWorkflowFile}
              label="Video Workflow"
            />
          </div>

          {/* Image Model Dropdown - Only show if workflow type is image-to-video */}
          {workflowType === 'image-to-video' ? (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <label className="block text-sm font-medium text-gray-200">
                  Image Model <span className="text-red-400">*</span>
                </label>
                <Tooltip content="Select the AI model for image generation (if needed for the workflow)">
                  <HelpCircle className="h-4 w-4 text-gray-400 hover:text-gray-300 cursor-help" />
                </Tooltip>
              </div>
              <WorkflowFileUpload
                value={imageWorkflowFile}
                onChange={setImageWorkflowFile}
                label="Image Workflow"
              />
            </div>
          ) : null}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 mt-8 pt-6 border-t border-gray-800">
          <button
            onClick={handleBack}
            className="px-4 py-2 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-lg font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving || !name.trim() || !concept.trim() || !videoWorkflowFile || (workflowType === 'image-to-video' && !imageWorkflowFile) || !scheduleValue || scheduleValue < (scheduleUnit === 'minutes' ? 60 : 1)}
            className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg font-medium transition-colors"
          >
            {isSaving ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4" />
                {isEditing ? 'Update Workflow' : 'Create Workflow'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
