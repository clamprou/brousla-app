import React, { useState } from 'react'
import { ArrowLeft, Image, Type, ArrowRight, Bot } from 'lucide-react'

export default function WorkflowTypeSelection() {
  const [selectedType, setSelectedType] = useState(null)

  const handleBack = () => {
    const ev = new CustomEvent('navigate', { detail: 'ai-composer' })
    window.dispatchEvent(ev)
  }

  const handleContinue = () => {
    if (selectedType) {
      // Store the selected workflow type
      window.selectedWorkflowType = selectedType
      // Navigate to CreateWorkflow page
      const ev = new CustomEvent('navigate', { detail: 'create-workflow' })
      window.dispatchEvent(ev)
    }
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
              <p className="text-gray-400">Choose the type of workflow you want to create</p>
            </div>
          </div>
        </div>
      </div>

      {/* Selection Cards */}
      <div className="grid md:grid-cols-2 gap-6 mb-8">
        {/* Image to Video Workflow */}
        <button
          onClick={() => setSelectedType('image-to-video')}
          className={`relative bg-gray-900 border-2 rounded-xl p-8 transition-all hover:border-blue-500 ${
            selectedType === 'image-to-video'
              ? 'border-blue-600 bg-blue-600/10'
              : 'border-gray-800 hover:bg-gray-800'
          }`}
        >
          <div className="flex flex-col items-center text-center">
            <div className={`p-4 rounded-full mb-4 ${
              selectedType === 'image-to-video'
                ? 'bg-blue-600/20'
                : 'bg-gray-800'
            }`}>
              <Image className="h-12 w-12 text-blue-400" />
            </div>
            <h2 className="text-xl font-semibold text-gray-200 mb-2">Image to Video</h2>
            <p className="text-sm text-gray-400">
              Videos will be generated using 2 different models. First a text to image model to generate the frames and then an image to video model to generate the video.
            </p>
          </div>
          {selectedType === 'image-to-video' && (
            <div className="absolute top-4 right-4">
              <div className="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center">
                <div className="w-2 h-2 bg-white rounded-full"></div>
              </div>
            </div>
          )}
        </button>

        {/* Text to Video Workflow */}
        <button
          onClick={() => setSelectedType('text-to-video')}
          className={`relative bg-gray-900 border-2 rounded-xl p-8 transition-all hover:border-blue-500 ${
            selectedType === 'text-to-video'
              ? 'border-blue-600 bg-blue-600/10'
              : 'border-gray-800 hover:bg-gray-800'
          }`}
        >
          <div className="flex flex-col items-center text-center">
            <div className={`p-4 rounded-full mb-4 ${
              selectedType === 'text-to-video'
                ? 'bg-blue-600/20'
                : 'bg-gray-800'
            }`}>
              <Type className="h-12 w-12 text-blue-400" />
            </div>
            <h2 className="text-xl font-semibold text-gray-200 mb-2">Text to Video</h2>
            <p className="text-sm text-gray-400">
              Videos will be generated using a text to video model. The model will generate the video frame by frame.
            </p>
          </div>
          {selectedType === 'text-to-video' && (
            <div className="absolute top-4 right-4">
              <div className="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center">
                <div className="w-2 h-2 bg-white rounded-full"></div>
              </div>
            </div>
          )}
        </button>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-end gap-3">
        <button
          onClick={handleBack}
          className="px-4 py-2 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-lg font-medium transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleContinue}
          disabled={!selectedType}
          className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg font-medium transition-colors"
        >
          Continue
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}

