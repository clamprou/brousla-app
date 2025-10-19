import React, { useState } from 'react'
import { ArrowLeft, Save, Bot, HelpCircle } from 'lucide-react'
import ModelSelector from '../components/ModelSelector.jsx'

export default function CreateWorkflow() {
  const [concept, setConcept] = useState('')
  const [clipDuration, setClipDuration] = useState(5)
  const [numberOfClips, setNumberOfClips] = useState(1)
  const [videoModel, setVideoModel] = useState('Wan2.1')
  const [imageModel, setImageModel] = useState('Flux Schnell')
  const [isSaving, setIsSaving] = useState(false)

  // Available models based on existing pages
  const videoModelOptions = ['Wan2.1', 'Wan2.2']
  const imageModelOptions = ['Flux Schnell', 'FLUX Schnell', 'Pika', 'RunwayML']

  const handleSave = async () => {
    if (!concept.trim()) {
      alert('Please enter a concept for your workflow')
      return
    }

    setIsSaving(true)
    
    // Mock save operation - replace with actual API call
    setTimeout(() => {
      console.log('Saving workflow:', {
        concept,
        clipDuration,
        numberOfClips,
        videoModel,
        imageModel
      })
      setIsSaving(false)
      
      // Navigate back to AI Workflows page
      const ev = new CustomEvent('navigate', { detail: 'ai-composer' })
      window.dispatchEvent(ev)
    }, 1000)
  }

  const handleBack = () => {
    const ev = new CustomEvent('navigate', { detail: 'ai-composer' })
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
              <h1 className="text-2xl font-bold text-gray-100">Create New Workflow</h1>
              <p className="text-gray-400">Design a new AI-powered content generation workflow</p>
            </div>
          </div>
        </div>
      </div>

      {/* Form */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="space-y-6">
          {/* Concept Field */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <label className="block text-sm font-medium text-gray-200">
                Concept
              </label>
              <Tooltip content="Describe the main concept/theme of videos">
                <HelpCircle className="h-4 w-4 text-gray-400 hover:text-gray-300 cursor-help" />
              </Tooltip>
            </div>
            <textarea
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

          {/* Video Model Dropdown */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <label className="block text-sm font-medium text-gray-200">
                Video Model
              </label>
              <Tooltip content="Select the AI model for video generation">
                <HelpCircle className="h-4 w-4 text-gray-400 hover:text-gray-300 cursor-help" />
              </Tooltip>
            </div>
            <ModelSelector
              value={videoModel}
              onChange={setVideoModel}
              options={videoModelOptions}
            />
          </div>

          {/* Image Model Dropdown */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <label className="block text-sm font-medium text-gray-200">
                Image Model
              </label>
              <Tooltip content="Select the AI model for image generation (if needed for the workflow)">
                <HelpCircle className="h-4 w-4 text-gray-400 hover:text-gray-300 cursor-help" />
              </Tooltip>
            </div>
            <ModelSelector
              value={imageModel}
              onChange={setImageModel}
              options={imageModelOptions}
            />
          </div>
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
            disabled={isSaving || !concept.trim()}
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
                Create Workflow
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
