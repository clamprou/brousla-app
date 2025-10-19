import React, { useState } from 'react'
import { Bot, Workflow, Zap, ArrowRight, ImageIcon, Film, Type, Upload, Sparkles, Plus, Play, Edit, Trash2, Clock } from 'lucide-react'

export default function AIWorkflows() {
  // Mock data for workflows - in a real app this would come from state management or API
  const [workflows] = useState([
    {
      id: '1',
      name: 'Social Media Campaign',
      description: 'Generate images and videos for social media posts',
      status: 'active',
      lastRun: '2024-01-15T10:30:00Z',
      steps: 5,
      category: 'Marketing'
    },
    {
      id: '2',
      name: 'Product Showcase',
      description: 'Create product demonstration videos with music',
      status: 'draft',
      lastRun: null,
      steps: 4,
      category: 'E-commerce'
    },
    {
      id: '3',
      name: 'Educational Content',
      description: 'Generate educational materials with visuals and narration',
      status: 'active',
      lastRun: '2024-01-14T15:45:00Z',
      steps: 6,
      category: 'Education'
    }
  ])

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
          <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors">
            <Plus className="h-4 w-4" />
            Create Workflow
          </button>
        </div>
      </div>

      {/* Workflows List */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-8">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-200">Your Workflows</h3>
          <div className="text-sm text-gray-400">
            {workflows.length} workflow{workflows.length !== 1 ? 's' : ''}
          </div>
        </div>
        
        {workflows.length > 0 ? (
          <div className="space-y-3">
            {workflows.map((workflow) => (
              <div key={workflow.id} className="bg-gray-800 border border-gray-700 rounded-lg p-4 hover:bg-gray-750 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="font-medium text-gray-200">{workflow.name}</h4>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        workflow.status === 'active' 
                          ? 'bg-green-600/20 text-green-400 border border-green-600/30' 
                          : 'bg-yellow-600/20 text-yellow-400 border border-yellow-600/30'
                      }`}>
                        {workflow.status}
                      </span>
                      <span className="px-2 py-1 bg-gray-700 text-gray-300 rounded-full text-xs">
                        {workflow.category}
                      </span>
                    </div>
                    <p className="text-sm text-gray-400 mb-3">{workflow.description}</p>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <div className="flex items-center gap-1">
                        <Workflow className="h-3 w-3" />
                        {workflow.steps} steps
                      </div>
                      {workflow.lastRun && (
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          Last run: {new Date(workflow.lastRun).toLocaleDateString()}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <button className="p-2 text-gray-400 hover:text-blue-400 hover:bg-blue-600/20 rounded-lg transition-colors" title="Run Workflow">
                      <Play className="h-4 w-4" />
                    </button>
                    <button className="p-2 text-gray-400 hover:text-gray-300 hover:bg-gray-700 rounded-lg transition-colors" title="Edit Workflow">
                      <Edit className="h-4 w-4" />
                    </button>
                    <button className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-600/20 rounded-lg transition-colors" title="Delete Workflow">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-gray-800 rounded-full mb-4">
              <Workflow className="h-6 w-6 text-gray-500" />
            </div>
            <h4 className="text-gray-300 font-medium mb-2">No workflows yet</h4>
            <p className="text-gray-500 text-sm mb-4">Create your first workflow to get started with AI-powered content generation</p>
            <button className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors">
              <Plus className="h-4 w-4" />
              Create Your First Workflow
            </button>
          </div>
        )}
      </div>

      {/* Main Description Card */}
      <div className="bg-gradient-to-br from-gray-900 to-gray-800 border border-gray-700 rounded-xl p-8 mb-8">
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
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        {features.map((feature, index) => (
          <div key={index} className="bg-gray-900 border border-gray-800 rounded-lg p-6">
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
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-200 mb-4">Example Workflow Templates</h3>
        <div className="grid md:grid-cols-3 gap-4">
          {exampleWorkflows.map((workflow, index) => (
            <div key={index} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
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
  )
}


